import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from datetime import datetime
from Utils.pdf_generator import create_epi_ficha_html

def generate_ficha_page():
    st.title("📄 Gerar Ficha de Controle de EPI")

    sheet_operations = SheetOperations()

    @st.cache_data(ttl=300)
    def load_data():
        control_stock_data = sheet_operations.carregar_dados()
        empregados_data = sheet_operations.carregar_dados_aba('empregados')
        return control_stock_data, empregados_data

    control_stock_data, empregados_data = load_data()

    if not control_stock_data:
        st.error("Não foi possível carregar os dados de estoque.")
        return

    df_stock = pd.DataFrame(control_stock_data[1:], columns=control_stock_data[0])
    df_stock['date'] = pd.to_datetime(df_stock['date'], errors='coerce').dt.strftime('%d/%m/%Y')
    
    df_empregados = pd.DataFrame()
    if empregados_data and len(empregados_data) > 1:
        df_empregados = pd.DataFrame(empregados_data[1:], columns=empregados_data[0])

    st.header("1. Selecione o Funcionário")
    
    lista_funcionarios = []
    if not df_empregados.empty and 'name_empregado' in df_empregados.columns:
        lista_funcionarios = sorted(df_empregados['name_empregado'].dropna().unique())
    
    if not lista_funcionarios:
        st.warning("Nenhum funcionário cadastrado na aba 'empregados'. Verifique a planilha.")
        return

    selected_employee = st.selectbox("Funcionário:", lista_funcionarios)

    if selected_employee:
        st.header("2. Confirme ou Preencha os Dados")
        
        employee_details = {}
        if not df_empregados.empty:
            match = df_empregados[df_empregados['name_empregado'] == selected_employee]
            if not match.empty:
                # Converte para dict e preenche valores nulos (NaN) com string vazia
                employee_details = match.iloc[0].fillna('').to_dict()

        col1, col2, col3 = st.columns(3)
        # Os campos são preenchidos com os dados da planilha. Se não houver dados, ficam vazios.
        registro = col1.text_input("Registro", value=employee_details.get("Registro", ""))
        setor = col2.text_input("Setor", value=employee_details.get("Setor", ""))
        cargo = col3.text_input("Cargo", value=employee_details.get("Cargo", ""))

        # ---- NOVA MELHORIA: AVISO SOBRE DADOS FALTANTES ----
        dados_faltantes = []
        if not registro: dados_faltantes.append("Registro")
        if not setor: dados_faltantes.append("Setor")
        if not cargo: dados_faltantes.append("Cargo")

        if dados_faltantes:
            st.info(f"Atenção: Os seguintes campos não foram encontrados na planilha para este funcionário: **{', '.join(dados_faltantes)}**. Por favor, preencha-os manualmente para que a ficha seja gerada corretamente.")
        else:
            st.success("Todos os dados do funcionário foram carregados da planilha.")

        st.header("3. EPIs Registrados")
        epi_records = df_stock[
            (df_stock['requester'] == selected_employee) & 
            (df_stock['transaction_type'] == 'saída')
        ].sort_values(by='date', ascending=True).to_dict('records')

        if not epi_records:
            st.warning("Nenhum EPI encontrado para este funcionário.")
        else:
            df_display = pd.DataFrame(epi_records)[['date', 'epi_name', 'CA']]
            st.dataframe(df_display.rename(columns={'date': 'Data', 'epi_name': 'EPI', 'CA': 'C.A.'}), hide_index=True)

            st.header("4. Gerar Ficha")
            
            # O botão só fica ativo se todos os campos estiverem preenchidos
            if st.button("Gerar Ficha em PDF", disabled=(len(dados_faltantes) > 0)):
                employee_info = {
                    "nome": selected_employee,
                    "registro": registro,
                    "setor": setor,
                    "cargo": cargo
                }
                
                with st.spinner("Gerando PDF..."):
                    pdf_buffer = create_epi_ficha_reportlab(employee_info, epi_records)
                    
                    st.download_button(
                        label="📥 Baixar Ficha PDF",
                        data=pdf_buffer,
                        file_name=f"Ficha_EPI_{selected_employee.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
            elif len(dados_faltantes) > 0:
                 st.warning("Preencha todos os campos acima para habilitar a geração da ficha.")
