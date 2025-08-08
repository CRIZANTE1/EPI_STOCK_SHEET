import streamlit as st
import pandas as pd
import numpy as np
from End.Operations import SheetOperations
from datetime import datetime
import plotly.express as px
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from auth import is_admin

def analytics_page():
    
    if not is_admin():
        st.error("Acesso Negado 🔒")
        st.warning("Esta página contém análises estratégicas e é restrita a administradores.")
        st.info("Por favor, selecione outra opção no menu lateral.")
        return # Impede a execução do resto do código para não-admins

    st.title("Análise de Utilização de EPIs")
    
    sheet_operations = SheetOperations()
    
    @st.cache_data(ttl=600)
    def load_analytics_data():
        
        data = sheet_operations.carregar_dados()
        if data and len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
            df.dropna(subset=['quantity'], inplace=True)
            df['quantity'] = df['quantity'].astype(int)
            
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            return df
        return pd.DataFrame()

    df_full = load_analytics_data()
    
    if df_full.empty:
        st.error("Não foi possível carregar os dados para análise ou não há dados válidos.")
        return

    # Pré-processamento dos dados de saída
    df = df_full[df_full['transaction_type'].str.lower() == 'saída'].copy()
    
    if df.empty:
        st.warning("Nenhuma transação de saída encontrada para análise.")
        return
        
    # Filtros em linha única
    col1, col2 = st.columns([1, 2])
    with col1:
        anos_disponiveis = sorted(df['date'].dt.year.unique(), reverse=True)
        ano_selecionado = st.selectbox("Ano:", anos_disponiveis)
    
    with col2:
        meses = {i: nome for i, nome in enumerate(["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                                  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], 0)}
        mes_selecionado = st.selectbox("Mês:", list(meses.values()))
    
    # Filtragem dos dados
    df_filtrado = df[df['date'].dt.year == ano_selecionado]
    if mes_selecionado != "Todos":
        mes_num = [k for k, v in meses.items() if v == mes_selecionado][0]
        df_filtrado = df_filtrado[df_filtrado['date'].dt.month == mes_num]
    
    # Métricas principais em uma linha compacta
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Requisições", len(df_filtrado))
    with col2: st.metric("Usuários Únicos", df_filtrado['requester'].nunique())
    with col3: st.metric("EPIs Únicos", df_filtrado['epi_name'].nunique())
    
    # Análise Principal em Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Tendências & Projeções", "📦 Top EPIs", "🔍 Análises Avançadas"])
    
    with tab1:
        st.subheader("Tendência de Consumo e Projeção")
        
        # Preparação de dados para análise temporal
        df_temporal = df.copy()
        df_temporal['yearmonth'] = df_temporal['date'].dt.to_period('M')
        consumo_mensal = df_temporal.groupby('yearmonth')['quantity'].sum()
        consumo_mensal = consumo_mensal.reset_index()
        consumo_mensal['yearmonth'] = consumo_mensal['yearmonth'].dt.to_timestamp()
        
        if len(consumo_mensal) >= 3:  # Precisamos de pelo menos 3 pontos para projeção
            # Criando projeção para 3 meses
            modelo = ExponentialSmoothing(
                consumo_mensal['quantity'],
                trend='add',
                seasonal=None,
                seasonal_periods=None
            )
            
            modelo_ajustado = modelo.fit()
            
            # Projetando próximos 3 meses
            ultimo_mes = consumo_mensal['yearmonth'].iloc[-1]
            proximos_meses = pd.date_range(start=ultimo_mes, periods=4, freq='M')[1:]
            
            previsao = modelo_ajustado.forecast(3)
            df_previsao = pd.DataFrame({
                'yearmonth': proximos_meses,
                'quantity': previsao.values
            })
            
            # Combinando dados históricos com projeção
            df_completo = pd.concat([
                consumo_mensal,
                df_previsao
            ])
            
            # Calculando tendência percentual
            if len(consumo_mensal) >= 2:
                variacao = ((previsao.mean() / consumo_mensal['quantity'].mean()) - 1) * 100
                tendencia_texto = f"↑ +{variacao:.1f}%" if variacao > 0 else f"↓ {variacao:.1f}%"
                st.metric("Tendência de Consumo (3 meses)", tendencia_texto)
            
            # Gráfico com dados históricos e projeção
            fig = px.line(df_completo, x='yearmonth', y='quantity', markers=True)
            fig.add_scatter(x=df_previsao['yearmonth'], y=df_previsao['quantity'], 
                           name='Projeção', line=dict(dash='dash'))
            fig.update_layout(
                xaxis_title="Período",
                yaxis_title="Quantidade",
                title="Consumo Histórico e Projeção Futura"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Dados insuficientes para gerar projeção. Necessário pelo menos 3 meses de histórico.")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            top_epis = df_filtrado.groupby('epi_name')['quantity'].sum().sort_values(ascending=False).head(5)
            fig = px.bar(top_epis, labels={'value': 'Quantidade', 'index': 'EPI'})
            fig.update_layout(title="Top 5 EPIs Mais Requisitados")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            top_users = df_filtrado.groupby('requester')['quantity'].sum().sort_values(ascending=False).head(5)
            fig = px.bar(top_users, labels={'value': 'Quantidade', 'index': 'Requisitante'})
            fig.update_layout(title="Top 5 Usuários por Volume")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Análise Compacta de Frequência
        dias_intervalo = st.slider("Identificar requisições com intervalo menor que (dias):", 1, 30, 7)
        
        # Análise de frequência simplificada
        df_ordenado = df_filtrado.sort_values(['requester', 'epi_name', 'date'])
        df_ordenado['intervalo'] = df_ordenado.groupby(['requester', 'epi_name'])['date'].diff().dt.days
        
        requisicoes_frequentes = df_ordenado[
            (df_ordenado['intervalo'] <= dias_intervalo) & 
            (df_ordenado['intervalo'].notna())
        ]
        
        if not requisicoes_frequentes.empty:
            st.warning(f"{len(requisicoes_frequentes)} requisições em intervalo menor que {dias_intervalo} dias")
            
            with st.expander("Ver Detalhes"):
                st.dataframe(
                    requisicoes_frequentes[['date', 'requester', 'epi_name', 'quantity', 'intervalo']]
                    .rename(columns={
                        'date': 'Data', 'requester': 'Requisitante', 'epi_name': 'EPI',
                        'quantity': 'Quantidade', 'intervalo': 'Dias desde última requisição'
                    })
                    .sort_values('Data', ascending=False),
                    hide_index=True
                )
        else:
            st.success("Nenhuma requisição frequente identificada no período.") 


