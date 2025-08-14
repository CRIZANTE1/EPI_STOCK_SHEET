import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
import os
from Utils.pdf_generator import create_forecast_pdf_from_report

# Adicionar o diretório pai ao path para import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from AI_container.credentials.API_Operation import PDFQA


def ai_recommendations_page():
    """
    Página para exibir recomendações de compra, análise de estoque e previsão orçamentária.
    """
    st.title("Análise por Inteligência Artificial 🤖")
    
    ai_engine = PDFQA()
    sheet_operations = SheetOperations()
    
    # Carregar e preparar os dados uma única vez para toda a página
    @st.cache_data(ttl=600)
    def load_and_prepare_data():
        data = sheet_operations.carregar_dados()
        if not data or len(data) < 2:
            return None
        df = pd.DataFrame(data[1:], columns=data[0])
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['value'] = df['value'].apply(lambda x: 0 if x == '' else float(str(x).replace('.', '').replace(',', '.')))
        df['transaction_type'] = df['transaction_type'].str.lower().str.strip()
        return df

    df = load_and_prepare_data()

    if df is None:
        st.error("Não foi possível carregar a planilha ou ela está vazia.")
        return

    try:
        # --- Preparação dos Dados para as Análises ---
        
        # Calcular estoque atual
        epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
        epi_exits = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum()
        all_epis = epi_entries.index.union(epi_exits.index)
        current_stock = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)
        stock_data = current_stock.to_dict()

        # Preparar históricos com mais dados para análises mais precisas
        # A previsão orçamentária se beneficia de um histórico maior (até 1 ano)
        purchase_history = df[df['transaction_type'] == 'entrada'].sort_values(by='date', ascending=False).head(200).to_dict('records')
        usage_history = df[df['transaction_type'] == 'saída'].sort_values(by='date', ascending=False).head(500).to_dict('records')
        
        # --- Exibição do Resumo do Estoque (Sempre Visível) ---
        st.subheader("Resumo do Estoque Atual")
        critical_items = {k: v for k, v in stock_data.items() if v <= 0}
        normal_items = {k: v for k, v in stock_data.items() if v > 0}
        
        if critical_items:
            st.error("⚠️ Itens com Estoque Crítico ou Negativo")
            critical_df = pd.DataFrame(list(critical_items.items()), columns=['EPI', 'Quantidade'])
            st.dataframe(critical_df, use_container_width=True, hide_index=True)

        if normal_items:
            st.success("Itens com Estoque Positivo")
            normal_df = pd.DataFrame(list(normal_items.items()), columns=['EPI', 'Quantidade'])
            st.dataframe(normal_df.sort_values(by='Quantidade'), use_container_width=True, hide_index=True)
        
        st.markdown("---")

        # --- Abas para as Diferentes Análises de IA ---
        tab1, tab2 = st.tabs(["Recomendações de Compra", "Previsão Orçamentária"])

        with tab1:
            st.subheader("Análise de Estoque e Sugestões de Compra")
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
                        st.session_state.latest_recommendation = recommendations["recommendations"]
                        if 'recommendation_history' not in st.session_state:
                            st.session_state.recommendation_history = []
                        st.session_state.recommendation_history.append({
                            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "recommendations": recommendations["recommendations"]
                        })

            if 'latest_recommendation' in st.session_state:
                st.markdown("### Últimas Recomendações Geradas")
                st.info(st.session_state.latest_recommendation)

            if 'recommendation_history' in st.session_state and st.session_state.recommendation_history:
                with st.expander("Ver Histórico de Recomendações"):
                    for rec in reversed(st.session_state.recommendation_history):
                        st.markdown(f"**Recomendação de {rec['timestamp']}**")
                        st.markdown(rec["recommendations"])
                        st.markdown("---")

        with tab2:
            st.subheader("Previsão Orçamentária Trimestral com IA")
            st.write("Esta ferramenta analisa o consumo histórico para projetar os custos com EPIs para os próximos 3 meses.")
    
            if st.button("Gerar Previsão Orçamentária"):
                with st.spinner("IA analisando histórico para gerar a previsão..."):
                    forecast_result = ai_engine.generate_budget_forecast(
                        usage_history,
                        purchase_history,
                        forecast_months=3
                    )
                    
                    if "error" in forecast_result:
                        st.error(forecast_result["error"])
                    else:
                        # Salva o resultado no session_state para ser usado pelo botão de download
                        st.session_state.latest_forecast = forecast_result["report"]
                        
                        if 'forecast_history' not in st.session_state:
                            st.session_state.forecast_history = []
                        st.session_state.forecast_history.append({
                            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "report": forecast_result["report"]
                        })
    
            # Exibe o último relatório gerado e o botão de download
            if 'latest_forecast' in st.session_state:
                st.markdown("### Última Previsão Gerada")
                st.markdown(st.session_state.latest_forecast)
                
                # ---- BLOCO ADICIONADO PARA O BOTÃO DE DOWNLOAD ----
                st.markdown("---")
                
                # Prepara os dados para o download
                report_text = st.session_state.latest_forecast
                pdf_buffer = create_forecast_pdf_from_report(report_text)
                
                st.download_button(
                    label="📥 Baixar Relatório em PDF",
                    data=pdf_buffer,
                    file_name=f"Previsao_Orcamentaria_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf"
                )
    
            # Exibe o histórico de previsões
            if 'forecast_history' in st.session_state and st.session_state.forecast_history:
                with st.expander("Ver Histórico de Previsões Orçamentárias"):
                    for rec in reversed(st.session_state.forecast_history):
                        st.markdown(f"**Previsão de {rec['timestamp']}**")
                        st.markdown(rec["report"])
                        st.markdown("---")

