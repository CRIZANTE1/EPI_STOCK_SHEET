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

class PDFQA:
    def __init__(self):
        load_api()  
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        self.embedding_model = 'models/embedding-001'

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

    def generate_budget_forecast(self, usage_history, purchase_history, forecast_months=3):
        """
        Gera uma previsão orçamentária gerencial para os próximos meses.
        """
        try:
            st.info("Iniciando a geração da previsão orçamentária...")
            
            if not usage_history:
                return {"error": "Histórico de uso insuficiente para gerar previsão."}
            if not purchase_history:
                return {"error": "Histórico de compras insuficiente para calcular custos."}
    
            # --- Preparação e Cálculos (permanecem os mesmos) ---
            df_usage = pd.DataFrame(usage_history)
            df_usage['date'] = pd.to_datetime(df_usage['date'], errors='coerce')
            df_usage['quantity'] = pd.to_numeric(df_usage['quantity'], errors='coerce')
            df_usage.dropna(subset=['date', 'quantity', 'epi_name'], inplace=True)
    
            df_purchase = pd.DataFrame(purchase_history)
            df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce')
            df_purchase['value'] = df_purchase['value'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_purchase['value'] = pd.to_numeric(df_purchase['value'], errors='coerce')
            df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce')
            df_purchase.dropna(subset=['date', 'value', 'quantity', 'epi_name'], inplace=True)
            
            df_purchase = df_purchase[df_purchase['quantity'] > 0].copy()
            df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
            latest_costs_df = df_purchase.sort_values('date').drop_duplicates('epi_name', keep='last')
            unit_costs = latest_costs_df.set_index('epi_name')['unit_cost'].to_dict()
    
            one_year_ago = datetime.now() - timedelta(days=365)
            df_usage_recent = df_usage[df_usage['date'] >= one_year_ago]
            
            if df_usage_recent.empty:
                return {"error": "Não há dados de consumo no último ano para gerar uma previsão."}
            
            df_usage_recent = df_usage_recent.set_index('date')
            monthly_consumption = df_usage_recent.groupby('epi_name').resample('M')['quantity'].sum()
            avg_monthly_consumption = monthly_consumption.groupby('epi_name').mean()
            
            forecast = []
            total_forecast_cost = 0
            
            for epi_name, avg_consumption in avg_monthly_consumption.items():
                projected_qty = np.ceil(avg_consumption * forecast_months)
                unit_cost = unit_costs.get(epi_name, 0)
                projected_cost = projected_qty * unit_cost
                total_forecast_cost += projected_cost
                
                if projected_qty > 0:
                    forecast.append({
                        "EPI": epi_name,
                        "Qtd. Prevista": int(projected_qty),
                        "Custo Unit. (R$)": f"{unit_cost:.2f}",
                        "Custo Total (R$)": f"{projected_cost:.2f}"
                    })
            
            df_forecast = pd.DataFrame(forecast)
            # Ordena a tabela pelos itens de maior custo previsto
            df_forecast = df_forecast.sort_values(by="Custo Total (R$)", ascending=False, key=lambda col: col.astype(float))
    
            # --- PROMPT DA IA MODIFICADO: Direto e Gerencial ---
            st.info("Formatando relatório gerencial...")
            prompt = f"""
            Formate os seguintes dados em um relatório orçamentário gerencial em Markdown.
    
            Dados da Previsão:
            {df_forecast.to_string(index=False)}
    
            Orçamento Total Previsto para o Período: R$ {total_forecast_cost:.2f}
    
            O relatório deve ter APENAS:
            1. Um título principal: "### Previsão Orçamentária de EPIs - Próximo Trimestre"
            2. Um subtítulo com o valor total: "#### Orçamento Total Estimado: R$ {total_forecast_cost:.2f}"
            3. A tabela de previsão exatamente como fornecida.
    
            Não adicione nenhum texto explicativo, resumo, introdução ou recomendação. Seja direto.
            """
            
            response = self.model.generate_content(prompt)
            st.success("Relatório gerencial gerado com sucesso!")
            return {"report": response.text}
    
        except Exception as e:
            st.error(f"Erro ao gerar previsão orçamentária: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}
       




   






