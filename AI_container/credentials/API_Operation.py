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
from datetime import datetime, timedelta
from io import StringIO
import re
import numpy as np
import json


class PDFQA:
    def __init__(self):
        load_api()  
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.embedding_model = 'models/embedding-001'
        
    @staticmethod
    def clean_monetary_value(value):
        if pd.isna(value) or value == '':
            return 0.0
        
        s = str(value).strip()
        
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')

        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

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


    def stock_analysis(self, stock_data, purchase_history=None, usage_history=None):
        """
        Analisa dados de estoque e fornece recomendações de compra
        
        Args:
            stock_data (dict): Dados atuais do estoque com quantidades
            purchase_history (dict, optional): Histórico de compras
            usage_history (dict, optional): Histórico de uso dos EPIs
            
        Returns:
            dict: Recomendações de compra e análise de estoque
        """
        try:
            st.info("Analisando estoque e gerando recomendações...")
            sheet_operations = SheetOperations()
            employee_data = None
            try:
                emp_data = sheet_operations.carregar_dados_funcionarios()
                if emp_data:
                    employee_data = pd.DataFrame(emp_data[1:], columns=emp_data[0])
            except Exception as e:
                logging.warning(f"Não foi possível carregar dados dos funcionários: {e}")
                
            epi_replacement_info = {
                "Botina": {
                    "periodicidade_troca": "6 meses",
                    "vida_util_estoque": "12 meses (solado derrete após 1 ano em estoque)",
                    "observacoes": "Necessário considerar vida útil limitada em estoque"
                },
                "Luva CA 28011": {
                    "periodicidade_troca": {
                        "grupo_1": "2 semanas (50% dos funcionários)",
                        "grupo_2": "1 mês (50% dos funcionários)"
                    },
                    "observacoes": "Alta rotatividade, consumo variável entre funcionários"
                },
                "Cinto de Segurança": {
                    "periodicidade_troca": "6 meses",
                    "observacoes": "Troca semestral programada"
                },
                "Camisa": {
                    "periodicidade_troca": "6 meses",
                    "observacoes": "Troca semestral mínima"
                },
                "Calça": {
                    "periodicidade_troca": "6 meses",
                    "observacoes": "Troca semestral mínima"
                }
            }
            
            employee_context = ""
            if employee_data is not None:
                size_counts = {
                    'Camisa Manga Comprida': employee_data['Tamanho Camisa Manga Comprida'].value_counts().to_dict(),
                    'Calça': employee_data['Tamanho Calça'].value_counts().to_dict(),
                    'Jaleco': employee_data['Tamanho Jaleco para laboratório'].value_counts().to_dict(),
                    'Camisa Polo': employee_data['Tamanho Camisa Polo'].value_counts().to_dict(),
                    'Japona de Lã': employee_data['Tamanho de Japona de Lã (para frio)'].value_counts().to_dict(),
                    'Jaqueta': employee_data['Tamanho Jaquetas (para frio)'].value_counts().to_dict(),
                    'Calçado': employee_data['Tamanho do calçado'].value_counts().to_dict()
                }
                
                total_needs = {
                    'Calça': employee_data['Quantidade de Calças'].sum(),
                    'Jaleco': employee_data['Quantidade de Jalecos'].sum(),
                    'Camisa Polo': employee_data['Quantidade de Camisa Polo'].sum(),
                    'Japona de Lã': employee_data['Quantidade de Japona de Lã'].sum(),
                    'Jaqueta': employee_data['Quantidade de Jaquetas'].sum(),
                    'Calçado': employee_data['Quantidade de Calçado'].sum()
                }
                area_analysis = employee_data.groupby('Área de Atuação').size().to_dict()
                gender_analysis = employee_data.groupby('Gênero').size().to_dict()
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
               - Importante manter estoque controlado devido à vida útil limitada
            
            2. Luvas CA 28011:
               - 50% dos funcionários trocam a cada 2 semanas
               - 50% dos funcionários trocam a cada 1 mês
               - Necessário manter estoque adequado para alta rotatividade
            
            3. Cinto de Segurança:
               - Troca programada a cada 6 meses
            
            4. Uniformes (Camisas e Calças):
               - Troca mínima a cada 6 meses
               - Considerar necessidade de trocas extras em casos específicos
            
            Com base nos dados fornecidos, analise de forma minimalista (direto ao ponto):
            1. Quais itens estão com estoque baixo e precisam ser reabastecidos
            2. Quais itens têm alto consumo e devem ter prioridade de compra
            3. Se existe algum padrão de consumo que deva ser considerado
            4. Uma lista de recomendações de compra com quantidades sugeridas, considerando:
               - Os tamanhos necessários
               - A periodicidade de troca de cada EPI
            5. Sugestão de cronograma de compras para evitar:
               - Excesso de estoque que possa deteriorar
            6. Quando indicar compra seja especifico, indique o EPI o CA e a quantidade especifica.   
            """
            response = self.model.generate_content(context)
            recommendations = response.text
            
            st.success("Análise de estoque concluída com sucesso.")
            
            return {
                "recommendations": recommendations,
                "timestamp": time.time()
            }
            
        except Exception as e:
            st.error(f"Erro ao analisar o estoque: {str(e)}")
            st.exception(e)
            return {
                "error": f"Ocorreu um erro ao analisar o estoque: {str(e)}",
                "timestamp": time.time()
            }

    
    
    def generate_comprehensive_annual_forecast(self, stock_data, purchase_history, usage_history, employee_data):
        """
        Gera uma análise de estoque completa e uma lista de compras anual robusta,
        usando dados sumarizados para evitar exceder a cota de tokens.
        """
        try:
            st.info("Iniciando análise completa de estoque e necessidades anuais...")
            
            # --- 1. SUMARIZAÇÃO DOS DADOS EM PYTHON ---
            st.info("Sumarizando históricos de consumo e compras...")
            
            if not usage_history: return {"error": "Histórico de uso (saídas) é necessário."}
            if not purchase_history: return {"error": "Histórico de compras (entradas) é necessário."}
            if not employee_data: return {"error": "Dados de funcionários são necessários."}
            
            # -- Sumarização do Consumo --
            df_usage = pd.DataFrame(usage_history)
            df_usage['date'] = pd.to_datetime(df_usage['date'], errors='coerce')
            df_usage['quantity'] = pd.to_numeric(df_usage['quantity'], errors='coerce').fillna(0)
            df_usage.dropna(subset=['date', 'quantity'], inplace=True)
            total_days = (df_usage['date'].max() - df_usage['date'].min()).days
            num_months = total_days / 30.44 if total_days > 0 else 1
            if num_months < 1: num_months = 1
            consumption_summary = df_usage.groupby('epi_name')['quantity'].sum().reset_index()
            consumption_summary.rename(columns={'quantity': 'Consumo Total no Período'}, inplace=True)
            consumption_summary['Consumo Médio Mensal'] = (consumption_summary['Consumo Total no Período'] / num_months).round(2)
    
            # -- Sumarização dos Custos --
            df_purchase = pd.DataFrame(purchase_history)
            df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce')
            df_purchase['value'] = df_purchase['value'].apply(PDFQA.clean_monetary_value)
            df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce').fillna(0)
            df_purchase = df_purchase[df_purchase['quantity'] > 0].copy()
            df_purchase.dropna(subset=['date', 'value', 'quantity'], inplace=True)
            df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
            latest_costs_df = df_purchase.sort_values('date').drop_duplicates('epi_name', keep='last')
            unit_costs_summary = latest_costs_df[['epi_name', 'unit_cost']]
            unit_costs_summary.rename(columns={'unit_cost': 'Custo Unitário Recente (R$)'}, inplace=True)
    
            # -- Sumarização dos Dados dos Funcionários --
            df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])
            employee_summary = {
                "Total de Funcionários": len(df_employees),
                "Necessidade Total de Calças": pd.to_numeric(df_employees['Quantidade de Calças'], errors='coerce').sum(),
                "Necessidade Total de Calçados": pd.to_numeric(df_employees['Quantidade de Calçado'], errors='coerce').sum(),
                "Distribuição de Tamanhos (Calça)": df_employees['Tamanho Calça'].value_counts().to_dict(),
                "Distribuição de Tamanhos (Calçado)": df_employees['Tamanho do calçado'].value_counts().to_dict()
            }
            
            # --- 2. Preparação do Prompt com Dados Sumarizados ---
            stock_str = pd.DataFrame(list(stock_data.items()), columns=['EPI', 'Estoque Atual']).to_markdown(index=False)
            consumption_str = consumption_summary.to_markdown(index=False)
            costs_str = unit_costs_summary.to_markdown(index=False)
            employee_str = json.dumps(employee_summary, indent=2, ensure_ascii=False)
    
            st.info("Enviando dados sumarizados para análise da IA...")
            prompt = f"""
            **Sua Tarefa:** Você é um especialista sênior em Segurança do Trabalho e Gestão de Estoque. Sua tarefa é realizar uma análise completa dos dados sumarizados e gerar uma **"Lista de Compras Anual"** com o respectivo orçamento.
    
            **Dados Sumarizados Disponíveis:**
    
            **1. Estoque Atual:**
            ```markdown
            {stock_str}
            ```
    
            **2. Resumo do Consumo Histórico:**
            ```markdown
            {consumption_str}
            ```
    
            **3. Resumo das Necessidades dos Funcionários (para Uniformes e Calçados):**
            ```json
            {employee_str}
            ```
    
            **4. Custos Unitários Mais Recentes:**
            ```markdown
            {costs_str}
            ```
    
            **5. Regras de Negócio Cruciais:**
            - **Periodicidade de Troca:** Uniformes e Calçados são trocados a cada 6 meses (ou seja, a necessidade anual é 2x a quantidade listada nos dados dos funcionários).
            - **Estoque Mínimo de Segurança:** O estoque nunca deve ficar abaixo de 2 unidades. Se a sua previsão de compra resultar em um estoque final menor que 2, ajuste a quantidade.
    
            **Instruções para o Relatório Final:**
    
            Com base em **TODA a informação sumarizada**, gere um relatório em Markdown com as seguintes seções:
    
            **Seção 1: Lista de Compras Anual Recomendada**
            - Crie uma tabela com as colunas: `EPI`, `Qtd. a Comprar`, `Custo Unit. (R$)`, `Custo Total (R$)`.
            - Para cada EPI, determine a `Qtd. a Comprar` para o próximo ano.
            - Para Uniformes e Calçados, use o resumo dos funcionários e a regra de troca.
            - Para outros EPIs, use o resumo de consumo.
            - **Subtraia o Estoque Atual** da necessidade anual para encontrar a quantidade a comprar.
            - Aplique a regra de estoque mínimo.
            - Use a tabela de Custos para encontrar o `Custo Unit. (R$)`.
            - Calcule o `Custo Total (R$)` para cada linha.
            - No final da tabela, some tudo e apresente o **"Orçamento Total Previsto"**.
    
            **Seção 2: Justificativa da Análise**
            - Em um parágrafo curto, explique como você chegou a essa lista, mencionando como combinou as diferentes fontes de dados.
    
            **Aja como um verdadeiro especialista.**
            """
    
            response = self.model.generate_content(prompt)
            
            try:
                final_report = response.text
            except ValueError:
                final_report = "A IA não conseguiu gerar a análise (bloqueio de segurança)."
    
            st.success("Análise de estoque e recomendações geradas com sucesso!")
            return {"report": final_report}
    
        except Exception as e:
            st.error(f"Erro ao gerar análise de estoque: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}

























