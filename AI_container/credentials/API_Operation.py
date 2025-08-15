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

    def generate_annual_forecast(self, stock_data_raw, employee_data, forecast_months=12):
        """
        Gera uma previsão de compra anual precisa, baseada na normalização de nomes,
        consumo real e regras de negócio.
        """
        try:
            st.info("Passo 1/5: Preparando e normalizando dados...")
    
            # --- 1. Preparação e Normalização dos Dados ---
            if not stock_data_raw or len(stock_data_raw) < 2: return {"error": "Dados de estoque insuficientes."}
            
            df_stock = pd.DataFrame(stock_data_raw[1:], columns=stock_data_raw[0])
            # Limpeza inicial
            df_stock['epi_name'] = df_stock['epi_name'].str.strip()
            df_stock['date'] = pd.to_datetime(df_stock['date'], errors='coerce')
            df_stock['quantity'] = pd.to_numeric(df_stock['quantity'], errors='coerce').fillna(0)
            df_stock['value'] = df_stock['value'].apply(PDFQA.clean_monetary_value)
            df_stock.dropna(subset=['date', 'epi_name'], inplace=True)
    
            # Criar nomes canônicos usando fuzzywuzzy
            unique_names = df_stock['epi_name'].unique()
            name_map = {name: process.extractOne(name, unique_names)[0] for name in unique_names}
            df_stock['epi_name_normalized'] = df_stock['epi_name'].map(name_map)
            
            # Separar entradas e saídas
            df_entradas = df_stock[df_stock['transaction_type'].str.lower() == 'entrada'].copy()
            df_saidas = df_stock[df_stock['transaction_type'].str.lower() == 'saída'].copy()
    
            # --- 2. Cálculo de Custo Unitário (com nomes normalizados) ---
            st.info("Passo 2/5: Calculando custos unitários...")
            df_entradas = df_entradas[df_entradas['quantity'] > 0]
            df_entradas['unit_cost'] = df_entradas['value'] / df_entradas['quantity']
            latest_costs_df = df_entradas.sort_values('date').drop_duplicates('epi_name_normalized', keep='last')
            unit_costs = latest_costs_df.set_index('epi_name_normalized')['unit_cost'].to_dict()
    
            # --- 3. Cálculo de Estoque Atual (com nomes normalizados) ---
            st.info("Passo 3/5: Calculando estoque atual...")
            total_entradas = df_entradas.groupby('epi_name_normalized')['quantity'].sum()
            total_saidas = df_saidas.groupby('epi_name_normalized')['quantity'].sum()
            current_stock = total_entradas.reindex(total_entradas.index.union(total_saidas.index), fill_value=0) - \
                            total_saidas.reindex(total_entradas.index.union(total_saidas.index), fill_value=0)
    
            # --- 4. Análise de Consumo e Projeção da Necessidade ---
            st.info("Passo 4/5: Analisando consumo e projetando necessidades anuais...")
            if df_saidas.empty: return {"error": "Não há dados de saída para análise de consumo."}
            
            total_days = (df_saidas['date'].max() - df_saidas['date'].min()).days
            num_months = total_days / 30.44 if total_days > 0 else 1
            if num_months < 1: num_months = 1
            
            total_consumption = df_saidas.groupby('epi_name_normalized')['quantity'].sum()
            avg_monthly_consumption = total_consumption / num_months
            
            recommendation_list = []
            for epi_name, avg_consumption in avg_monthly_consumption.items():
                projected_qty = np.ceil(avg_consumption * forecast_months)
                
                # REGRA DE NEGÓCIO: Mínimo de 100 para uniformes
                is_uniform = any(keyword in epi_name.upper() for keyword in ['CALÇA', 'CAMISA', 'JAPONA', 'JAQUETA'])
                if is_uniform and projected_qty < 100:
                    projected_qty = 100
                    justification = "Ajuste para estoque mínimo de uniformes (100 unidades)"
                else:
                    justification = "Projeção de consumo anual"
    
                stock = current_stock.get(epi_name, 0)
                needed_qty = max(0, projected_qty - stock)
                
                if needed_qty > 0:
                    recommendation_list.append({
                        "EPI": epi_name,
                        "Qtd. a Comprar": int(needed_qty),
                        "Justificativa": justification
                    })
    
            if not recommendation_list:
                return {"report": "## Previsão Anual\n\nEstoque atual suficiente."}
    
            # --- 5. Cálculo do Orçamento e Geração do Relatório Final ---
            st.info("Passo 5/5: Calculando orçamento e montando relatório final...")
            df_recommendation = pd.DataFrame(recommendation_list)
            df_recommendation['Custo Unit. (R$)'] = df_recommendation['EPI'].map(unit_costs).fillna(0)
            df_recommendation['Custo Total (R$)'] = df_recommendation['Qtd. a Comprar'] * df_recommendation['Custo Unit. (R$)']
            
            df_recommendation = df_recommendation.sort_values(by="Custo Total (R$)", ascending=False)
            total_cost = df_recommendation['Custo Total (R$)'].sum()
            formatted_total_cost = '{:_.2f}'.format(total_cost).replace('.', ',').replace('_', '.')
            
            df_display = df_recommendation.copy()
            df_display['Custo Unit. (R$)'] = df_display['Custo Unit. (R$)'].map('R$ {:,.2f}'.format).str.replace(',', 'v').str.replace('.', ',').str.replace('v', '.')
            df_display['Custo Total (R$)'] = df_display['Custo Total (R$)'].map('R$ {:,.2f}'.format).str.replace(',', 'v').str.replace('.', ',').str.replace('v', '.')
            
            report_title = f"### Previsão de Compras para {forecast_months} Meses"
            report_subtitle = f"#### Orçamento Total Estimado: {formatted_total_cost}"
            table_md = df_display.to_markdown(index=False)
            final_report = f"{report_title}\n{report_subtitle}\n\n{table_md}"
    
            st.success("Previsão de compras gerada com sucesso!")
            return {"report": final_report}
    
        except Exception as e:
            st.error(f"Erro ao gerar previsão de compras: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}










































