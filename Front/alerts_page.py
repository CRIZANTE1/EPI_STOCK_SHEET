import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from Utils.alert_system import analyze_replacement_alerts 

def alerts_page():
    st.title("🚨 Alertas de Troca Periódica de EPI")
    st.write("Esta página analisa a data da última retirada de cada EPI por funcionário e a compara com as regras de troca pré-definidas.")
    
    sheet_operations = SheetOperations()
    
    @st.cache_data(ttl=300)
    def load_stock_data():
        data = sheet_operations.carregar_dados()
        if data:
            return pd.DataFrame(data[1:], columns=data[0])
        return pd.DataFrame()

    df_stock = load_stock_data()

    if df_stock.empty:
        st.error("Não foi possível carregar os dados de estoque para análise.")
        return

    with st.spinner("Analisando registros e gerando alertas..."):
        alerts = analyze_replacement_alerts(df_stock)

    if not alerts:
        st.success("✅ Nenhuma troca de EPI vencida encontrada. Tudo em dia!")
    else:
        st.warning(f"Encontrado(s) {len(alerts)} alerta(s) de troca vencida:")
        
        df_alerts = pd.DataFrame(alerts)
        
        # Reordenando colunas para melhor visualização
        df_alerts = df_alerts[["Funcionário", "EPI", "Última Retirada", "Próxima Troca Prevista", "Status"]]
        
        st.dataframe(
            df_alerts,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Mostra há quantos dias a troca está vencida."
                )
            }
        )

        st.info("Para remover um alerta da lista, registre uma nova saída do mesmo EPI para o funcionário correspondente na Página Principal.")
