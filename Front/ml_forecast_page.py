import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import plotly.graph_objects as go

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from ML.demand_forecasting import DemandForecasting
from ML.data_loader import DataLoader


def ml_forecast_page():
    """
    Página de previsão de demanda com Machine Learning.
    """
    st.title("🤖 Previsão de Demanda com Machine Learning")
    
    st.markdown("""
    Esta ferramenta utiliza algoritmos avançados de Machine Learning para prever a demanda futura de EPIs:
    
    - **XGBoost**: Modelo de gradient boosting para capturar padrões complexos
    - **Prophet**: Desenvolvido pelo Facebook para séries temporais com sazonalidade
    - **Ensemble**: Combina as previsões de ambos os modelos para maior precisão
    """)
    
    # Carregar dados usando o DataLoader
    sheet_operations = SheetOperations()
    
    @st.cache_data(ttl=300)
    def load_stock_data():
        loader = DataLoader(sheet_operations)
        df = loader.load_data()
        
        # Mostrar relatório de qualidade
        if not df.empty:
            quality = loader.get_data_quality_report(df)
            with st.expander("ℹ️ Qualidade dos Dados", expanded=False):
                col1, col2, col3 = st.columns(3)
                col1.metric("Registros", quality['total_registros'])
                col2.metric("EPIs Únicos", quality['epis_unicos'])
                col3.metric("Período (dias)", 
                           (pd.to_datetime(quality['periodo']['fim']) - 
                            pd.to_datetime(quality['periodo']['inicio'])).days)
        
        return df
    
    df = load_stock_data()
    
    if df.empty:
        st.error("Não foi possível carregar os dados de estoque.")
        st.info("Verifique se há registros na planilha e se as colunas estão corretas.")
        return
    
    # Diagnóstico de dados
    with st.expander("🔧 Diagnóstico de Dados", expanded=False):
        st.markdown("### Verificar Estrutura dos Dados")
        
        if st.button("Executar Diagnóstico"):
            st.markdown("#### Primeiros 10 Registros")
            st.dataframe(df.head(10))
            
            st.markdown("#### Tipos de Dados")
            st.code(str(df.dtypes))
            
            st.markdown("#### Valores Únicos por Coluna")
            for col in df.columns:
                unique_count = df[col].nunique()
                st.write(f"- **{col}**: {unique_count} valores únicos")
            
            st.markdown("#### Distribuição de Transações")
            trans_dist = df['transaction_type'].value_counts()
            st.bar_chart(trans_dist)
    
    # Inicializar modelo
    forecaster = DemandForecasting()
    
    # Preparar dados
    with st.spinner("Preparando dados para análise..."):
        df_prepared = forecaster.prepare_data(df)
    
    if df_prepared.empty:
        st.warning("Dados insuficientes para previsão. É necessário ter pelo menos 30 dias de histórico.")
        return
    
    # Estatísticas gerais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("EPIs Únicos", df_prepared['epi_name'].nunique())
    with col2:
        st.metric("Dias de Histórico", (df_prepared['date'].max() - df_prepared['date'].min()).days)
    with col3:
        st.metric("Total de Transações", len(df_prepared))
    with col4:
        avg_daily = df_prepared.groupby('date')['quantity'].sum().mean()
        st.metric("Média Diária", f"{avg_daily:.1f}")
    
    st.markdown("---")
    
    # Tabs principais
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Previsão de Demanda", 
        "🎯 Recomendações de Compra", 
        "📈 Análise de Sazonalidade",
        "🔍 Métricas dos Modelos",
        "⚡ Análise de Performance"
    ])
    
    # TAB 1: PREVISÃO
    with tab1:
        st.subheader("Previsão de Demanda Futura")
        
        # Seletor de EPI
        epis_disponiveis = sorted(df_prepared['epi_name'].unique())
        selected_epi = st.selectbox(
            "Selecione o EPI para análise:",
            epis_disponiveis,
            key="epi_forecast"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            days_ahead = st.slider(
                "Dias para previsão:",
                min_value=30,
                max_value=180,
                value=90,
                step=15
            )
        with col2:
            confidence_interval = st.slider(
                "Nível de confiança (%):",
                min_value=80,
                max_value=99,
                value=95
            )
        
        if st.button("🚀 Gerar Previsão", type="primary", key="btn_forecast"):
            with st.spinner(f"Treinando modelos e gerando previsão para {selected_epi}..."):
                
                # Criar barra de progresso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Preparando dados...")
                progress_bar.progress(20)
                
                status_text.text("Treinando modelo XGBoost...")
                progress_bar.progress(40)
                
                status_text.text("Treinando modelo Prophet...")
                progress_bar.progress(60)
                
                # Fazer previsão
                predictions = forecaster.predict_future_demand(
                    df_prepared, 
                    selected_epi, 
                    days_ahead
                )
                
                status_text.text("Gerando visualizações...")
                progress_bar.progress(80)
                
                if predictions is not None:
                    # Salvar no session state
                    st.session_state['last_prediction'] = predictions
                    st.session_state['last_epi'] = selected_epi
                    
                    progress_bar.progress(100)
                    status_text.text("Concluído!")
                    
                    # Métricas de resumo
                    st.markdown("### 📊 Resumo da Previsão")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    total_demand = predictions['ensemble_prediction'].sum()
                    avg_daily_demand = predictions['ensemble_prediction'].mean()
                    max_demand = predictions['ensemble_prediction'].max()
                    min_demand = predictions['ensemble_prediction'].min()
                    
                    col1.metric("Demanda Total Prevista", f"{total_demand:.0f}")
                    col2.metric("Média Diária", f"{avg_daily_demand:.1f}")
                    col3.metric("Pico Máximo", f"{max_demand:.0f}")
                    col4.metric("Mínimo", f"{min_demand:.0f}")
                    
                    # Gráfico de previsão
                    st.markdown("### 📈 Visualização da Previsão")
                    fig = forecaster.plot_forecast(df_prepared, predictions, selected_epi)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Comparação dos modelos
                    st.markdown("### 🔄 Comparação dos Modelos")
                    
                    comparison_df = predictions[['date', 'prophet_prediction', 'xgboost_prediction', 'ensemble_prediction']].copy()
                    comparison_df.columns = ['Data', 'Prophet', 'XGBoost', 'Ensemble']
                    
                    st.line_chart(comparison_df.set_index('Data'))
                    
                    # Tabela de dados
                    with st.expander("📋 Ver Dados Detalhados"):
                        display_df = predictions.copy()
                        display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
                        display_df = display_df.rename(columns={
                            'date': 'Data',
                            'ensemble_prediction': 'Previsão',
                            'lower_bound': 'Limite Inferior',
                            'upper_bound': 'Limite Superior'
                        })
                        st.dataframe(
                            display_df[['Data', 'Previsão', 'Limite Inferior', 'Limite Superior']],
                            hide_index=True
                        )
                    
                    # Limpar
                    progress_bar.empty()
                    status_text.empty()
                    
                else:
                    st.error("Não foi possível gerar a previsão. Verifique se há dados suficientes.")
                    progress_bar.empty()
                    status_text.empty()
    
    # TAB 2: RECOMENDAÇÕES DE COMPRA
    with tab2:
        st.subheader("🎯 Recomendações de Compra Baseadas em ML")
        
        st.markdown("""
        As recomendações consideram:
        - Previsão de demanda dos próximos 90 dias
        - Estoque atual
        - Estoque de segurança (baseado na variabilidade da demanda)
        - Priorização inteligente
        """)
        
        # Calcular estoque atual
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['transaction_type'] = df['transaction_type'].str.lower().str.strip()
        
        epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
        epi_exits = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum()
        
        all_epis = epi_entries.index.union(epi_exits.index)
        current_stock = (epi_entries.reindex(all_epis, fill_value=0) - 
                        epi_exits.reindex(all_epis, fill_value=0)).to_dict()
        
        safety_days = st.slider(
            "Dias de estoque de segurança:",
            min_value=7,
            max_value=60,
            value=30,
            help="Quantidade de dias de demanda média a manter como margem de segurança"
        )
        
        if st.button("📊 Gerar Recomendações", type="primary", key="btn_recommendations"):
            with st.spinner("Gerando recomendações inteligentes..."):
                
                all_predictions = []
                epis_to_analyze = df_prepared['epi_name'].unique()
                
                progress = st.progress(0)
                for idx, epi in enumerate(epis_to_analyze):
                    pred = forecaster.predict_future_demand(df_prepared, epi, 90)
                    if pred is not None:
                        all_predictions.append(pred)
                    progress.progress((idx + 1) / len(epis_to_analyze))
                
                progress.empty()
                
                if all_predictions:
                    all_predictions_df = pd.concat(all_predictions, ignore_index=True)
                    
                    # Gerar recomendações
                    recommendations = forecaster.generate_purchase_recommendations(
                        all_predictions_df,
                        current_stock,
                        safety_days
                    )
                    
                    # Salvar no session state
                    st.session_state['recommendations'] = recommendations
                    
                    # Exibir resumo
                    st.markdown("### 📋 Resumo das Recomendações")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    criticas = len(recommendations[recommendations['prioridade'] == 'CRÍTICA'])
                    altas = len(recommendations[recommendations['prioridade'] == 'ALTA'])
                    
                    col1.metric("Compras Críticas", criticas, delta="Atenção!", delta_color="inverse")
                    col2.metric("Compras Alta Prioridade", altas)
                    col3.metric("Total de EPIs", len(recommendations))
                    
                    # Filtro por prioridade
                    st.markdown("### 🎯 Recomendações por Prioridade")
                    
                    prioridades = ['TODAS'] + recommendations['prioridade'].unique().tolist()
                    selected_priority = st.selectbox("Filtrar por prioridade:", prioridades)
                    
                    if selected_priority != 'TODAS':
                        filtered_recs = recommendations[recommendations['prioridade'] == selected_priority]
                    else:
                        filtered_recs = recommendations
                    
                    # Tabela de recomendações
                    display_recs = filtered_recs.copy()
                    display_recs = display_recs.rename(columns={
                        'epi': 'EPI',
                        'estoque_atual': 'Estoque Atual',
                        'demanda_prevista_90d': 'Demanda 90d',
                        'demanda_media_diaria': 'Média Diária',
                        'quantidade_recomendada': 'Qtd. Recomendada',
                        'prioridade': 'Prioridade',
                        'dias_cobertura': 'Dias de Cobertura'
                    })
                    
                    # Formatação
                    display_recs['Estoque Atual'] = display_recs['Estoque Atual'].apply(lambda x: f"{x:.0f}")
                    display_recs['Demanda 90d'] = display_recs['Demanda 90d'].apply(lambda x: f"{x:.0f}")
                    display_recs['Média Diária'] = display_recs['Média Diária'].apply(lambda x: f"{x:.1f}")
                    display_recs['Qtd. Recomendada'] = display_recs['Qtd. Recomendada'].apply(lambda x: f"{x:.0f}")
                    display_recs['Dias de Cobertura'] = display_recs['Dias de Cobertura'].apply(
                        lambda x: f"{x:.0f}" if x < 999 else "∞"
                    )
                    
                    st.dataframe(
                        display_recs[['EPI', 'Estoque Atual', 'Demanda 90d', 
                                     'Média Diária', 'Qtd. Recomendada', 
                                     'Dias de Cobertura', 'Prioridade']],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Gráfico de priorização
                    st.markdown("### 📊 Visualização de Prioridades")
                    
                    import plotly.express as px
                    
                    fig = px.bar(
                        recommendations,
                        x='epi',
                        y='quantidade_recomendada',
                        color='prioridade',
                        title='Quantidade Recomendada por EPI',
                        labels={
                            'epi': 'EPI',
                            'quantidade_recomendada': 'Quantidade',
                            'prioridade': 'Prioridade'
                        },
                        color_discrete_map={
                            'CRÍTICA': '#FF4444',
                            'ALTA': '#FF8800',
                            'MÉDIA': '#FFBB00',
                            'BAIXA': '#00CC66'
                        }
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Exportar recomendações
                    st.markdown("### 💾 Exportar Recomendações")
                    
                    csv = recommendations.to_csv(index=False)
                    st.download_button(
                        label="📥 Baixar CSV",
                        data=csv,
                        file_name=f"recomendacoes_compra_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                    
                else:
                    st.error("Não foi possível gerar recomendações.")
    
    # TAB 3: ANÁLISE DE SAZONALIDADE
    with tab3:
        st.subheader("📈 Análise de Sazonalidade")
        
        st.markdown("""
        Identifique padrões de consumo ao longo do tempo:
        - **Sazonalidade Mensal**: Meses com maior/menor demanda
        - **Padrão Semanal**: Dias da semana com maior consumo
        """)
        
        selected_epi_season = st.selectbox(
            "Selecione o EPI:",
            sorted(df_prepared['epi_name'].unique()),
            key="epi_seasonality"
        )
        
        if st.button("🔍 Analisar Sazonalidade", key="btn_seasonality"):
            with st.spinner("Analisando padrões sazonais..."):
                fig = forecaster.analyze_seasonality(df_prepared, selected_epi_season)
                st.plotly_chart(fig, use_container_width=True)
                
                # Insights automáticos
                st.markdown("### 💡 Insights Automáticos")
                
                df_epi = df_prepared[df_prepared['epi_name'] == selected_epi_season].copy()
                
                # Análise mensal
                monthly_avg = df_epi.groupby('month')['quantity'].mean()
                peak_month = monthly_avg.idxmax()
                low_month = monthly_avg.idxmin()
                
                month_names = {
                    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
                }
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"""
                    **📈 Pico de Demanda**
                    
                    Mês: **{month_names[peak_month]}**
                    
                    Média: **{monthly_avg[peak_month]:.1f} unidades/dia**
                    """)
                
                with col2:
                    st.success(f"""
                    **📉 Menor Demanda**
                    
                    Mês: **{month_names[low_month]}**
                    
                    Média: **{monthly_avg[low_month]:.1f} unidades/dia**
                    """)
                
                # Análise semanal
                weekly_avg = df_epi.groupby('dayofweek')['quantity'].mean()
                peak_day = weekly_avg.idxmax()
                
                day_names = {
                    0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
                    3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
                }
                
                st.warning(f"""
                **📅 Dia com Maior Consumo**
                
                {day_names[peak_day]} - Média de **{weekly_avg[peak_day]:.1f} unidades**
                
                *Considere aumentar o estoque antes deste dia da semana.*
                """)
    
    # TAB 4: MÉTRICAS DOS MODELOS
    with tab4:
        st.subheader("🔍 Métricas e Performance dos Modelos")
        
        st.markdown("""
        Avalie a precisão e confiabilidade das previsões através de métricas estatísticas.
        """)
        
        selected_epi_metrics = st.selectbox(
            "Selecione o EPI para avaliação:",
            sorted(df_prepared['epi_name'].unique()),
            key="epi_metrics"
        )
        
        if st.button("📊 Avaliar Modelos", type="primary", key="btn_metrics"):
            with st.spinner("Treinando e avaliando modelos..."):
                
                # Treinar modelos
                xgb_result = forecaster.train_xgboost_model(df_prepared, selected_epi_metrics)
                prophet_result = forecaster.train_prophet_model(df_prepared, selected_epi_metrics)
                
                if xgb_result and prophet_result:
                    
                    # Métricas comparativas
                    st.markdown("### 📈 Comparação de Métricas")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### XGBoost")
                        st.metric("MAE (Erro Médio Absoluto)", f"{xgb_result['metrics']['mae']:.2f}")
                        st.metric("RMSE (Erro Quadrático Médio)", f"{xgb_result['metrics']['rmse']:.2f}")
                        st.metric("R² (Coeficiente de Determinação)", f"{xgb_result['metrics']['r2']:.3f}")
                    
                    with col2:
                        st.markdown("#### Prophet")
                        st.metric("MAE (Erro Médio Absoluto)", f"{prophet_result['metrics']['mae']:.2f}")
                        st.metric("RMSE (Erro Quadrático Médio)", f"{prophet_result['metrics']['rmse']:.2f}")
                        st.info("Prophet é otimizado para capturar tendências e sazonalidade")
                    
                    # Interpretação das métricas
                    st.markdown("### 📚 Interpretação das Métricas")
                    
                    st.info("""
                    **MAE (Mean Absolute Error)**
                    - Média dos erros absolutos entre valores reais e previstos
                    - Quanto menor, melhor
                    - Exemplo: MAE=2 significa erro médio de ±2 unidades
                    
                    **RMSE (Root Mean Squared Error)**
                    - Penaliza erros maiores mais fortemente que o MAE
                    - Útil para detectar outliers
                    
                    **R² (R-squared)**
                    - Varia de 0 a 1 (ou -∞ a 1)
                    - Próximo de 1: modelo explica bem a variação dos dados
                    - Próximo de 0: modelo não é melhor que a média
                    """)
                    
                    # Feature Importance (XGBoost)
                    st.markdown("### 🎯 Importância das Features (XGBoost)")
                    
                    import plotly.express as px
                    
                    fig = px.bar(
                        xgb_result['feature_importance'].head(10),
                        x='importance',
                        y='feature',
                        orientation='h',
                        title='Top 10 Features Mais Importantes',
                        labels={'importance': 'Importância', 'feature': 'Feature'}
                    )
                    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("""
                    **Interpretação:**
                    - Features no topo têm maior impacto na previsão
                    - Valores históricos (lags) geralmente são os mais importantes
                    - Médias móveis capturam tendências
                    """)
                    
                    # Gráfico de resíduos
                    st.markdown("### 📉 Análise de Resíduos (XGBoost)")
                    
                    residuals = xgb_result['y_test'].values - xgb_result['y_pred']
                    
                    fig = px.scatter(
                        x=xgb_result['y_pred'],
                        y=residuals,
                        labels={'x': 'Valores Previstos', 'y': 'Resíduos'},
                        title='Gráfico de Resíduos'
                    )
                    fig.add_hline(y=0, line_dash="dash", line_color="red")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.info("""
                    **Como interpretar:**
                    - Resíduos devem estar distribuídos aleatoriamente em torno de zero
                    - Padrões nos resíduos indicam que o modelo não capturou toda a informação
                    - Valores distantes de zero são outliers
                    """)
                    
                    # Comparação visual: Real vs Previsto
                    st.markdown("### 🎯 Comparação: Real vs Previsto")
                    
                    comparison_df = pd.DataFrame({
                        'Real': xgb_result['y_test'].values,
                        'Previsto': xgb_result['y_pred']
                    })
                    
                    fig = px.scatter(
                        comparison_df,
                        x='Real',
                        y='Previsto',
                        title='Real vs Previsto',
                        labels={'Real': 'Valor Real', 'Previsto': 'Valor Previsto'}
                    )
                    # Linha de previsão perfeita
                    max_val = max(comparison_df['Real'].max(), comparison_df['Previsto'].max())
                    fig.add_trace(
                        go.Scatter(
                            x=[0, max_val],
                            y=[0, max_val],
                            mode='lines',
                            name='Previsão Perfeita',
                            line=dict(dash='dash', color='red')
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.error("Dados insuficientes para treinar os modelos. São necessários pelo menos 30 dias de histórico.")
        
        # Informações adicionais sobre os modelos
        with st.expander("ℹ️ Sobre os Modelos Utilizados"):
            st.markdown("""
            ### XGBoost (Extreme Gradient Boosting)
            
            **O que é:**
            - Algoritmo de ensemble baseado em árvores de decisão
            - Constrói múltiplas árvores sequencialmente, cada uma corrigindo erros da anterior
            
            **Vantagens:**
            - Alta precisão em dados tabulares
            - Captura relações não-lineares complexas
            - Robusto contra overfitting
            - Rápido para treinar e prever
            
            **Quando usar:**
            - Dados com muitas features
            - Padrões complexos
            - Relações não-lineares
            
            ---
            
            ### Prophet (Facebook Prophet)
            
            **O que é:**
            - Modelo especializado em séries temporais
            - Desenvolvido pelo Facebook para análise de dados com sazonalidade
            
            **Vantagens:**
            - Excelente para capturar sazonalidade (diária, semanal, anual)
            - Robusto contra dados faltantes
            - Fornece intervalos de confiança
            - Fácil de interpretar
            
            **Quando usar:**
            - Dados com forte componente sazonal
            - Séries temporais com feriados/eventos especiais
            - Necessidade de intervalos de confiança
            
            ---
            
            ### Ensemble (Combinação)
            
            **O que é:**
            - Média ponderada das previsões de XGBoost e Prophet
            
            **Por que funciona:**
            - XGBoost captura padrões complexos
            - Prophet captura sazonalidade
            - A combinação reduz o viés de cada modelo individual
            - Geralmente mais preciso que modelos isolados
            """)
    
    # TAB 5: ANÁLISE DE PERFORMANCE
    with tab5:
        st.subheader("⚡ Análise de Performance e Backtesting")
        
        st.markdown("""
        Valide a precisão dos modelos através de testes rigorosos:
        - **Backtesting**: Simula previsões no passado para validar acurácia
        - **Comparação de Métodos**: Compara ML com métodos tradicionais
        """)
        
        from ML.performance_analyzer import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer()
        
        # Subtabs
        subtab1, subtab2, subtab3 = st.tabs([
            "🔄 Backtest Individual",
            "🏆 Comparação de Métodos",
            "📊 Relatório Completo"
        ])
        
        with subtab1:
            st.markdown("### Backtest de Modelo Individual")
            
            selected_epi_backtest = st.selectbox(
                "Selecione o EPI:",
                sorted(df_prepared['epi_name'].unique()),
                key="epi_backtest"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                train_days = st.number_input(
                    "Dias de treino:",
                    min_value=30,
                    max_value=365,
                    value=180
                )
            with col2:
                test_days = st.number_input(
                    "Dias de teste:",
                    min_value=7,
                    max_value=90,
                    value=30
                )
            
            if st.button("🚀 Executar Backtest", type="primary", key="btn_backtest"):
                with st.spinner("Executando backtest... Isso pode levar alguns minutos."):
                    backtest_result = analyzer.backtest_model(
                        df_prepared,
                        selected_epi_backtest,
                        train_days,
                        test_days
                    )
                    
                    if backtest_result:
                        st.success("Backtest concluído!")
                        
                        # Métricas principais
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("MAE Médio", f"{backtest_result['avg_mae']:.2f}")
                        col2.metric("RMSE Médio", f"{backtest_result['avg_rmse']:.2f}")
                        col3.metric("MAPE Médio", f"{backtest_result['avg_mape']:.1f}%")
                        col4.metric("Testes Realizados", backtest_result['num_backtests'])
                        
                        # Gráfico
                        fig = analyzer.plot_backtest_results(backtest_result)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Interpretação
                        st.markdown("### 📖 Interpretação dos Resultados")
                        
                        mape = backtest_result['avg_mape']
                        if mape < 10:
                            st.success(f"✅ Excelente! MAPE de {mape:.1f}% indica alta precisão.")
                        elif mape < 20:
                            st.info(f"ℹ️ Bom! MAPE de {mape:.1f}% indica precisão aceitável.")
                        elif mape < 30:
                            st.warning(f"⚠️ Moderado. MAPE de {mape:.1f}% indica que há espaço para melhoria.")
                        else:
                            st.error(f"❌ MAPE de {mape:.1f}% indica baixa precisão. Considere revisar os dados.")
                        
                        # Tabela de resultados
                        with st.expander("📋 Ver Resultados Detalhados"):
                            st.dataframe(
                                backtest_result['results'],
                                hide_index=True,
                                use_container_width=True
                            )
                    else:
                        st.error("Não foi possível executar o backtest. Verifique se há dados suficientes.")
        
        with subtab2:
            st.markdown("### Comparação entre Métodos de Previsão")
            
            st.info("""
            Compare o desempenho do ML Ensemble com métodos tradicionais:
            - **Naive**: Usa o último valor conhecido
            - **Moving Average**: Média dos últimos 7 dias
            - **Exponential Smoothing**: Suavização exponencial
            - **ML Ensemble**: XGBoost + Prophet
            """)
            
            selected_epi_comp = st.selectbox(
                "Selecione o EPI:",
                sorted(df_prepared['epi_name'].unique()),
                key="epi_comparison"
            )
            
            if st.button("🏆 Comparar Métodos", type="primary", key="btn_compare"):
                with st.spinner("Comparando diferentes métodos de previsão..."):
                    comparison_result = analyzer.compare_forecast_methods(
                        df_prepared,
                        selected_epi_comp
                    )
                    
                    if comparison_result:
                        st.success("Comparação concluída!")
                        
                        # Tabela de comparação
                        st.markdown("### 📊 Ranking de Métodos")
                        
                        comp_table = comparison_result['comparison_table'].copy()
                        comp_table['MAE'] = comp_table['MAE'].apply(lambda x: f"{x:.2f}")
                        comp_table['RMSE'] = comp_table['RMSE'].apply(lambda x: f"{x:.2f}")
                        comp_table['Rank'] = comp_table['Rank'].apply(lambda x: f"#{int(x)}")
                        
                        st.dataframe(
                            comp_table,
                            use_container_width=True,
                            column_config={
                                'Rank': st.column_config.TextColumn('Posição')
                            }
                        )
                        
                        # Identificar o melhor método
                        best_method = comp_table.index[0]
                        st.success(f"🏆 **Melhor Método**: {best_method}")
                        
                        # Gráfico comparativo
                        fig = analyzer.plot_method_comparison(comparison_result)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Insights
                        st.markdown("### 💡 Insights")
                        
                        if best_method == "ML Ensemble":
                            st.info("""
                            ✅ O ML Ensemble demonstrou o melhor desempenho, justificando o uso de 
                            algoritmos mais complexos para este EPI. Os modelos de Machine Learning 
                            estão capturando padrões que métodos tradicionais não conseguem identificar.
                            """)
                        else:
                            st.warning(f"""
                            ⚠️ O método {best_method} obteve melhor desempenho neste caso. 
                            Isso pode indicar que os dados para este EPI têm padrões simples que 
                            não justificam o uso de ML, ou que há necessidade de mais dados de treino.
                            """)
                    else:
                        st.error("Não foi possível executar a comparação.")
        
        with subtab3:
            st.markdown("### Relatório Completo de Performance")
            
            st.markdown("""
            Gera um relatório abrangente analisando todos os EPIs do sistema.
            
            **Atenção**: Este processo pode levar vários minutos dependendo da quantidade de EPIs.
            """)
            
            if st.button("📊 Gerar Relatório Completo", type="primary", key="btn_full_report"):
                epi_list = df_prepared['epi_name'].unique().tolist()
                
                with st.spinner(f"Analisando {len(epi_list)} EPIs... Por favor aguarde."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    report = analyzer.generate_performance_report(df_prepared, epi_list)
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    progress_bar.empty()
                    
                    if report and report.get('summary_statistics'):
                        st.success("Relatório gerado com sucesso!")
                        
                        # Resumo executivo
                        st.markdown("### 📋 Resumo Executivo")
                        
                        stats = report['summary_statistics']
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("MAE Geral", f"{stats['overall_mae']:.2f}")
                        col2.metric("RMSE Geral", f"{stats['overall_rmse']:.2f}")
                        col3.metric("MAPE Geral", f"{stats['overall_mape']:.1f}%")
                        
                        col1, col2 = st.columns(2)
                        col1.success(f"🏆 Melhor EPI: **{stats['best_epi']}**")
                        col2.error(f"⚠️ EPI com maior erro: **{stats['worst_epi']}**")
                        
                        # Gráfico resumo
                        fig = analyzer.plot_performance_summary(report)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabela detalhada
                        with st.expander("📊 Ver Resultados Individuais"):
                            individual_df = pd.DataFrame(report['individual_results']).T
                            individual_df = individual_df.sort_values('avg_mae')
                            individual_df.columns = ['MAE Médio', 'RMSE Médio', 'MAPE Médio', 'Nº Testes']
                            st.dataframe(individual_df, use_container_width=True)
                        
                        # Exportar relatório
                        import json
                        report_json = json.dumps(report, indent=2, default=str)
                        
                        st.download_button(
                            label="💾 Baixar Relatório JSON",
                            data=report_json,
                            file_name=f"performance_report_{datetime.now().strftime('%Y%m%d')}.json",
                            mime="application/json"
                        )
                    else:
                        st.error("Não foi possível gerar o relatório.")
        
        # Informações adicionais sobre os modelos
        with st.expander("ℹ️ Sobre os Modelos Utilizados"):
            st.markdown("""
            ### XGBoost (Extreme Gradient Boosting)
            
            **O que é:**
            - Algoritmo de ensemble baseado em árvores de decisão
            - Constrói múltiplas árvores sequencialmente, cada uma corrigindo erros da anterior
            
            **Vantagens:**
            - Alta precisão em dados tabulares
            - Captura relações não-lineares complexas
            - Robusto contra overfitting
            - Rápido para treinar e prever
            
            **Quando usar:**
            - Dados com muitas features
            - Padrões complexos
            - Relações não-lineares
            
            ---
            
            ### Prophet (Facebook Prophet)
            
            **O que é:**
            - Modelo especializado em séries temporais
            - Desenvolvido pelo Facebook para análise de dados com sazonalidade
            
            **Vantagens:**
            - Excelente para capturar sazonalidade (diária, semanal, anual)
            - Robusto contra dados faltantes
            - Fornece intervalos de confiança
            - Fácil de interpretar
            
            **Quando usar:**
            - Dados com forte componente sazonal
            - Séries temporais com feriados/eventos especiais
            - Necessidade de intervalos de confiança
            
            ---
            
            ### Ensemble (Combinação)
            
            **O que é:**
            - Média ponderada das previsões de XGBoost e Prophet
            
            **Por que funciona:**
            - XGBoost captura padrões complexos
            - Prophet captura sazonalidade
            - A combinação reduz o viés de cada modelo individual
            - Geralmente mais preciso que modelos isolados
            """)
    
    # Rodapé com informações
    st.markdown("---")
    st.caption("""
    💡 **Dica**: Para melhores resultados, mantenha um histórico consistente de pelo menos 3 meses de dados.
    As previsões são atualizadas automaticamente conforme novos dados são registrados no sistema.
    """)


if __name__ == "__main__":
    ml_forecast_page()
