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

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class PDFQA:
    def __init__(self):
        self.genai_api = load_api()
        if not self.genai_api:
            st.error("Falha ao carregar a API do Google Generative AI.")
            return

     
        try:
            google_api_key = st.secrets["general"]["GOOGLE_API_KEY"]
        except (KeyError, TypeError):
            google_api_key = os.getenv('GOOGLE_API_KEY')

        if not google_api_key:
            st.error("Chave GOOGLE_API_KEY não encontrada. Verifique os secrets ou o .env")
            return
            
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        
        # Passa a chave explicitamente
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=google_api_key,
            temperature=0.1,
            safety_settings=safety_settings
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=google_api_key
        )
        
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

    def _create_knowledge_base(self, stock_data, purchase_history, employee_data):
        """
        Cria uma base de conhecimento vetorial a partir de todos os dados da empresa.
        """
        st.info("Criando base de conhecimento vetorial (embeddings)...")
        documents = []

        # 1. Fatos sobre Custo e Descrição dos Itens
        df_purchase = pd.DataFrame(purchase_history)
        df_purchase['date'] = pd.to_datetime(df_purchase['date'], errors='coerce')
        df_purchase['value'] = df_purchase['value'].apply(self.clean_monetary_value)
        df_purchase['quantity'] = pd.to_numeric(df_purchase['quantity'], errors='coerce').fillna(1)
        df_purchase = df_purchase[df_purchase['quantity'] > 0].copy()
        df_purchase.dropna(subset=['date', 'value', 'quantity'], inplace=True)
        df_purchase['unit_cost'] = df_purchase['value'] / df_purchase['quantity']
        latest_costs_df = df_purchase.sort_values('date', ascending=False).drop_duplicates('epi_name', keep='first')
        for _, row in latest_costs_df.iterrows():
            doc_content = f"Item: '{row['epi_name']}', Categoria: EPI, Custo Unitário: R${row['unit_cost']:.2f}, CA: {row.get('CA', 'N/A')}"
            documents.append(Document(page_content=doc_content))

        # 2. Fatos sobre Necessidades dos Funcionários
        df_employees = pd.DataFrame(employee_data[1:], columns=employee_data[0])
        uniform_needs_str = df_employees[['Empregado', 'Tamanho Camisa Manga Comprida', 'Tamanho Calça', 'Tamanho do calçado']].to_string(index=False)
        documents.append(Document(page_content=f"Necessidades de Uniformes por Funcionário:\n{uniform_needs_str}"))
        total_calcas = pd.to_numeric(df_employees['Quantidade de Calças'], errors='coerce').sum()
        documents.append(Document(page_content=f"Fato de Necessidade: A necessidade total de calças para todos os funcionários é de {total_calcas} unidades."))
        total_calcados = pd.to_numeric(df_employees['Quantidade de Calçado'], errors='coerce').sum()
        documents.append(Document(page_content=f"Fato de Necessidade: A necessidade total de calçados para todos os funcionários é de {total_calcados} unidades."))


        # 3. Fatos sobre Estoque Atual
        df_stock = pd.DataFrame(list(stock_data.items()), columns=['EPI', 'Estoque_Atual'])
        stock_str = df_stock.to_string(index=False)
        documents.append(Document(page_content=f"Estoque Atual de Itens:\n{stock_str}"))

        if not documents:
            return None
        # Usa FAISS para criar o banco de dados vetorial
        vector_store = FAISS.from_documents(documents, self.embeddings)
        st.success(f"Base de conhecimento criada com {len(documents)} fatos relevantes.")
        # Retorna um "retriever" que busca os 'k' documentos mais relevantes
        return vector_store.as_retriever(search_kwargs={"k": 50})

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

    
    
    def generate_costing_report(self, stock_data, purchase_history, usage_history, employee_data):
        """
        Gera o Relatório de Custeio completo usando a abordagem RAG.
        """
        try:
            # Chama a função que estava faltando para criar o retriever
            retriever = self._create_knowledge_base(stock_data, purchase_history, employee_data)
            if not retriever:
                return {"error": "Não foi possível criar a base de conhecimento a partir dos dados."}

            # Template do Prompt para guiar a IA
            prompt_template = """
            Você é um especialista sênior em Segurança do Trabalho e Gestão de Estoque, responsável por criar o "Relatório de Custeio SSMAS BAERI".
            Use os "Fatos Relevantes" extraídos da base de dados para responder à pergunta.

            **Fatos Relevantes:**
            {context}

            **Pergunta:**
            {question}

            **Sua Resposta (O Relatório Completo em Markdown):**
            """
            PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": PROMPT}
            )

            # A "pergunta" que guia a IA a montar o relatório no formato desejado
            question = """
            Com base nos fatos fornecidos, gere o "Relatório de Custeio SSMAS BAERI" completo para o próximo ano.
            O relatório deve ter a seguinte estrutura em Markdown:
            1. Título Principal: `## Relatório de Custeio SSMAS BAERI`
            2. Seção "Totais por Categoria": Crie uma tabela com `Categoria` e `Total (R$)`. Calcule e preencha os valores para `EPI` e `Uniforme`.
            3. Seção "Pares de uniformes por tamanho e gênero": Use os fatos da planilha de funcionários para listar a quantidade necessária de cada item por gênero e tamanho.
            4. Seção "Lista Detalhada de Itens": Crie uma tabela com `Descrição`, `Quantidade`, `Categoria`, `Valor Unit.`, `CA`. Para cada item, determine a quantidade anual necessária e preencha todas as colunas com os dados relevantes encontrados nos fatos.
            Seja preciso nos cálculos e siga a estrutura do relatório de referência o mais fielmente possível.
            """
            
            st.info("IA está consultando a base de conhecimento e gerando o relatório de custeio...")
            response = qa_chain.invoke({"query": question}) # Use .invoke() para LangChain
            final_report = response.get("result", "Não foi possível gerar a análise.")

            st.success("Relatório de Custeio gerado com sucesso!")
            return {"report": final_report}

        except Exception as e:
            st.error(f"Erro ao gerar relatório com RAG: {str(e)}")
            st.exception(e)
            return {"error": f"Ocorreu um erro inesperado: {str(e)}"}
































