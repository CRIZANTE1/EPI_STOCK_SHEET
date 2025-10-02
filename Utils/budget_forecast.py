import pandas as pd
import numpy as np
from datetime import datetime
from AI_container.credentials.API_Operation import PDFQA
import logging

def generate_budget_forecast(sheet_operations, ano_base, margem_seguranca_percent):
    """
    Gera uma previsão orçamentária para o próximo ano baseada no histórico de consumo.
    
    Args:
        sheet_operations: Instância de SheetOperations para acessar os dados
        ano_base: Ano que será usado como base para a análise
        margem_seguranca_percent: Percentual de margem de segurança a ser aplicado
        
    Returns:
        dict: Contém o relatório completo, valores previstos e detalhes
    """
    try:
        # Carregar dados
        data = sheet_operations.carregar_dados()
        if not data or len(data) <= 1:
            return {"erro": "Não foi possível carregar os dados da planilha."}
        
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Processar dados
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['value'] = df['value'].apply(lambda x: 0 if x == '' else float(str(x).replace('.', '').replace(',', '.')))
        df['transaction_type'] = df['transaction_type'].str.lower().str.strip()
        
        # Filtrar apenas entradas do ano base
        df_ano_base = df[
            (df['date'].dt.year == ano_base) & 
            (df['transaction_type'] == 'entrada')
        ].copy()
        
        if df_ano_base.empty:
            return {"erro": f"Nenhum dado de entrada encontrado para o ano {ano_base}."}
        
        # Calcular estatísticas por EPI
        df_ano_base['valor_total'] = df_ano_base['quantity'] * df_ano_base['value']
        
        estatisticas_epi = df_ano_base.groupby('epi_name').agg({
            'quantity': 'sum',
            'valor_total': 'sum',
            'value': 'mean'
        }).round(2)
        
        estatisticas_epi.columns = ['Quantidade Total', 'Valor Total Gasto', 'Valor Médio Unitário']
        
        # Carregar dados de funcionários
        try:
            emp_data = sheet_operations.carregar_dados_funcionarios()
            if emp_data and len(emp_data) > 1:
                df_funcionarios = pd.DataFrame(emp_data[1:], columns=emp_data[0])
                total_funcionarios = len(df_funcionarios)
            else:
                total_funcionarios = df['requester'].nunique()
        except:
            total_funcionarios = df['requester'].nunique()
        
        # Preparar contexto para IA
        contexto = f"""
        Análise para Previsão Orçamentária de EPIs - Ano {ano_base + 1}
        
        Dados do Ano Base ({ano_base}):
        - Total de funcionários: {total_funcionarios}
        - Total gasto com EPIs: R$ {estatisticas_epi['Valor Total Gasto'].sum():,.2f}
        - Número de EPIs diferentes adquiridos: {len(estatisticas_epi)}
        
        Detalhamento por EPI:
        {estatisticas_epi.to_string()}
        
        Informações Importantes:
        1. Botinas têm vida útil de 1 ano em estoque (o solado derrete)
        2. Luvas CA 28011: 50% dos funcionários trocam a cada 2 semanas, 50% a cada 1 mês
        3. EPIs de proteção (cintos, máscaras): troca a cada 6 meses
        4. Uniformes (camisas, calças): troca mínima a cada 6 meses
        
        Com base nestes dados históricos e considerando:
        - Manutenção do quadro de funcionários
        - Periodicidade de troca dos EPIs
        - Tendências de consumo observadas
        - Margem de segurança de {margem_seguranca_percent}%
        
        Por favor, forneça uma previsão orçamentária DETALHADA para {ano_base + 1} contendo:
        
        1. **Resumo Executivo**: Valor total previsto e principais direcionadores de custo
        
        2. **Análise por Categoria de EPI**: Para cada EPI principal, indique:
           - Quantidade estimada necessária
           - Custo unitário projetado
           - Custo total estimado
           - Justificativa baseada na periodicidade de troca
        
        3. **Cronograma de Compras Sugerido**: Distribua as compras ao longo do ano considerando:
           - Vida útil dos produtos em estoque
           - Sazonalidade (se aplicável)
           - Otimização de fluxo de caixa
        
        4. **Recomendações Estratégicas**: Sugestões para otimização de custos
        
        5. **Tabela Resumo**: Apresente uma tabela markdown com:
           | EPI | Qtd. Prevista | Valor Unit. | Subtotal |
        
        Formato: Use Markdown para formatação clara e profissional.
        """
        
        # Chamar IA
        ai_engine = PDFQA()
        relatorio_ia = ai_engine.model.generate_content(contexto).text
        
        # Calcular valores
        total_previsto = estatisticas_epi['Valor Total Gasto'].sum()
        margem = total_previsto * (margem_seguranca_percent / 100)
        total_com_margem = total_previsto + margem
        
        # Montar relatório completo
        relatorio_completo = f"""
# Previsão Orçamentária de EPIs - Ano {ano_base + 1}

**Data de Geração:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

---

## Dados de Referência (Ano Base: {ano_base})

- **Total de Funcionários:** {total_funcionarios}
- **Gasto Total em {ano_base}:** R$ {total_previsto:,.2f}
- **EPIs Diferentes Adquiridos:** {len(estatisticas_epi)}

---

## Projeção de Gastos

- **Valor Base Projetado:** R$ {total_previsto:,.2f}
- **Margem de Segurança ({margem_seguranca_percent}%):** R$ {margem:,.2f}
- **TOTAL PREVISTO:** R$ {total_com_margem:,.2f}

---

{relatorio_ia}

---

## Observações Finais

Esta previsão foi gerada automaticamente com base em dados históricos e análise de IA. 
Recomenda-se revisão trimestral para ajustes conforme necessário.

**Disclaimer:** Valores sujeitos a alterações devido a variações de mercado, mudanças no quadro de funcionários 
ou alterações nas normas de segurança do trabalho.
        """
        
        return {
            "relatorio_completo": relatorio_completo,
            "total_previsto": total_previsto,
            "total_com_margem": total_com_margem,
            "margem": margem,
            "estatisticas": estatisticas_epi.to_dict()
        }
        
    except Exception as e:
        logging.error(f"Erro ao gerar previsão orçamentária: {e}")
        return {"erro": f"Erro ao gerar previsão: {str(e)}"}
