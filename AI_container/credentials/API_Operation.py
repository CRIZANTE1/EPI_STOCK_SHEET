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
from fuzzywuzzy import process

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


    def stock_analysis(self, stock_data, purchase_history, usage_history, employee_data):
        """
        Gera uma análise de estoque completa e uma lista de compras de curto prazo (base 3 meses).
        """
        try:
            st.info("Analisando estoque e necessidades de curto prazo...")
            
            df_employees = None
            if employee_data and len(employee_data) > 1:
                df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])

            employee_context = ""
            if df_employees is not None:
                # Converte colunas de quantidade para numérico
                qty_cols = [col for col in df_employees.columns if 'Quantidade' in col]
                for col in qty_cols:
                    df_employees[col] = pd.to_numeric(df_employees[col], errors='coerce').fillna(0)
                
                # Resumo para a IA
                employee_summary = {
                    "total_funcionarios": len(df_employees),
                    "necessidade_total_calcas": df_employees['Quantidade de Calças'].sum() if 'Quantidade de Calças' in df_employees.columns else 0,
                    "necessidade_total_calcados": df_employees['Quantidade de Calçado'].sum() if 'Quantidade de Calçado' in df_employees.columns else 0
                }
                employee_context = json.dumps(employee_summary, indent=2, ensure_ascii=False)

            context = f"""
            **Dados:**
            - Estoque Atual: {json.dumps(stock_data, indent=2, ensure_ascii=False)}
            - Histórico de Uso (últimos 50): {pd.DataFrame(usage_history).head(50).to_string()}
            - Resumo dos Funcionários: {employee_context}
            
            **Regras de Negócio:**
            - Botinas e Uniformes: Troca a cada 6 meses.
            - Luvas (ex: CA 28011): Consumo muito alto (média de 1.5 por funcionário/mês).
            - Estoque Crítico: Qualquer item com estoque <= 5.

            **Tarefa:**
            Com base em TODOS os dados, gere um relatório Markdown completo e detalhado. A sua recomendação de compra deve ser projetada para garantir um estoque de segurança para os próximos **3 MESES**.
            O relatório deve conter as 5 seções que você gerou anteriormente:
            1. Itens com Estoque Baixo (Reabastecimento Urgente)
            2. Itens com Alto Consumo (Prioridade de Compra)
            3. Padrão de Consumo
            4. Recomendações de Compra (Lista Detalhada para 3 meses)
            5. Sugestão de Cronograma de Compras (Mensal, Trimestral, etc.)
            """
            response = self.model.generate_content(context)
            
            try:
                recommendations = response.text
            except ValueError:
                recommendations = "A IA não conseguiu gerar recomendações."
            
            return {"recommendations": recommendations}
            
        except Exception as e:
            st.error(f"Erro ao analisar o estoque: {str(e)}")
            return {"error": f"Ocorreu um erro ao analisar o estoque: {str(e)}"}

    def generate_annual_forecast(self, short_term_report: str, purchase_history):
        """
        Pega o relatório de curto prazo, projeta para 12 meses e calcula o orçamento.
        """
        try:
            st.info("Projetando recomendação para 12 meses e calculando orçamento...")

            if not purchase_history: return {"error": "Histórico de compras insuficiente para calcular custos."}

            df_purchase = pd.DataFrame(purchase_history)
            df_purchase['value'] = df_purchase['value'].apply(PDFQA.clean_monetary_value)
            df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce').fillna(0)
            
            # --- CORREÇÃO APLICADA AQUI ---
            # Converte a data e REMOVE qualquer linha onde a data for inválida (NaT)
            df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce')
            df_purchase.dropna(subset=['date', 'value', 'quantity', 'epi_name'], inplace=True)
            
            if df_purchase.empty:
                return {"error": "Não há dados de compra válidos para calcular os custos."}

            df_purchase = df_purchase[df_purchase['quantity'] > 0].copy()
            df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
            
            # A ordenação agora é segura
            latest_costs_df = df_purchase.sort_values(by='date').drop_duplicates('epi_name', keep='last')
            
            unit_costs_str = "EPI | Custo Unit. (R$)\n---|---\n"
            for _, row in latest_costs_df.iterrows():
                unit_costs_str += f"{row['epi_name']} | {row['unit_cost']:.2f}\n"

            prompt = f"""
            **Sua Tarefa:** Você é um analista financeiro. Sua tarefa é pegar um relatório de recomendação de compra de 3 meses e projetá-lo para um período de 12 meses, calculando o orçamento anual total.

            **Dados de Entrada:**

            **1. Relatório de Recomendação de Compra (Base para 3 meses):**
            ```markdown
            {short_term_report}
            ```

            **2. Tabela de Custos Unitários Recentes (R$):**
            ```
            {unit_costs_str}
            ```

            **Instruções:**
            1.  **Leia** a seção "Recomendações de Compra (Lista Detalhada)" do relatório.
            2.  **Projete a Quantidade Anual:** Para cada item listado, multiplique a quantidade recomendada por 4 para obter a projeção para 12 meses. Arredonde para o número inteiro mais próximo.
            3.  **Calcule o Custo Total por Item:** Usando a tabela de custos, encontre o custo unitário de cada EPI e multiplique pela "Quantidade Anual".
            4.  **Calcule o Orçamento Total Anual:** Some todos os custos totais por item.
            5.  **Formate a Saída** em um relatório Markdown claro, contendo:
                - Um título: `### Previsão Orçamentária Anual de Compras`
                - Um subtítulo com o orçamento total que você calculou.
                - Uma tabela final com as colunas: `EPI`, `Qtd. Anual Recomendada`, `Custo Unit. (R$)`, `Custo Total (R$)`.
            
            **Seja preciso nos cálculos e direto na formatação.**
            """

            response = self.model.generate_content(prompt)
            try:
                final_report = response.text
            except ValueError:
                final_report = "A IA não conseguiu gerar a previsão orçamentária (bloqueio de segurança)."

            st.success("Previsão anual e orçamento gerados com sucesso!")
            return {"report": final_report}

        except Exception as e:
            # Captura a exceção real e a formata como string
            error_message = f"Um erro inesperado ocorreu: {str(e)}"
            st.error(error_message)
            return {"error": error_message}










































