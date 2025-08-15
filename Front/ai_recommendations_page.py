import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from AI_container.credentials.API_Operation import PDFQA
from Utils.pdf_generator import create_forecast_pdf_from_report

def ai_recommendations_page():
    st.title("Análise por Inteligência Artificial 🤖")
    
    try:
        ai_engine = PDFQA()
        sheet_operations = SheetOperations()
        
        @st.cache_data(ttl=600)
        def load_all_data():
            stock_data_raw = sheet_operations.carregar_dados()
            employee_data_raw = sheet_operations.carregar_dados_aba('funcionarios')
            return stock_data_raw, employee_data_raw

        stock_data_raw, employee_data = load_all_data() # employee_data é definido aqui

        if not stock_data_raw or len(stock_data_raw) < 2:
            st.error("Não foi possível carregar a planilha de estoque ou ela está vazia."); return
        
        if not employee_data:
            st.warning("Dados de funcionários não carregados. Análises podem ser limitadas.")
            
        # Processamento dos dados que será usado por ambas as abas
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
        
        # --- INTERFACE COM ABAS ---
        tab1, tab2 = st.tabs(["Recomendações de Compra (Análise Geral)", "Previsão Orçamentária Anual"])
    
        with tab1:
            st.subheader("Análise de Estoque e Sugestões de Compra (Base Trimestral)")
            if st.button("Gerar Recomendações Gerais"):
                with st.spinner("IA analisando todos os dados..."):
                    result = ai_engine.stock_analysis(
                        stock_data, purchase_history, usage_history, employee_data
                    )
                    # Salva o resultado para ser usado pela Tab 2 e para exibição
                    st.session_state.latest_recommendation = result
            
            if 'latest_recommendation' in st.session_state:
                res = st.session_state.latest_recommendation
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.markdown("### Relatório de Análise e Recomendações")
                    st.markdown(res["recommendations"])
    
        with tab2:
            st.subheader("Previsão Orçamentária de Compras para os Próximos 12 Meses")
            st.write("Esta ferramenta utiliza a recomendação da primeira aba e a projeta para um ano, calculando o orçamento total.")
    
            # Botão só fica ativo se a recomendação da tab1 já foi gerada
            if 'latest_recommendation' not in st.session_state or "error" in st.session_state.latest_recommendation:
                st.warning("👈 Por favor, gere primeiro as 'Recomendações Gerais' na primeira aba para habilitar a previsão anual.")
            else:
                if st.button("Gerar Previsão Anual a partir da Recomendação"):
                    with st.spinner("IA projetando a necessidade anual e calculando o orçamento..."):
                        short_term_text = st.session_state.latest_recommendation['recommendations']
                        
                        result = ai_engine.generate_annual_forecast(short_term_text, purchase_history)
                        st.session_state.latest_forecast = result
                
                if 'latest_forecast' in st.session_state:
                    res = st.session_state.latest_forecast
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        st.markdown(res["report"])
                        st.markdown("---")
                        pdf_buffer = create_forecast_pdf_from_report(res["report"])
                        st.download_button(
                            label="📥 Baixar Previsão em PDF",
                            data=pdf_buffer,
                            file_name=f"Previsao_Anual_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                            mime="application/pdf"
                        )
    
                if 'forecast_history' in st.session_state and st.session_state.forecast_history:
                    with st.expander("Ver Histórico de Previsões Anuais"):
                        for rec in reversed(st.session_state.forecast_history):
                            st.markdown(f"**Previsão de {rec['timestamp']}**")
                            history_result = rec.get("result", {})
                            if "error" in history_result:
                                st.error(history_result["error"])
                            else:
                                st.markdown(history_result.get("report", "Relatório não disponível."))
                            st.markdown("---")

    except Exception as e:
        st.error(f"Erro ao processar dados para a análise de IA: {str(e)}")
        st.exception(e)







