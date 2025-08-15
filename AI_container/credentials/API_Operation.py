import os
from dotenv import load_dotenv
import google.generativeai as genai
from AI_container.credentials.api_load import load_api
import time
import tempfile
import numpy as np
import streamlit as st
import re
import os
import pandas as pd
import logging
from End.Operations import SheetOperations
import json
from datetime import datetime

class PDFQA:
    def __init__(self):
        load_api()  
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.embedding_model = 'models/embedding-001'

    @staticmethod
    def clean_monetary_value(value):
        if pd.isna(value) or value == '': return 0.0
        s = str(value).strip()
        if ',' in s: s = s.replace('.', '').replace(',', '.')
        try: return float(s)
        except (ValueError, TypeError): return 0.0

    def clean_text(self, text):
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s,.!?\'\"-]', '', text)
        return text.strip()

    def ask_gemini(self, context, question):
        try:
            st.info("Enviando pergunta para o modelo Gemini...")
            response = self.model.generate_content(f"""
            Contexto: {context}

            Pergunta: {question}

            Por favor, forneça uma resposta detalhada e precisa.
            """)
            st.success("Resposta recebida do modelo Gemini.")
            return response.text
        except Exception as e:
            st.error(f"Erro ao obter resposta do modelo Gemini: {str(e)}")
            return None

    def answer_question(self, pdf_files, question):
        start_time = time.time()

        try:

            with st.spinner("Gerando resposta com o modelo Gemini..."):
                answer = self.ask_gemini("Baseado nos arquivos fornecidos", question)
                st.info("Resposta gerada com sucesso.")
            st.success("Resposta gerada com sucesso.")

            end_time = time.time()
            elapsed_time = end_time - start_time

            return answer, elapsed_time
        except Exception as e:
            st.error(f"Erro inesperado ao processar a pergunta: {str(e)}")
            st.exception(e)
            return f"Ocorreu um erro ao processar a pergunta: {str(e)}", 0


    def stock_analysis(self, stock_data, purchase_history=None, usage_history=None, employee_data=None):
        """
        Analisa dados de estoque e fornece recomendações de compra (versão completa restaurada).
        """
        try:
            st.info("Analisando estoque e gerando recomendações...")
            
            # A lógica de carregar os dados de funcionários agora vem do argumento da função
            df_employees = None
            if employee_data and len(employee_data) > 1:
                df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])

            employee_context = ""
            if df_employees is not None:
                # Converte colunas de quantidade para numérico antes de somar
                for col in ['Quantidade de Calças', 'Quantidade de Jalecos', 'Quantidade de Camisa Polo', 
                            'Quantidade de Japona de Lã', 'Quantidade de Jaquetas', 'Quantidade de Calçado']:
                    if col in df_employees.columns:
                        df_employees[col] = pd.to_numeric(df_employees[col], errors='coerce').fillna(0)

                size_counts = {
                    'Camisa Manga Comprida': df_employees['Tamanho Camisa Manga Comprida'].value_counts().to_dict(),
                    'Calça': df_employees['Tamanho Calça'].value_counts().to_dict(),
                    'Jaleco': df_employees['Tamanho Jaleco para laboratório'].value_counts().to_dict(),
                    'Camisa Polo': df_employees['Tamanho Camisa Polo'].value_counts().to_dict(),
                    'Japona de Lã': df_employees['Tamanho de Japona de Lã (para frio)'].value_counts().to_dict(),
                    'Jaqueta': df_employees['Tamanho Jaquetas (para frio)'].value_counts().to_dict(),
                    'Calçado': df_employees['Tamanho do calçado'].value_counts().to_dict()
                }
                
                total_needs = {
                    'Calça': df_employees['Quantidade de Calças'].sum(),
                    'Jaleco': df_employees['Quantidade de Jalecos'].sum(),
                    'Camisa Polo': df_employees['Quantidade de Camisa Polo'].sum(),
                    'Japona de Lã': df_employees['Quantidade de Japona de Lã'].sum(),
                    'Jaqueta': df_employees['Quantidade de Jaquetas'].sum(),
                    'Calçado': df_employees['Quantidade de Calçado'].sum()
                }
                area_analysis = df_employees.groupby('Área de Atuação').size().to_dict()
                gender_analysis = df_employees.groupby('Gênero').size().to_dict()
                employee_context = f"""
                Informações adicionais dos funcionários:
                Distribuição de tamanhos por EPI: {size_counts}
                Necessidades totais por EPI: {total_needs}
                Distribuição por área: {area_analysis}
                Distribuição por gênero: {gender_analysis}
                Por favor, considere estas informações ao fazer as recomendações de compra,
                levando em conta os tamanhos necessários e as quantidades adequadas para cada funcionário.
                """
            
            context = f"""
            Dados atuais do estoque: {stock_data}
            {f'Histórico de compras: {purchase_history}' if purchase_history else ''}
            {f'Histórico de uso: {usage_history}' if usage_history else ''}
            {employee_context if employee_context else ''}
            
            Informações importantes sobre periodicidade de troca dos EPIs:
            1. Botinas:
               - Troca a cada 6 meses
               - Vida útil em estoque: 1 ano (após isso o solado derrete)
            2. Luvas CA 28011:
               - 50% dos funcionários trocam a cada 2 semanas, 50% trocam a cada 1 mês.
            3. Cinto de Segurança:
               - Troca programada a cada 6 meses.
            4. Uniformes (Camisas e Calças):
               - Troca mínima a cada 6 meses.
            
            Com base nos dados fornecidos, analise de forma minimalista (direto ao ponto):
            1. Quais itens estão com estoque baixo e precisam ser reabastecidos.
            2. Quais itens têm alto consumo e devem ter prioridade de compra.
            3. Se existe algum padrão de consumo que deva ser considerado.
            4. Uma lista de recomendações de compra com quantidades sugeridas.
            5. Sugestão de cronograma de compras para evitar excesso de estoque.
            6. Quando indicar compra seja especifico, indique o EPI, o CA e a quantidade especifica.
            """
            response = self.model.generate_content(context)
            
            try:
                recommendations = response.text
            except ValueError:
                recommendations = "A IA não conseguiu gerar recomendações (provável bloqueio de segurança)."
            
            st.success("Análise de estoque concluída com sucesso.")
            
            return {
                "recommendations": recommendations,
            }
            
        except Exception as e:
            st.error(f"Erro ao analisar o estoque: {str(e)}")
            st.exception(e)
            return { "error": f"Ocorreu um erro ao analisar o estoque: {str(e)}" }

    def generate_annual_forecast(self, usage_history, purchase_history, stock_data, employee_data, forecast_months=12):
        """
        Usa Python para cálculos precisos e a IA para análise estratégica e formatação do relatório.
        """
        try:
            st.info("Passo 1/3: Realizando cálculos de necessidade...")
            
            # --- 1. PYTHON FAZ O TRABALHO BRAÇAL (CÁLCULOS PRECISOS) ---
            if not usage_history: return {"error": "Histórico de uso insuficiente."}
            if not purchase_history: return {"error": "Histórico de compras insuficiente."}
            if not employee_data: return {"error": "Dados de funcionários não carregados."}
            
            df_usage = pd.DataFrame(usage_history); df_usage['date'] = pd.to_datetime(df_usage['date'], errors='coerce'); df_usage['quantity'] = pd.to_numeric(df_usage['quantity'], errors='coerce').fillna(0); df_usage.dropna(subset=['date', 'quantity', 'epi_name'], inplace=True)
            df_purchase = pd.DataFrame(purchase_history); df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce'); df_purchase['value'] = df_purchase['value'].apply(PDFQA.clean_monetary_value); df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce').fillna(0); df_purchase.dropna(subset=['date', 'value', 'quantity', 'epi_name'], inplace=True)
            df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])
            df_purchase = df_purchase[df_purchase['quantity'] > 0].copy(); df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
            latest_costs_df = df_purchase.sort_values('date').drop_duplicates('epi_name', keep='last'); unit_costs = latest_costs_df.set_index('epi_name')['unit_cost'].to_dict()
    
            needs_from_employees = {}
            employee_need_mapping = {'Tamanho Calça': ('CALÇA', 'Quantidade de Calças'), 'Tamanho do calçado': ('BOTINA', 'Quantidade de Calçado'), 'Tamanho Camisa Manga Comprida': ('CAMISA', 'Quantidade de Camisas'), 'Tamanho Camisa Polo': ('CAMISA POLO', 'Quantidade de Camisa Polo')}
            exchange_factor = forecast_months / 6.0
            
            for size_col, (epi_prefix, qty_col) in employee_need_mapping.items():
                if size_col in df_employees.columns and qty_col in df_employees.columns:
                    df_employees[qty_col] = pd.to_numeric(df_employees[qty_col], errors='coerce').fillna(0)
                    size_needs = df_employees.groupby(size_col)[qty_col].sum()
                    for size, total_qty in size_needs.items():
                        if total_qty > 0 and pd.notna(size) and str(size).strip() != '-':
                            projected_qty = np.ceil(total_qty * exchange_factor)
                            found_name = next((name for name in {**stock_data, **unit_costs}.keys() if epi_prefix in name.upper() and str(size).split(' ')[0] in name), None)
                            final_epi_name = found_name if found_name else f"{epi_prefix} TAMANHO {size}"
                            needs_from_employees[final_epi_name] = needs_from_employees.get(final_epi_name, 0) + projected_qty
    
            excluded_prefixes = ['CALÇA', 'BOTINA', 'CAMISA']
            df_usage_others = df_usage[~df_usage['epi_name'].str.upper().str.contains('|'.join(excluded_prefixes), na=False)]
            needs_from_consumption = {}
            if not df_usage_others.empty:
                total_days = (df_usage_others['date'].max() - df_usage_others['date'].min()).days
                num_months_in_data = total_days / 30.44 if total_days > 0 else 1
                if num_months_in_data < 1: num_months_in_data = 1
                total_consumption = df_usage_others.groupby('epi_name')['quantity'].sum()
                avg_monthly_consumption = total_consumption / num_months_in_data
                for epi_name, avg_consumption in avg_monthly_consumption.items():
                    needs_from_consumption[epi_name] = np.ceil(avg_consumption * forecast_months)
    
            total_projected_needs = {**needs_from_employees, **needs_from_consumption}
            
            recommendation_list = []
            all_relevant_epis = set(total_projected_needs.keys()) | set(stock_data.keys())
            for epi_name in all_relevant_epis:
                projected_qty = total_projected_needs.get(epi_name, 0)
                current_stock = stock_data.get(epi_name, 0)
                needed_qty = max(0, projected_qty - current_stock)
                if 0 < current_stock <= 5 and needed_qty < 2: needed_qty = 2
                if current_stock > 5 and needed_qty == 0: needed_qty = 1
                if needed_qty > 0:
                    recommendation_list.append({
                        "EPI": epi_name.strip(),
                        "Qtd. Ideal a Comprar": int(needed_qty),
                        "Custo Unit. (R$)": unit_costs.get(epi_name.strip(), 0.0)
                    })
    
            if not recommendation_list:
                return {"report": "## Previsão Anual\n\nEstoque atual suficiente."}
            
            df_recommendation = pd.DataFrame(recommendation_list)
            df_recommendation['Custo Total Ideal (R$)'] = df_recommendation['Qtd. Ideal a Comprar'] * df_recommendation['Custo Unit. (R$)']
            df_recommendation = df_recommendation.sort_values(by="Custo Total Ideal (R$)", ascending=False)
            total_ideal_cost = df_recommendation['Custo Total Ideal (R$)'].sum()
    
            # --- 2. IA FAZ O TRABALHO ESTRATÉGICO ---
            st.info("Passo 2/3: IA analisando dados e gerando relatório estratégico...")
            
            prompt = f"""
            **Sua Tarefa:** Você é um especialista sênior em Gestão de Estoque e Compras. Sua tarefa é analisar os dados pré-calculados e gerar um relatório completo de previsão de compras anual.
    
            **Dados de Entrada (Cálculo Bruto da Necessidade):**
            A tabela abaixo mostra a necessidade de compra "ideal" calculada matematicamente para os próximos 12 meses. O custo total ideal é de R$ {total_ideal_cost:,.2f}.
            ```
            {df_recommendation.to_string(index=False)}
            ```
    
            **Instruções para o Relatório Final:**
            1.  **Analise a lista:** Use seu conhecimento para interpretar os dados. Itens com custo alto merecem atenção, itens de consumo rápido precisam de um bom estoque de segurança.
            2.  **Crie um relatório final em Markdown** com as seguintes seções:
                *   **Título:** `### Previsão de Compras Anual e Análise Estratégica`
                *   **Orçamento Estimado:** Calcule o custo total final com base nas suas recomendações e apresente-o (ex: `#### Orçamento Total Estimado: R$ 198.543,21`).
                *   **Resumo Executivo (Curto):** Um parágrafo destacando o valor total e os 2-3 principais itens que impulsionam o custo.
                *   **Lista de Compras Recomendada:** Uma tabela final com as colunas `EPI`, `Qtd. a Comprar`, `Custo Total (R$)` e `Justificativa`. Na `Qtd. a Comprar`, você pode ajustar a "Qtd. Ideal" com bom senso (arredondar, etc.) e explicar na `Justificativa`.
                *   **Sugestão de Cronograma de Compras:** Sugira quais itens devem ser comprados mensalmente, trimestralmente ou semestralmente.
            
            **Seja preciso, use todos os dados e forneça um relatório gerencial de alto nível.**
            """
            
            st.info("Passo 3/3: Aguardando formatação final da IA...")
            response = self.model.generate_content(prompt)
            
            try:
                final_report = response.text
            except ValueError:
                final_report = "A IA não conseguiu gerar o relatório (provável bloqueio de segurança)."
    
            st.success("Previsão de compras gerada com sucesso!")
            return {"report": final_report}
    
        except Exception as e:
            st.error(f"Erro ao gerar previsão de compras: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}
        








































