import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
from io import StringIO

# Ajuste o caminho se necessário, mas este deve funcionar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from End.Operations import SheetOperations
from API_Operation import PDFQA
from Utils.pdf_generator import create_forecast_pdf_from_report

def ai_recommendations_page():
    st.title("Análise por Inteligência Artificial 🤖")
    
    # Inicializa as classes de operação
    ai_engine = PDFQA()
    sheet_operations = SheetOperations()
    
    # --- CARREGAMENTO DE DADOS NO INÍCIO ---
    # Carrega todos os dados necessários uma vez para toda a página
    @st.cache_data(ttl=600)
    def load_all_data():
        stock_data_raw = sheet_operations.carregar_dados()
        employee_data_raw = sheet_operations.carregar_dados_aba('funcionarios')
        return stock_data_raw, employee_data_raw

    stock_data_raw, employee_data = load_all_data()

    if not stock_data_raw or len(stock_data_raw) < 2:
        st.error("Não foi possível carregar a planilha de estoque ou ela está vazia."); return
    
    # Se os dados dos funcionários não forem carregados, exibe um aviso mas continua
    if not employee_data:
        st.warning("Não foi possível carregar os dados dos funcionários. Algumas análises podem ser limitadas.")
        
    # --- PREPARAÇÃO DOS DADOS (disponível para ambas as abas) ---
    df = pd.DataFrame(stock_data_raw[1:], columns=stock_data_raw[0])
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    # Usa a função de limpeza de valor da classe, que é mais robusta
    df['value'] = df['value'].apply(PDFQA.clean_monetary_value)
    df['transaction_type'] = df['transaction_type'].str.lower().str.strip()

    epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
    epi_exits = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum()
    all_epis = epi_entries.index.union(epi_exits.index)
    current_stock = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)
    stock_data = current_stock.to_dict()

    purchase_history = df[df['transaction_type'] == 'entrada'].sort_values(by='date', ascending=False).to_dict('records')
    usage_history = df[df['transaction_type'] == 'saída'].sort_values(by='date', ascending=False).to_dict('records')
    
    # --- Abas para as Diferentes Análises de IA ---
    tab1, tab2 = st.tabs(["Recomendações de Compra (Análise Geral)", "Previsão Orçamentária Anual (Otimizada)"])

    with tab1:
        st.subheader("Análise Rápida de Estoque e Sugestões de Compra")
        if st.button("Gerar Recomendações Gerais"):
            with st.spinner("Analisando estoque e consumo..."):
                # Agora 'employee_data' está sempre disponível aqui
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

        if 'latest_recommendation' in st.session_state:
            st.markdown("### Últimas Recomendações Geradas")
            st.info(st.session_state.latest_recommendation)

    with tab2:
        st.subheader("Previsão de Compras Anual com Otimização de Orçamento")
        st.write("Esta ferramenta usa o histórico completo, a necessidade dos funcionários e uma meta orçamentária para criar uma lista de compras inteligente.")
        
        budget_target = st.number_input("Defina a meta orçamentária (R$):", min_value=1000, value=200000, step=1000)

        if st.button("Gerar Previsão Anual Otimizada"):
            with st.spinner("IA analisando todos os dados e otimizando para o orçamento..."):
                # E 'employee_data' também está disponível aqui
                forecast_result = ai_engine.generate_annual_forecast(
                    usage_history,
                    purchase_history,
                    stock_data,
                    employee_data,
                    budget_target=budget_target,
                    forecast_months=12
                )
                st.session_state.latest_forecast_result = forecast_result
        
        if 'latest_forecast_result' in st.session_state:
            result = st.session_state.latest_forecast_result
            if "error" in result:
                st.error(result["error"])
            else:
                report_text = result.get("report", "Nenhum relatório gerado.")
                st.markdown("---")
                st.markdown(report_text)
                
                st.markdown("---")
                pdf_buffer = create_forecast_pdf_from_report(report_text)
                st.download_button(
                    label="📥 Baixar Previsão em PDF",
                    data=pdf_buffer,
                    file_name=f"Previsao_Otimizada_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf"
                )

            if 'forecast_history' in st.session_state and st.session_state.forecast_history:
                with st.expander("Ver Histórico de Previsões de Compra"):
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








