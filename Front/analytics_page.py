import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
import calendar

def analytics_page():
    st.title("Análise de Utilização de EPIs")
    
    sheet_operations = SheetOperations()
    
    if 'data' not in st.session_state:
        data = sheet_operations.carregar_dados()
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            st.session_state['data'] = df
        else:
            st.error("Não foi possível carregar a planilha")
            return

    df = st.session_state['data']
    
    # Pré-processamento dos dados
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df[df['transaction_type'].str.lower() == 'saída'].copy()
    
    if df.empty:
        st.warning("Nenhuma transação de saída encontrada.")
        return
        
    # Filtros de período
    col1, col2 = st.columns(2)
    with col1:
        anos_disponiveis = sorted(df['date'].dt.year.unique(), reverse=True)
        ano_selecionado = st.selectbox("Ano:", anos_disponiveis)
    
    with col2:
        meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        mes_selecionado = st.selectbox("Mês:", ["Todos"] + list(meses.values()))
    
    # Filtragem dos dados
    df_filtrado = df[df['date'].dt.year == ano_selecionado]
    if mes_selecionado != "Todos":
        mes_num = [k for k, v in meses.items() if v == mes_selecionado][0]
        df_filtrado = df_filtrado[df_filtrado['date'].dt.month == mes_num]
    
    # Layout em três colunas para métricas principais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total de Requisições",
            len(df_filtrado)
        )
    
    with col2:
        st.metric(
            "Usuários Únicos",
            df_filtrado['requester'].nunique()
        )
    
    with col3:
        st.metric(
            "EPIs Únicos",
            df_filtrado['epi_name'].nunique()
        )
    
    # Top EPIs e Usuários em tabs
    tab1, tab2 = st.tabs(["📦 Top EPIs", "👥 Top Usuários"])
    
    with tab1:
        top_epis = df_filtrado.groupby('epi_name')['quantity'].sum().sort_values(ascending=False).head(5)
        st.bar_chart(top_epis)
        
    with tab2:
        top_users = df_filtrado.groupby('requester')['quantity'].sum().sort_values(ascending=False).head(5)
        st.bar_chart(top_users)
    
    # Análise de Frequência
    st.subheader("Análise de Frequência")
    dias_intervalo = st.slider("Intervalo de dias para análise:", 1, 30, 7)
    
    df_ordenado = df_filtrado.sort_values(['requester', 'epi_name', 'date'])
    df_ordenado['intervalo'] = df_ordenado.groupby(['requester', 'epi_name'])['date'].diff().dt.days
    
    requisicoes_frequentes = df_ordenado[
        (df_ordenado['intervalo'] <= dias_intervalo) & 
        (df_ordenado['intervalo'].notna())
    ]
    
    if not requisicoes_frequentes.empty:
        st.warning(f"{len(requisicoes_frequentes)} requisições feitas em intervalo menor que {dias_intervalo} dias")
        
        with st.expander("Ver Detalhes"):
            st.dataframe(
                requisicoes_frequentes[['date', 'requester', 'epi_name', 'quantity', 'intervalo']]
                .rename(columns={
                    'date': 'Data',
                    'requester': 'Requisitante',
                    'epi_name': 'EPI',
                    'quantity': 'Quantidade',
                    'intervalo': 'Dias desde última requisição'
                })
                .sort_values('Data', ascending=False),
                hide_index=True
            )
    else:
        st.success("Nenhuma requisição frequente identificada no período selecionado.") 