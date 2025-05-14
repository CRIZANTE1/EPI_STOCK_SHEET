import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def analytics_page():
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>Análise de EPIs</h1>", unsafe_allow_html=True)
    
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
    
    # Pré-processamento dos dados
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    
    # Filtro lateral compacto
    with st.sidebar:
        st.markdown("### Filtros")
        
        # Filtro tipo de transação
        tipo_transacao = st.radio(
            "Tipo de Análise:",
            options=["Saídas", "Entradas", "Ambas"],
            horizontal=True
        )
        
        # Filtro de período
        periodo_opcoes = ["Últimos 30 dias", "Últimos 90 dias", "Últimos 6 meses", "Último ano", "Todo período"]
        periodo = st.selectbox("Período:", periodo_opcoes)
        
        # Filtro de visualização
        modo_visualizacao = st.radio(
            "Modo de Visualização:",
            options=["Dashboard", "Detalhado"],
            horizontal=True,
            index=0
        )
    
    # Aplicar filtros
    hoje = datetime.now().date()
    
    # Filtro de período
    if periodo == "Últimos 30 dias":
        data_inicial = hoje - timedelta(days=30)
        df = df[df['date'].dt.date >= data_inicial]
    elif periodo == "Últimos 90 dias":
        data_inicial = hoje - timedelta(days=90)
        df = df[df['date'].dt.date >= data_inicial]
    elif periodo == "Últimos 6 meses":
        data_inicial = hoje - timedelta(days=180)
        df = df[df['date'].dt.date >= data_inicial]
    elif periodo == "Último ano":
        data_inicial = hoje - timedelta(days=365)
        df = df[df['date'].dt.date >= data_inicial]
    
    # Filtro de tipo de transação
    if tipo_transacao == "Saídas":
        df = df[df['transaction_type'].str.lower().str.strip() == 'saída']
    elif tipo_transacao == "Entradas":
        df = df[df['transaction_type'].str.lower().str.strip() == 'entrada']
    
    if df.empty:
        st.info(f"Nenhum registro encontrado para os filtros aplicados.")
        return
    
    # DASHBOARD MODE - Interface simplificada
    if modo_visualizacao == "Dashboard":
        # Indicadores-chave na parte superior
        total_qtd = df['quantity'].sum()
        media_por_data = df.groupby(df['date'].dt.date)['quantity'].sum().mean()
        top_epi = df.groupby('epi_name')['quantity'].sum().idxmax()
        top_usuario = df.groupby('requester')['quantity'].sum().idxmax() if 'requester' in df.columns else "N/A"
        
        # Layout de cartões em grade
        col1, col2 = st.columns(2)
        
        with col1:
            # Cartão 1 - Volumetria
            st.markdown(
                f"""
                <div style="background-color:#f0f9ff; padding:15px; border-radius:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <h3 style="color:#1e6091; margin:0;">Quantidade Total</h3>
                    <p style="font-size:28px; font-weight:bold; color:#2E86C1; margin:5px 0;">{int(total_qtd):,}</p>
                    <p style="color:#666; margin:0; font-size:14px;">Média de {media_por_data:.1f}/dia</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Gráfico 1 - Distribuição Temporal
            st.markdown("<h4 style='margin-top:20px;'>Distribuição Temporal</h4>", unsafe_allow_html=True)
            df_temp = df.groupby(df['date'].dt.date)['quantity'].sum().reset_index()
            fig = px.line(df_temp, x='date', y='quantity', 
                          line_shape='spline', markers=True,
                          color_discrete_sequence=['#2E86C1'])
            fig.update_layout(
                xaxis_title="", yaxis_title="",
                margin=dict(l=0, r=10, t=10, b=0),
                height=200, 
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False),
                plot_bgcolor="white",
                hovermode="x"
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with col2:
            # Cartão 2 - Líderes
            st.markdown(
                f"""
                <div style="background-color:#f0f9ff; padding:15px; border-radius:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <h3 style="color:#1e6091; margin:0;">Top EPI e Requisitante</h3>
                    <p style="font-size:18px; font-weight:bold; color:#2E86C1; margin:5px 0;">EPI: {top_epi}</p>
                    <p style="font-size:18px; font-weight:bold; color:#2E86C1; margin:5px 0;">Requisitante: {top_usuario}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Gráfico 2 - Top EPIs (Donut chart)
            st.markdown("<h4 style='margin-top:20px;'>Top EPIs</h4>", unsafe_allow_html=True)
            top_epis = df.groupby('epi_name')['quantity'].sum().nlargest(5)
            
            fig = go.Figure(data=[go.Pie(
                labels=top_epis.index,
                values=top_epis.values,
                hole=.4,
                marker_colors=['#2E86C1', '#3498DB', '#5DADE2', '#85C1E9', '#AED6F1']
            )])
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=200,
                showlegend=False
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Seção de análise crítica - usando métricas para destacar pontos importantes
        st.markdown("### Análise Crítica")
        
        # Criar colunas para métricas críticas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Padrões incomuns - Requisitantes com múltiplas requisições no mesmo dia
            df_req_mesmo_dia = df.copy()
            df_req_mesmo_dia['date_only'] = df_req_mesmo_dia['date'].dt.date
            reqs_mesmo_dia = df_req_mesmo_dia.groupby(['requester', 'date_only']).size()
            reqs_multiplas = reqs_mesmo_dia[reqs_mesmo_dia > 1].count()
            
            st.metric(
                "Requisições Múltiplas/Dia", 
                reqs_multiplas,
                delta=None,
                delta_color="off"
            )
        
        with col2:
            # EPIs com maior variação
            if len(df['date'].dt.month.unique()) > 1:  # Se houver dados de mais de um mês
                df['month'] = df['date'].dt.month
                ultimo_mes = df['month'].max()
                penultimo_mes = sorted(df['month'].unique())[-2] if len(df['month'].unique()) > 1 else ultimo_mes
                
                df_ultimo = df[df['month'] == ultimo_mes]
                df_penultimo = df[df['month'] == penultimo_mes]
                
                epi_ultimo = df_ultimo.groupby('epi_name')['quantity'].sum()
                epi_penultimo = df_penultimo.groupby('epi_name')['quantity'].sum()
                
                # EPIs comuns aos dois meses
                epis_comuns = set(epi_ultimo.index) & set(epi_penultimo.index)
                
                if epis_comuns:
                    variacoes = {}
                    for epi in epis_comuns:
                        if epi_penultimo[epi] > 0:
                            variacoes[epi] = (epi_ultimo[epi] - epi_penultimo[epi]) / epi_penultimo[epi] * 100
                    
                    if variacoes:
                        epi_maior_variacao = max(variacoes.items(), key=lambda x: abs(x[1]))
                        st.metric(
                            "Maior Variação Entre Meses", 
                            f"{epi_maior_variacao[0][:15]}...",
                            f"{epi_maior_variacao[1]:.1f}%",
                            delta_color="normal"
                        )
                    else:
                        st.metric("Variação Entre Meses", "N/A")
                else:
                    st.metric("Variação Entre Meses", "N/A")
            else:
                st.metric("Variação Entre Meses", "N/A")
        
        with col3:
            # Detecção de padrões de requisição frequente
            if 'requester' in df.columns and not df.empty:
                df_sorted = df.sort_values(['requester', 'epi_name', 'date'])
                df_sorted['intervalo'] = df_sorted.groupby(['requester', 'epi_name'])['date'].diff().dt.days
                
                requisicoes_frequentes = df_sorted[
                    (df_sorted['intervalo'] <= 7) & (df_sorted['intervalo'].notna())
                ]
                
                qt_frequentes = len(requisicoes_frequentes)
                
                st.metric(
                    "Requisições Freq. (<7 dias)", 
                    qt_frequentes,
                    delta=None,
                    delta_color="off"
                )
            else:
                st.metric("Requisições Frequentes", "N/A")
        
        # Expander para detalhes das requisições frequentes
        if 'requisicoes_frequentes' in locals() and not requisicoes_frequentes.empty:
            with st.expander("📋 Ver Detalhes das Requisições Frequentes"):
                st.dataframe(
                    requisicoes_frequentes[['date', 'requester', 'epi_name', 'quantity', 'intervalo']]
                    .rename(columns={
                        'date': 'Data',
                        'requester': 'Requisitante',
                        'epi_name': 'EPI',
                        'quantity': 'Quantidade',
                        'intervalo': 'Dias'
                    })
                    .sort_values('Data', ascending=False),
                    hide_index=True,
                    use_container_width=True
                )
    
    # DETAILED MODE - Visualização mais completa
    else:
        st.subheader("Análise Detalhada")
        
        # Usar tabs para organizar diferentes análises
        tab1, tab2, tab3 = st.tabs(["📊 Estatísticas", "👥 Usuários", "⏱️ Frequência"])
        
        with tab1:
            # Estatísticas por EPI
            st.subheader("Estatísticas por EPI")
            
            # Gráfico de barras horizontal para os top 10 EPIs
            epi_stats = df.groupby('epi_name')['quantity'].agg(['sum', 'mean', 'count']).reset_index()
            epi_stats.columns = ['EPI', 'Total', 'Média', 'Contagem']
            epi_stats = epi_stats.sort_values('Total', ascending=False).head(10)
            
            fig = px.bar(
                epi_stats, 
                y='EPI', 
                x='Total',
                orientation='h',
                color='Total',
                color_continuous_scale='Blues',
                text='Total'
            )
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="",
                yaxis_title="",
                coloraxis_showscale=False
            )
            fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela completa com paginação
            with st.expander("Ver tabela completa"):
                st.dataframe(
                    epi_stats,
                    hide_index=True,
                    use_container_width=True
                )
        
        with tab2:
            if 'requester' in df.columns:
                # Análise de usuários
                st.subheader("Análise por Requisitante")
                
                # Mostrar top requisitantes
                user_stats = df.groupby('requester')['quantity'].sum().reset_index()
                user_stats.columns = ['Requisitante', 'Quantidade']
                user_stats = user_stats.sort_values('Quantidade', ascending=False).head(10)
                
                fig = px.bar(
                    user_stats,
                    x='Requisitante',
                    y='Quantidade',
                    color='Quantidade',
                    color_continuous_scale='Blues',
                    text='Quantidade'
                )
                fig.update_layout(
                    height=400,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="",
                    yaxis_title="",
                    coloraxis_showscale=False
                )
                fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
                
                # Análise cruzada: EPI por Requisitante
                st.subheader("EPIs por Requisitante")
                
                # Dropdown para selecionar requisitante
                top_users = df['requester'].value_counts().head(10).index.tolist()
                selected_user = st.selectbox("Selecione o requisitante:", top_users)
                
                # Mostrar EPIs do requisitante selecionado
                user_epis = df[df['requester'] == selected_user].groupby('epi_name')['quantity'].sum().reset_index()
                user_epis.columns = ['EPI', 'Quantidade']
                user_epis = user_epis.sort_values('Quantidade', ascending=False)
                
                if not user_epis.empty:
                    fig = px.pie(
                        user_epis.head(5), 
                        values='Quantidade', 
                        names='EPI',
                        color_discrete_sequence=px.colors.sequential.Blues_r
                    )
                    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Não há dados para o requisitante {selected_user}")
            else:
                st.info("Dados de requisitantes não disponíveis")
        
        with tab3:
            # Análise de frequência
            st.subheader("Análise de Frequência")
            
            # Controle do intervalo de dias
            dias = st.slider("Intervalo de dias para análise:", 1, 30, 7)
            
            if 'requester' in df.columns:
                df_sorted = df.sort_values(['requester', 'epi_name', 'date'])
                df_sorted['intervalo'] = df_sorted.groupby(['requester', 'epi_name'])['date'].diff().dt.days
                
                requisicoes_frequentes = df_sorted[
                    (df_sorted['intervalo'] <= dias) & (df_sorted['intervalo'].notna())
                ]
                
                if not requisicoes_frequentes.empty:
                    # Visualização das requisições frequentes
                    st.warning(f"{len(requisicoes_frequentes)} requisições feitas em intervalo menor que {dias} dias")
                    
                    # Análise por EPI - quais EPIs são mais frequentemente solicitados
                    epi_freq = requisicoes_frequentes['epi_name'].value_counts().reset_index()
                    epi_freq.columns = ['EPI', 'Contagem']
                    
                    fig = px.bar(
                        epi_freq.head(5),
                        x='EPI',
                        y='Contagem',
                        color='Contagem',
                        color_continuous_scale='Reds',
                        text='Contagem'
                    )
                    fig.update_layout(
                        height=300,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_title="",
                        yaxis_title="",
                        coloraxis_showscale=False
                    )
                    fig.update_traces(texttemplate='%{text}', textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Dados detalhados
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
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.success(f"Nenhuma requisição frequente identificada (intervalo ≤ {dias} dias)")
            else:
                st.info("Dados de requisitantes não disponíveis para análise de frequência") 
