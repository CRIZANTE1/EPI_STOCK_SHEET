import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sys
import os


# Adicionar o diretório pai ao path para import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from AI_container.credentials.API_Operation import PDFQA
# Adicionar a importação da nova função de geração de PDF
from Utils.pdf_generator import create_forecast_pdf_from_report

def ai_recommendations_page():
    """
    Página para exibir recomendações de compra, análise de estoque e previsão orçamentária.
    """
    st.title("Análise por Inteligência Artificial 🤖")
    
    ai_engine = PDFQA()
    sheet_operations = SheetOperations()
    
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
        # Preparação dos Dados
        epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
        epi_exits = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum()
        all_epis = epi_entries.index.union(epi_exits.index)
        current_stock = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)
        stock_data = current_stock.to_dict()

        purchase_history = df[df['transaction_type'] == 'entrada'].sort_values(by='date', ascending=False).head(200).to_dict('records')
        usage_history = df[df['transaction_type'] == 'saída'].sort_values(by='date', ascending=False).head(500).to_dict('records')
        
        # Resumo do Estoque
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

        # Abas para as Análises
        tab1, tab2 = st.tabs(["Recomendações de Compra", "Previsão Orçamentária"])

        with tab1:
            st.subheader("Análise de Estoque e Sugestões de Compra")
            if st.button("Gerar Recomendações de Compra"):
                with st.spinner("Analisando dados de estoque e gerando recomendações..."):
                    # ----- ESTE BLOCO FOI CORRIGIDO -----
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
            st.subheader("Previsão de Compras Anual com IA")
            st.write("Esta ferramenta analisa o consumo histórico e o estoque atual para gerar uma lista de compras realista para os próximos 12 meses.")
    
            if st.button("Gerar Previsão de Compras"):
                with st.spinner("IA analisando dados para gerar a previsão..."):
                    forecast_result = ai_engine.generate_annual_forecast(
                        usage_history,
                        purchase_history,
                        stock_data,
                        forecast_months=12
                    )
                    
                    # Salva o resultado completo no session_state
                    st.session_state.latest_forecast_result = forecast_result
                    
                    if 'forecast_history' not in st.session_state:
                        st.session_state.forecast_history = []
                    st.session_state.forecast_history.append({
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "result": forecast_result # Salva o resultado completo no histórico
                    })
            
            # Exibe o último relatório gerado e o CUSTO TOTAL
            if 'latest_forecast_result' in st.session_state:
                result = st.session_state.latest_forecast_result
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    report_text = result.get("report", "")
                    df_data = result.get("data", pd.DataFrame())
    
                    # ---- NOVO: Bloco para calcular e exibir o Custo Total ----
                    if not df_data.empty:
                        # Calcula o custo total baseado na necessidade de compra
                        total_cost = (df_data['Necessidade de Compra (cálculo)'] * df_data['Custo Unit. (R$)']).sum()
                        
                        st.metric(
                            label="Orçamento Total Estimado para Compras",
                            value=f"R$ {total_cost:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
                        )
                    
                    # Exibe o relatório gerado pela IA
                    st.markdown(report_text)
                    
                    # ---- Botão de Download ----
                    st.markdown("---")
                    # A função de PDF precisaria ser adaptada para incluir o total,
                    # mas por enquanto vamos gerar o PDF apenas com o relatório da IA.
                    pdf_buffer = create_forecast_pdf_from_report(report_text)
                    st.download_button(
                        label="📥 Baixar Relatório em PDF",
                        data=pdf_buffer,
                        file_name=f"Previsao_Compras_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                        mime="application/pdf"
                    )
    
            # Exibe o histórico de previsões
            if 'forecast_history' in st.session_state and st.session_state.forecast_history:
                with st.expander("Ver Histórico de Previsões de Compra"):
                    for rec in reversed(st.session_state.forecast_history):
                        st.markdown(f"**Previsão de {rec['timestamp']}**")
                        if "error" in rec["result"]:
                            st.error(rec["result"]["error"])
                        else:
                            st.markdown(rec["result"]["report"])
                        st.markdown("---")

    except Exception as e:
        st.error(f"Erro ao processar dados para a análise de IA: {str(e)}")
        st.exception(e)



