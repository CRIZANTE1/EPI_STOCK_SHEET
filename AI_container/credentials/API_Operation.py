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
        Gera uma análise de estoque completa e uma lista de compras para curto prazo.
        """
        try:
            st.info("Analisando estoque e necessidades de curto prazo...")
            
            employee_context_str = ""
            if employee_data:
                df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])
                employee_summary = {
                    "total_funcionarios": len(df_employees),
                    "distribuicao_tamanhos_calca": df_employees['Tamanho Calça'].value_counts().to_dict(),
                    "necessidade_total_calcas": pd.to_numeric(df_employees['Quantidade de Calças'], errors='coerce').sum(),
                    "distribuicao_tamanhos_calcado": df_employees['Tamanho do calçado'].value_counts().to_dict(),
                    "necessidade_total_calcados": pd.to_numeric(df_employees['Quantidade de Calçado'], errors='coerce').sum()
                }
                employee_context_str = json.dumps(employee_summary, indent=2, ensure_ascii=False)
            
            prompt = f"""
            Com base no estoque atual, histórico de uso, e dados dos funcionários, gere uma recomendação de compra para os próximos 3 meses.

            Estoque Atual:
            {json.dumps(stock_data, indent=2)}

            Dados dos Funcionários (Resumo):
            {employee_context_str}

            Sua resposta deve ser um relatório em Markdown contendo uma lista de itens a comprar e a justificativa.
            """
            response = self.model.generate_content(prompt)
            return {"recommendations": response.text}
        except Exception as e:
            logging.error(f"Erro na função stock_analysis: {e}")
            return {"error": f"Erro na análise de estoque: {str(e)}"}

    def generate_annual_forecast(self, usage_history, purchase_history, stock_data, employee_data, forecast_months=12):
        """
        Gera uma previsão orçamentária anual precisa, unindo todas as fontes de dados.
        """
        try:
            st.info(f"Iniciando a geração da previsão para {forecast_months} meses...")
            
            # --- 1. Preparação dos Dados ---
            if not usage_history: return {"error": "Histórico de uso insuficiente."}
            if not purchase_history: return {"error": "Histórico de compras insuficiente."}
            if not employee_data: return {"error": "Dados de funcionários não carregados."}
            
            df_usage = pd.DataFrame(usage_history)
            df_usage['date'] = pd.to_datetime(df_usage['date'], errors='coerce')
            df_usage['quantity'] = pd.to_numeric(df_usage['quantity'], errors='coerce').fillna(0)
            df_usage.dropna(subset=['date', 'quantity', 'epi_name'], inplace=True)
            
            df_purchase = pd.DataFrame(purchase_history)
            df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce')
            df_purchase['value'] = df_purchase['value'].apply(PDFQA.clean_monetary_value)
            df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce').fillna(0)
            df_purchase.dropna(subset=['date', 'value', 'quantity', 'epi_name'], inplace=True)
            
            df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])
            df_purchase = df_purchase[df_purchase['quantity'] > 0].copy()
            df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
            latest_costs_df = df_purchase.sort_values('date').drop_duplicates('epi_name', keep='last')
            unit_costs = latest_costs_df.set_index('epi_name')['unit_cost'].to_dict()

            # --- 2. Cálculo da Necessidade Direta (Uniformes e Calçados) ---
            needs_from_employees = {}
            employee_need_mapping = {
                'Tamanho Calça': ('CALÇA', 'Quantidade de Calças'),
                'Tamanho do calçado': ('BOTINA', 'Quantidade de Calçado'),
                'Tamanho Camisa Manga Comprida': ('CAMISA', 'Quantidade de Camisas'),
                'Tamanho Camisa Polo': ('CAMISA POLO', 'Quantidade de Camisa Polo')
            }
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

            # --- 3. Cálculo da Necessidade por Consumo (Outros EPIs) ---
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

            # --- 4. Unificação e Geração do Relatório Final ---
            total_projected_needs = needs_from_employees.copy()
            total_projected_needs.update(needs_from_consumption)
            recommendation_list = []
            for epi_name, projected_qty in total_projected_needs.items():
                current_stock = stock_data.get(epi_name, 0)
                needed_qty = max(0, projected_qty - current_stock)
                if 0 < current_stock <= 5 and needed_qty < 2:
                    needed_qty += 2
                if needed_qty > 0:
                    unit_cost = unit_costs.get(epi_name.strip(), 0.0)
                    total_cost = needed_qty * unit_cost
                    recommendation_list.append({
                        "EPI": epi_name.strip(),
                        "Qtd. a Comprar": int(needed_qty),
                        "Custo Unit. (R$)": unit_cost,
                        "Custo Total (R$)": total_cost
                    })

            if not recommendation_list:
                return {"report": f"## Previsão para {forecast_months} Meses\n\nEstoque atual suficiente.", "total_cost": 0}
            
            df_recommendation = pd.DataFrame(recommendation_list).sort_values(by="Custo Total (R$)", ascending=False)
            final_total_cost = df_recommendation['Custo Total (R$)'].sum()
            formatted_total_cost = '{:_.2f}'.format(final_total_cost).replace('.', ',').replace('_', '.')
            
            df_display = df_recommendation.copy()
            df_display['Custo Unit. (R$)'] = df_display['Custo Unit. (R$)'].map('{:,.2f}'.format).str.replace(',', 'v').replace('.', ',').str.replace('v', '.')
            df_display['Custo Total (R$)'] = df_display['Custo Total (R$)'].map('{:,.2f}'.format).str.replace(',', 'v').replace('.', ',').str.replace('v', '.')
            
            report_title = f"### Previsão de Compras para {forecast_months} Meses"
            report_subtitle = f"#### Orçamento Total Estimado: R$ {formatted_total_cost}"
            table_md = df_display.to_markdown(index=False)
            final_report = f"{report_title}\n{report_subtitle}\n\n{table_md}"

            st.success("Previsão de compras gerada com sucesso!")
            return {"report": final_report, "total_cost": final_total_cost}

        except Exception as e:
            st.error(f"Erro ao gerar previsão de compras: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}





































