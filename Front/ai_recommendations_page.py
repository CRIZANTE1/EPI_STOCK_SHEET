import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
import os
import re

# Adicionar o diretório pai ao path para import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from AI_container.credentials.API_Operation import PDFQA

def extract_purchase_recommendations(text):
    """
    Extrai recomendações de compra do texto da IA e retorna como DataFrame
    """
    lines = text.split('\n')
    recommendations = []
    
    for line in lines:
        # Procura por padrões que indiquem uma recomendação de compra
        if any(keyword in line.lower() for keyword in ['comprar', 'adquirir', 'necessário']):
            # Tenta extrair quantidade, EPI e CA
            quantity_match = re.search(r'(\d+)', line)
            ca_match = re.search(r'CA (\d+)', line)
            
            if quantity_match:
                quantity = int(quantity_match.group(1))
                epi = line.split('CA')[0] if 'CA' in line else line
                epi = re.sub(r'\d+', '', epi).strip()
                epi = re.sub(r'^[-•\s]+', '', epi)
                ca = ca_match.group(1) if ca_match else 'N/A'
                
                recommendations.append({
                    'EPI': epi,
                    'Quantidade': quantity,
                    'CA': ca
                })
    
    return pd.DataFrame(recommendations) if recommendations else None

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
        epi_exits = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum().fillna(0)
        
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
        
        # Criar DataFrame para visualização
        stock_df = pd.DataFrame(list(stock_data.items()), columns=['EPI', 'Quantidade'])
        stock_df = stock_df.sort_values(by='Quantidade')
        
        # Criar gráfico de barras usando st.bar_chart
        st.bar_chart(
            data=stock_df.set_index('EPI'),
            height=400
        )
        
        # Separar os itens em críticos (<=0) e normais (>0)
        critical_items = {k: v for k, v in stock_data.items() if v <= 0}
        normal_items = {k: v for k, v in stock_data.items() if v > 0}
        
        # Exibir itens críticos
        if critical_items:
            st.error("⚠️ Itens com Estoque Crítico")
            critical_df = pd.DataFrame(list(critical_items.items()), columns=['EPI', 'Quantidade'])
            st.dataframe(critical_df, use_container_width=True)
        
        # Seção para análise de IA
        st.subheader("Análise de Estoque por Inteligência Artificial")
        
        # Botão para gerar recomendações
        if st.button("Gerar Recomendações de Compra"):
            with st.spinner("Analisando dados de estoque e gerando recomendações..."):
                recommendations = ai_engine.stock_analysis(
                    stock_data, 
                    purchase_history,
                    usage_history
                )
                
                if "error" in recommendations:
                    st.error(recommendations["error"])
                else:
                    # Exibir as recomendações em formato de texto
                    st.markdown("### Análise Geral")
                    st.markdown(recommendations["recommendations"])
                    
                    # Extrair e exibir recomendações de compra em tabela
                    st.markdown("### Recomendações de Compra")
                    purchase_df = extract_purchase_recommendations(recommendations["recommendations"])
                    if purchase_df is not None:
                        st.dataframe(
                            purchase_df.style.highlight_max(subset=['Quantidade'], color='red'),
                            use_container_width=True
                        )
                    else:
                        st.info("Nenhuma recomendação específica de compra foi identificada.")
                    
                    # Salvar as recomendações no histórico
                    if 'recommendation_history' not in st.session_state:
                        st.session_state.recommendation_history = []
                    
                    st.session_state.recommendation_history.append({
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "recommendations": recommendations["recommendations"],
                        "purchase_df": purchase_df
                    })
        
        # Exibir histórico de recomendações
        if 'recommendation_history' in st.session_state and st.session_state.recommendation_history:
            st.subheader("Histórico de Recomendações")
            
            for i, rec in enumerate(reversed(st.session_state.recommendation_history)):
                with st.expander(f"Recomendação de {rec['timestamp']}"):
                    st.markdown("#### Análise")
                    st.markdown(rec["recommendations"])
                    
                    st.markdown("#### Recomendações de Compra")
                    if rec.get("purchase_df") is not None:
                        st.dataframe(rec["purchase_df"], use_container_width=True)
                    else:
                        st.info("Nenhuma recomendação específica de compra foi identificada.")
                
                if i >= 4:
                    break
    
    except Exception as e:
        st.error(f"Erro ao analisar dados de estoque: {str(e)}")
        st.exception(e) 
