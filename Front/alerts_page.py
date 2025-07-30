import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from Utils.alert_system import analyze_replacement_alerts, get_ia_insights_for_alert

def alerts_page():
    st.title("🚨 Alertas de Troca Periódica de EPI")
    st.write("Esta página analisa a data da última retirada de cada EPI por funcionário e a compara com as regras de troca pré-definidas.")
    
    sheet_operations = SheetOperations()
    
    @st.cache_data(ttl=300)
    def load_stock_data():
        data = sheet_operations.carregar_dados()
        if data and len(data) > 1:
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
        return # Termina a execução aqui se não houver alertas
    
    total_alerts = len(alerts)
    st.warning(f"Encontrado(s) {total_alerts} alerta(s) de troca vencida:")

    # Converte os alertas para um DataFrame para facilitar a manipulação
    df_alerts = pd.DataFrame(alerts)

    # Adiciona um filtro para o usuário focar em um funcionário específico, se desejar
    st.markdown("---")
    funcionarios_com_alerta = sorted(df_alerts['Funcionário'].unique())
    selected_employee = st.selectbox(
        "Filtrar por funcionário (opcional)",
        options=["Todos"] + funcionarios_com_alerta
    )

    # Filtra o DataFrame de alertas se um funcionário foi selecionado
    if selected_employee != "Todos":
        df_alerts_display = df_alerts[df_alerts['Funcionário'] == selected_employee]
    else:
        df_alerts_display = df_alerts

    if df_alerts_display.empty:
        st.info(f"Nenhum alerta para {selected_employee}.")
    else:
        # Loop sobre os alertas (filtrados ou não) e exibe os expanders
        for index, row in df_alerts_display.iterrows():
            # Usamos o índice original do DataFrame para garantir uma chave única para o botão
            original_index = row.name 
            
            # Título do expander mais informativo
            expander_title = f"**{row['Funcionário']}** — EPI: **{row['EPI']}** (Status: {row['Status']})"
            
            with st.expander(expander_title):
                col1, col2 = st.columns(2)
                col1.metric("Última Retirada", row['Última Retirada'])
                col2.metric("Troca Prevista", row['Próxima Troca Prevista'], delta=f"-{row['Status'].split(' ')[0]} dias", delta_color="inverse")
                
                # Botão para chamar a análise de IA
                if st.button("Analisar Padrão de Consumo com IA 🤖", key=f"ia_btn_{original_index}"):
                    with st.spinner("A Inteligência Artificial está analisando o histórico..."):
                        insights = get_ia_insights_for_alert(row['Funcionário'], row['EPI'], df_stock)
                        st.markdown("---")
                        st.markdown("#### Análise da IA:")
                        st.info(insights) # st.info é ótimo para destacar a resposta da IA

    st.markdown("---")
    st.info("ℹ️ **Como resolver um alerta?** Para remover um alerta da lista, registre uma nova saída do mesmo EPI para o funcionário correspondente na Página Principal.")
