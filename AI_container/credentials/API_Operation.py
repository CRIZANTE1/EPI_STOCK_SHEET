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

    
    
    def generate_annual_forecast(self, usage_history, purchase_history, stock_data, forecast_months=12):
        """
        Gera uma previsão de compra anual, com quantidades ajustadas pela IA e custo recalculado em Python.
        """
        try:
            st.info("Iniciando a geração da previsão de compras anual...")
            
            # --- 1. Preparação e Cálculos em Python (Garantia de Precisão) ---
            if not usage_history: return {"error": "Histórico de uso insuficiente."}
            if not purchase_history: return {"error": "Histórico de compras insuficiente."}
            
            df_usage = pd.DataFrame(usage_history)
            df_usage['date'] = pd.to_datetime(df_usage['date'], errors='coerce')
            df_usage['quantity'] = pd.to_numeric(df_usage['quantity'], errors='coerce').fillna(0)
            df_usage.dropna(subset=['date', 'quantity', 'epi_name'], inplace=True)
    
            df_purchase = pd.DataFrame(purchase_history)
            df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce')
            df_purchase['value'] = df_purchase['value'].apply(PDFQA.clean_monetary_value)
            df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce').fillna(0)
            df_purchase.dropna(subset=['date', 'value', 'quantity', 'epi_name'], inplace=True)
            
            df_purchase = df_purchase[df_purchase['quantity'] > 0].copy()
            df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
            latest_costs_df = df_purchase.sort_values('date').drop_duplicates('epi_name', keep='last')
            unit_costs = latest_costs_df.set_index('epi_name')['unit_cost'].to_dict()
    
            if df_usage.empty: return {"error": "Não há dados de consumo válidos."}
            
            total_days_in_period = (df_usage['date'].max() - df_usage['date'].min()).days
            num_months_in_data = total_days_in_period / 30.44
            if num_months_in_data < 1: num_months_in_data = 1
    
            total_consumption_period = df_usage.groupby('epi_name')['quantity'].sum()
            avg_monthly_consumption = total_consumption_period / num_months_in_data
    
            forecast = []
            for epi_name, avg_consumption in avg_monthly_consumption.items():
                projected_qty = np.ceil(avg_consumption * forecast_months)
                current_stock = stock_data.get(epi_name, 0)
                needed_qty = max(0, projected_qty - current_stock)
                
                # Inclui o item na previsão mesmo que a necessidade seja zero, para a IA ter o contexto completo
                forecast.append({
                    "EPI": epi_name.strip(),
                    "Consumo Anual Previsto": int(projected_qty),
                    "Estoque Atual": int(current_stock),
                    "Necessidade de Compra (cálculo)": int(needed_qty),
                    "Custo Unit. (R$)": unit_costs.get(epi_name.strip(), 0)
                })
            
            if not forecast:
                return {"report": "## Previsão Anual\n\nO estoque atual é suficiente. Nenhuma compra recomendada.", "data": pd.DataFrame()}
    
            df_forecast = pd.DataFrame(forecast)
            # Filtra apenas itens que realmente precisam ser comprados
            df_forecast_to_buy = df_forecast[df_forecast['Necessidade de Compra (cálculo)'] > 0].copy()
            df_forecast_to_buy = df_forecast_to_buy.sort_values(by="Necessidade de Compra (cálculo)", ascending=False)
            
            if df_forecast_to_buy.empty:
                return {"report": "## Previsão Anual\n\nO estoque atual é suficiente. Nenhuma compra recomendada.", "data": pd.DataFrame()}
                
            # --- 2. Chamada à IA APENAS para a parte criativa (justificativas) ---
            st.info("IA está gerando recomendações e justificativas...")
            prompt_recommendation = f"""
            Você é um gestor de estoque de EPIs. A tabela abaixo mostra uma previsão de compra matemática para os próximos 12 meses.
            Sua tarefa é revisar **TODOS OS ITENS** e gerar uma tabela Markdown com as colunas: `EPI`, `Qtd. a Comprar (Recomendado)`, `Justificativa`.
    
            **Dados Calculados:**
            {df_forecast_to_buy[['EPI', 'Consumo Anual Previsto', 'Estoque Atual', 'Necessidade de Compra (cálculo)']].to_markdown(index=False)}
    
            **Instruções:**
            1. Para a coluna "Qtd. a Comprar (Recomendado)", ajuste a "Necessidade de Compra (cálculo)" usando bom senso (arredondar para pacotes, adicionar estoque de segurança).
            2. Na "Justificativa", explique o porquê do ajuste. Se não houver ajuste, use "Cálculo direto".
            3. Mantenha os nomes dos EPIs exatamente como estão, em uma única linha.
            4. **Sua resposta deve conter APENAS a tabela Markdown, sem nenhum outro texto, título ou introdução.**
            """
            
            response = self.model.generate_content(prompt_recommendation)
            try:
                recommended_table_md = response.text
            except ValueError:
                return {"error": "A IA não conseguiu gerar a lista de compras (bloqueio de segurança)."}
    
            # --- 3. Processamento Final e Cálculo de Custo em Python ---
            st.info("Calculando custo final com base nas recomendações...")
            final_report = "### Lista de Compras Anual Recomendada\n\n"
            total_cost_final = 0
            
            try:
                df_recommended = pd.read_csv(StringIO(recommended_table_md.replace('<br>', ' ')), sep='|').dropna(axis=1, how='all').iloc[1:]
                df_recommended.columns = [col.strip() for col in df_recommended.columns]
                df_recommended['EPI'] = df_recommended['EPI'].str.strip()
                df_recommended['Qtd. a Comprar (Recomendado)'] = pd.to_numeric(df_recommended['Qtd. a Comprar (Recomendado)'], errors='coerce').fillna(0)
                
                # Mapeia os custos e calcula o total
                df_recommended['Custo Unit. (R$)'] = df_recommended['EPI'].map(unit_costs)
                df_recommended.fillna({'Custo Unit. (R$)': 0}, inplace=True)
                df_recommended['Custo Total (R$)'] = df_recommended['Qtd. a Comprar (Recomendado)'] * df_recommended['Custo Unit. (R$)']
                
                total_cost_final = df_recommended['Custo Total (R$)'].sum()
                
            except Exception as e:
                logging.error(f"Erro ao processar tabela da IA, usando cálculo direto: {e}")
                # Fallback: Se a IA falhar, usa o cálculo matemático direto
                df_forecast_to_buy['Custo Total (R$)'] = df_forecast_to_buy['Necessidade de Compra (cálculo)'] * df_forecast_to_buy['Custo Unit. (R$)']
                total_cost_final = df_forecast_to_buy['Custo Total (R$)'].sum()
                recommended_table_md = df_forecast_to_buy[['EPI', 'Necessidade de Compra (cálculo)']].rename(columns={'Necessidade de Compra (cálculo)': 'Qtd. a Comprar'}).to_markdown(index=False)
                
            formatted_total_cost = '{:_.2f}'.format(total_cost_final).replace('.', ',').replace('_', '.')
            report_subtitle = f"#### Orçamento Total Estimado: R$ {formatted_total_cost}"
            final_report += f"{report_subtitle}\n\n{recommended_table_md}"
    
            st.success("Previsão de compras gerada com sucesso!")
            return {"report": final_report}
    
        except Exception as e:
            st.error(f"Erro ao gerar previsão de compras: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}


















