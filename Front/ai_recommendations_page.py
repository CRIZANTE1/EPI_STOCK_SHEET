import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
import os

# Adicionar o diretório pai ao path para import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from AI_container.credentials.API_Operation import PDFQA

def ai_recommendations_page():
    """
    Página para exibir recomendações de compra e análise de estoque geradas por IA
    """
    st.title("Recomendações de Compra Inteligentes 🤖")
    
    # Inicializar a classe PDFQA que contém os métodos de IA
    ai_engine = PDFQA()
    
    # Carregar dados da planilha
    sheet_operations = SheetOperations()
    
    if 'data' not in st.session_state:
        data = sheet_operations.carregar_dados()
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            st.session_state['data'] = df
        else:
            st.error("Não foi possível carregar a planilha")
            return

    df = st.session_state['data'].copy()
    
    # Preparar dados para análise
    try:
        # Converter colunas para formatos adequados
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['value'] = df['value'].apply(lambda x: 0 if x == '' else float(str(x).replace('.', '').replace(',', '.')))
        
        # Normalizar tipos de transação
        df['transaction_type'] = df['transaction_type'].str.lower().str.strip()
        
        # Calcular estoque atual por EPI
        epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum().fillna(0)
        epi_exits = df[df['transaction_type'] == 'saida'].groupby('epi_name')['quantity'].sum().fillna(0)
        
        # Unir os índices para garantir que todos EPIs sejam considerados
        all_epis = epi_entries.index.union(epi_exits.index)
        current_stock = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)
        
        # Converter para dicionário para uso na IA
        stock_data = current_stock.to_dict()
        
        # Preparar histórico de compras (últimas 20 entradas)
        purchase_history = df[df['transaction_type'] == 'entrada'].sort_values(
            by='date', ascending=False
        ).head(20)[['date', 'epi_name', 'quantity', 'value']].to_dict('records')
        
        # Preparar histórico de uso (últimas 30 saídas)
        usage_history = df[df['transaction_type'] == 'saida'].sort_values(
            by='date', ascending=False
        ).head(30)[['date', 'epi_name', 'quantity', 'requester']].to_dict('records')
        
        # Exibir resumo do estoque atual
        st.subheader("Resumo do Estoque Atual")
        
        # Separar os itens em críticos (<=0) e normais (>0)
        critical_items = {k: v for k, v in stock_data.items() if v <= 0}
        normal_items = {k: v for k, v in stock_data.items() if v > 0}
        
        # Exibir itens críticos
        if critical_items:
            st.error("⚠️ Itens com Estoque Crítico")
            for item, qty in critical_items.items():
                st.write(f"- **{item}**: {int(qty) if qty == int(qty) else qty:.2f}")
        
        # Exibir itens normais como tabela
        if normal_items:
            normal_df = pd.DataFrame(list(normal_items.items()), columns=['EPI', 'Quantidade'])
            normal_df = normal_df.sort_values(by='Quantidade')
            st.dataframe(normal_df, use_container_width=True)
        
        # Seção para análise de IA
        st.subheader("Análise de Estoque por Inteligência Artificial")
        
        # Botão para gerar recomendações
        if st.button("Gerar Recomendações de Compra"):
            with st.spinner("Analisando dados de estoque e gerando recomendações..."):
                # Chamar a função de análise de estoque da IA
                recommendations = ai_engine.stock_analysis(
                    stock_data, 
                    purchase_history,
                    usage_history
                )
                
                if "error" in recommendations:
                    st.error(recommendations["error"])
                else:
                    # Exibir as recomendações
                    st.markdown("### Recomendações de Compra")
                    st.markdown(recommendations["recommendations"])
                    
                    # Salvar as recomendações no histórico de sessão
                    if 'recommendation_history' not in st.session_state:
                        st.session_state.recommendation_history = []
                    
                    # Adicionar nova recomendação ao histórico
                    st.session_state.recommendation_history.append({
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "recommendations": recommendations["recommendations"]
                    })
        
        # Exibir histórico de recomendações
        if 'recommendation_history' in st.session_state and st.session_state.recommendation_history:
            st.subheader("Histórico de Recomendações")
            
            for i, rec in enumerate(reversed(st.session_state.recommendation_history)):
                with st.expander(f"Recomendação de {rec['timestamp']}"):
                    st.markdown(rec["recommendations"])
                
                # Limitar a exibição das últimas 5 recomendações
                if i >= 4:
                    break
    
    except Exception as e:
        st.error(f"Erro ao analisar dados de estoque: {str(e)}")
        st.exception(e) 