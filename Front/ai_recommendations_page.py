import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
from io import StringIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from AI_container.credentials.API_Operation import PDFQA
from Utils.pdf_generator import create_forecast_pdf_from_report

def ai_recommendations_page():
    st.title("Análise por Inteligência Artificial 🤖")
    
    ai_engine = PDFQA()
    sheet_operations = SheetOperations()
    
    @st.cache_data(ttl=600)
    def load_all_data():
        stock_data_raw = sheet_operations.carregar_dados()
        employee_data_raw = sheet_operations.carregar_dados_aba('funcionarios')
        return stock_data_raw, employee_data_raw

    stock_data_raw, employee_data = load_all_data()

    if not stock_data_raw or len(stock_data_raw) < 2:
        st.error("Não foi possível carregar a planilha de estoque ou ela está vazia."); return
    
    if not employee_data:
        st.warning("Dados de funcionários não carregados. Análises podem ser limitadas.")
        
    df = pd.DataFrame(stock_data_raw[1:], columns=stock_data_raw[0])
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['value'] = df['value'].apply(PDFQA.clean_monetary_value)
    df['transaction_type'] = df['transaction_type'].str.lower().str.strip()

    epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
    epi_exits = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum()
    all_epis = epi_entries.index.union(epi_exits.index)
    current_stock = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)
    stock_data = current_stock.to_dict()

    purchase_history = df[df['transaction_type'] == 'entrada'].sort_values(by='date', ascending=False).to_dict('records')
    usage_history = df[df['transaction_type'] == 'saída'].sort_values(by='date', ascending=False).to_dict('records')
    
    tab1, tab2 = st.tabs(["Recomendações de Compra (Análise Geral)", "Previsão Orçamentária Anual (Otimizada)"])

    with tab1:
        st.subheader("Análise Rápida de Estoque e Sugestões de Compra")
        if st.button("Gerar Recomendações Gerais"):
            with st.spinner("Analisando estoque e consumo..."):
                recommendations = ai_engine.stock_analysis(
                    stock_data,
                    purchase_history,
                    usage_history,
                    employee_data
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
        st.subheader("Relatório de Custeio Anual (Análise Completa com IA e Embeddings)")
        st.write("Esta ferramenta utiliza todos os dados da empresa e a técnica de RAG para gerar um relatório de custeio detalhado, similar ao modelo de referência.")

        if st.button("Gerar Relatório de Custeio Completo"):
            with st.spinner("IA criando e consultando a base de conhecimento (embeddings)... Este processo pode levar um momento."):
                
                # Chama a nova função RAG que faz todo o trabalho
                report_result = ai_engine.generate_costing_report(
                    stock_data,
                    purchase_history,
                    usage_history,
                    employee_data
                )
                
                st.session_state.latest_costing_report = report_result
                
                if 'costing_report_history' not in st.session_state:
                    st.session_state.costing_report_history = []
                st.session_state.costing_report_history.append({
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "result": report_result 
                })
        
        if 'latest_costing_report' in st.session_state:
            result = st.session_state.latest_costing_report
            st.markdown("---")
            
            if "error" in result:
                st.error(result["error"])
            else:
                report_text = result.get("report", "Nenhum relatório gerado.")
                st.markdown(report_text)
                
                st.markdown("---")
                pdf_buffer = create_forecast_pdf_from_report(report_text)
                st.download_button(
                    label="📥 Baixar Relatório de Custeio em PDF",
                    data=pdf_buffer,
                    file_name=f"Relatorio_Custeio_Anual_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf"
                )
        
        if 'costing_report_history' in st.session_state and st.session_state.costing_report_history:
            with st.expander("Ver Histórico de Relatórios de Custeio"):
                for rec in reversed(st.session_state.costing_report_history):
                    st.markdown(f"**Relatório de {rec['timestamp']}**")
                    history_result = rec.get("result", {})
                    if "error" in history_result:
                        st.error(history_result["error"])
                    else:
                        st.markdown(history_result.get("report", "Relatório não disponível."))
                    st.markdown("---")
