import streamlit as st
import pandas as pd
from End.Operations import SheetOperations

def show_history_page():
    st.title("📜 Histórico de Emissão de Fichas de EPI")

    sheet_ops = SheetOperations()
    
    @st.cache_data(ttl=300)
    def load_history_data():
        history_data = sheet_ops.carregar_dados_aba('emission_history')
        return history_data

    history_data = load_history_data()

    if not history_data or len(history_data) <= 1:
        st.info("Nenhum histórico de emissão encontrado.")
        return

    columns = history_data[0][:3]
    data = [row[:3] for row in history_data[1:]]
    df_history = pd.DataFrame(data, columns=columns)
    df_history = df_history.sort_values(by='emission_date', ascending=False)

    st.dataframe(df_history, hide_index=True)
