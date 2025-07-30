import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from Utils.pdf_generator import create_epi_ficha_reportlab 

def generate_ficha_page():
    st.title("📄 Gerar Ficha de Controle de EPI")

    sheet_operations = SheetOperations()

    # Carregar dados
    @st.cache_data(ttl=300)
    def load_data():
        control_stock_data = sheet_operations.carregar_dados()
        funcionarios_data = sheet_operations.carregar_dados_aba('funcionarios')
        return control_stock_data, funcionarios_data

    control_stock_data, funcionarios_data = load_data()

    if not control_stock_data:
        st.error("Não foi possível carregar os dados de estoque.")
        return

    df_stock = pd.DataFrame(control_stock_data[1:], columns=control_stock_data[0])
    df_stock['date'] = pd.to_datetime(df_stock['date'], errors='coerce').dt.strftime('%d/%m/%Y')
    
    df_funcionarios = pd.DataFrame()
    if funcionarios_data and len(funcionarios_data) > 1:
        df_funcionarios = pd.DataFrame(funcionarios_data[1:], columns=funcionarios_data[0])

    # 1. Selecionar o funcionário
    st.header("1. Selecione o Funcionário")
    funcionarios_com_saida = sorted(df_stock[df_stock['transaction_type'] == 'saída']['requester'].unique())
    
    if not funcionarios_com_saida:
        st.warning("Nenhum funcionário com registro de saída de EPI encontrado.")
        return

    selected_employee = st.selectbox("Funcionário:", funcionarios_com_saida)

    if selected_employee:
        st.header("2. Confirme os Dados do Funcionário")
        
        # Tentar encontrar dados do funcionário na planilha 'funcionarios'
        employee_details = {}
        if not df_funcionarios.empty:
            # Assumindo que a planilha de funcionários tem uma coluna 'Nome Completo'
            # Adapte 'Nome Completo' para o nome real da coluna na sua planilha
            if 'Nome Completo' in df_funcionarios.columns:
                match = df_funcionarios[df_funcionarios['Nome Completo'] == selected_employee]
                if not match.empty:
                    employee_details = match.iloc[0].to_dict()

        # Permitir que o usuário preencha dados faltantes
        # Adapte os nomes das colunas ('Registro', 'Setor', 'Cargo') para os nomes reais
        col1, col2, col3 = st.columns(3)
        registro = col1.text_input("Registro:", value=employee_details.get("Registro", ""))
        setor = col2.text_input("Setor:", value=employee_details.get("Setor", ""))
        cargo = col3.text_input("Cargo:", value=employee_details.get("Cargo", ""))

        # 3. Listar EPIs a serem incluídos
        st.header("3. EPIs Registrados para este Funcionário")
        epi_records = df_stock[
            (df_stock['requester'] == selected_employee) & 
            (df_stock['transaction_type'] == 'saída')
        ].sort_values(by='date', ascending=True).to_dict('records')

        if not epi_records:
            st.warning("Nenhum EPI encontrado para este funcionário.")
        else:
            df_display = pd.DataFrame(epi_records)[['date', 'epi_name', 'CA']]
            st.dataframe(df_display, hide_index=True)

            # 4. Gerar o PDF
            st.header("4. Gerar Ficha")
            if st.button("Gerar Ficha em PDF"):
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
