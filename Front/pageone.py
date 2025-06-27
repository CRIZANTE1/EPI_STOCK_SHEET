import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from datetime import datetime
from fuzzywuzzy import process
import altair as alt
import plotly.express as px 
import calendar
from auth import is_admin

# Função para limpar e converter valores monetários
def clean_value(value_str):
    if value_str is None or pd.isna(value_str):
        return 0.0
    s = str(value_str).strip()
    if s == '':
        return 0.0
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def configurar_pagina():
    st.set_page_config(
        page_title="Página Inicial",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
           
def front_page():
    st.title("Controle de Estoque de EPIs") 
       
    if 'data' not in st.session_state:
        sheet_operations = SheetOperations()
        data = sheet_operations.carregar_dados()
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['value'] = df['value'].apply(clean_value)
            if 'image_url' not in df.columns:
                df['image_url'] = ''
            st.session_state['data'] = df
        else:
            st.error("Não foi possível carregar a planilha")
            return

    df = st.session_state['data']
    entrance_exit_edit_delete()

    st.write("### Registros de Entradas e Saídas")

    if 'image_url' in df.columns:
        df['image_url'] = df['image_url'].fillna('')
        image_map = df[df['image_url'].str.strip() != ''].drop_duplicates(subset=['epi_name'], keep='last').set_index('epi_name')['image_url'].to_dict()
        df['imagem_display'] = df['epi_name'].map(image_map)
    else:
        df['imagem_display'] = None

    display_columns = [
        'id', 'imagem_display', 'epi_name', 'quantity', 'transaction_type', 
        'date', 'value', 'requester', 'CA'
    ]
    display_columns = [col for col in display_columns if col in df.columns]
    
    df_display = df.sort_values(by='date', ascending=False)
    
    st.dataframe(data=df_display[display_columns],
                 column_config={
                     'imagem_display': st.column_config.ImageColumn(
                         "Imagem", help="Foto do EPI"
                     ),
                     'value': st.column_config.NumberColumn(
                         "Valor", help="O preço do material em Reais", min_value=0, max_value=100000, step=1, format='R$ %.2f'
                     ),
                     'epi_name': st.column_config.TextColumn(
                         'Equipamento', help='Nome do EPI', max_chars=50
                     ),
                     'quantity': st.column_config.NumberColumn(
                         'Quantidade', help='Quantidade de EPI', min_value=0, max_value=1000000, step=1, format='%.0f'
                     ),
                     'transaction_type': st.column_config.TextColumn(
                         'Transação', help='Entrada ou Saída', max_chars=50
                     ),
                     'CA': st.column_config.NumberColumn(
                         'CA', help='Certificado de Aprovação se aplicável', min_value=0, max_value=1000000, step=1, format='%.0f'
                     ),
                     'date': st.column_config.DateColumn(
                         'Data', help='Data da transação', format='DD/MM/YYYY', step=1
                     ),
                     'requester': st.column_config.TextColumn(
                         'Requisitante', help='Requisitante do Equipamento', max_chars=50
                     ),
                 }, hide_index=True)    
    
    st.write("### Análise do Estoque")
    calc_position(df)

def get_closest_match_name(name, choices):
    closest_match, score = process.extractOne(name, choices)
    closest_match, score = process.extractOne(name, choices, score_cutoff=90) 
    return closest_match if score >= 90 else name 

def calc_position(df):
    df = df.copy()
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    unique_epi_names = df['epi_name'].dropna().unique()
    if len(unique_epi_names) == 0:
        st.warning("Não há nomes de EPI válidos nos dados.")
        return
        
    name_mapping = {name: get_closest_match_name(name, unique_epi_names) for name in unique_epi_names}
    df['epi_name_normalized'] = df['epi_name'].map(name_mapping)
    df.dropna(subset=['epi_name_normalized'], inplace=True)

    epi_entries = df[df['transaction_type'].str.lower() == 'entrada'].groupby('epi_name_normalized')['quantity'].sum().fillna(0)
    epi_exits = df[df['transaction_type'].str.lower() == 'saída'].groupby('epi_name_normalized')['quantity'].sum().fillna(0)
    all_epis = epi_entries.index.union(epi_exits.index)
    total_epi = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)

    if total_epi.empty or total_epi.isnull().all():
        st.warning("Não há dados de estoque válidos para exibir no gráfico após o cálculo.")
        return
        
    total_epi_sorted = total_epi.sort_values()
    normal_stock = total_epi_sorted[total_epi_sorted > 0]
    if not normal_stock.empty:
        st.write("### Posição Atual do Estoque 📊")
        normal_df = pd.DataFrame({'Estoque': normal_stock})
        st.bar_chart(normal_df, use_container_width=True)
        
def carregar_empregados(sheet_operations):
    empregados_data = sheet_operations.carregar_dados_aba('empregados')
    if empregados_data:
        # ----- CORREÇÃO APLICADA AQUI -----
        df_empregados = pd.DataFrame(empregados_data[1:], columns=empregados_data[0])
        return df_empregados['name_empregado'].tolist()
    else:
        st.error("Não foi possível carregar os dados dos empregados")
        return []
    
def entrance_exit_edit_delete():
    if not is_admin():
        st.error("Acesso negado. Apenas administradores podem realizar esta ação.")
        return

    sheet_operations = SheetOperations()
    data = sheet_operations.carregar_dados()
    if data:
        df = pd.DataFrame(data[1:], columns=data[0])
        if 'value' in df.columns:
            df['value'] = df['value'].apply(clean_value)
    else:
        st.error("Não foi possível carregar a planilha")
        return

    required_columns = ['id', 'epi_name', 'quantity', 'transaction_type', 'date', 'value', 'requester', 'CA', 'image_url']
    if not all(column in df.columns for column in required_columns):
        st.error("A planilha não contém todas as colunas necessárias (verifique se 'image_url' existe).")
        return

    empregados = carregar_empregados(sheet_operations)

    with st.expander("Inserir novo registro"):
        transaction_type = st.selectbox("Tipo de transação:", ["entrada", "saída"], key="transaction_type_add")
        
        epi_name = ""
        ca = ""
        image_url = ""
        requester = None

        if transaction_type == "entrada":
            df_ep_unicos = df[df['transaction_type'] == 'entrada'].drop_duplicates(subset=['epi_name'], keep='last')
            lista_ep_existentes = df_ep_unicos['epi_name'].tolist()
            opcoes_epi = ["Adicionar Novo EPI"] + sorted(lista_ep_existentes)
            selecao_epi = st.selectbox("Selecionar EPI existente ou Adicionar Novo:", options=opcoes_epi, key="epi_choice_add")

            if selecao_epi == "Adicionar Novo EPI":
                st.write("---"); st.subheader("Cadastro de Novo EPI")
                epi_name = st.text_input("Nome do Novo EPI:", "", key="epi_name_add_new")
                ca = st.text_input("CA do Novo EPI:", "", key="ca_add_new")
                image_url = st.text_input("URL da Imagem:", "", placeholder="https://...", key="image_url_add_new")
                st.write("---")
            else:
                dados_epi_selecionado = df_ep_unicos[df_ep_unicos['epi_name'] == selecao_epi].iloc[0]
                epi_name = selecao_epi
                ca = dados_epi_selecionado.get('CA', '')
                image_url = dados_epi_selecionado.get('image_url', '')
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    if image_url: st.image(image_url, caption=f"Imagem de: {epi_name}", use_container_width=True)
                    else: st.info("ℹ️ Item sem imagem.")
                with col_info:
                    st.text_input("Nome do EPI", value=epi_name, disabled=True)
                    st.text_input("CA", value=ca, disabled=True)

        elif transaction_type == "saída":
            df['CA'] = df['CA'].fillna('')
            itens_disponiveis = df[df['transaction_type'] == 'entrada'].drop_duplicates(subset=['epi_name', 'CA'], keep='last')

            if not itens_disponiveis.empty:
                opcoes_saida = []
                lookup_saida = {}
                for _, item in itens_disponiveis.iterrows():
                    nome_item = item.get('epi_name', 'N/A')
                    ca_item = item.get('CA', '')
                    url_item = item.get('image_url', '')

                    if ca_item:
                        display_text = f"CA: {ca_item} - {nome_item}"
                    else:
                        display_text = f"SEM CA - {nome_item}"
                    
                    opcoes_saida.append(display_text)
                    lookup_saida[display_text] = {'nome': nome_item, 'ca': ca_item, 'url': url_item}

                selecao_saida = st.selectbox("Selecione o Item (por CA):", sorted(opcoes_saida), key="saida_choice_add")

                if selecao_saida:
                    dados_selecionados = lookup_saida[selecao_saida]
                    epi_name = dados_selecionados['nome']
                    ca = dados_selecionados['ca']
                    image_url = dados_selecionados['url']

                    if image_url:
                        st.image(image_url, caption=f"Visualização de: {epi_name}", width=200)
                    st.text_input("CA do item selecionado:", value=ca if ca else "N/A", disabled=True, key="ca_display_add")
            
            else:
                st.write("Não há itens de entrada registrados no banco de dados.")
            
            requester = st.selectbox("Solicitante:", empregados, key="requester_add")
            exit_date = st.date_input("Data da saída:", key="date_add")

        quantity = st.number_input("Quantidade:", min_value=1, step=1, key="quantity_add")
        value = st.number_input("Valor (Total ou Unitário):", min_value=0.0, step=0.01, key="value_add") if transaction_type == "entrada" else 0
        
        if st.button("Adicionar Registro", key="btn_add"):
            data_transacao = str(exit_date) if transaction_type == "saída" else str(datetime.now().date())
            if epi_name and quantity:
                url_para_salvar = image_url if transaction_type == "entrada" else ''
                new_data = [epi_name, quantity, transaction_type, data_transacao, value, requester, ca, url_para_salvar]
                sheet_operations.adc_dados(new_data)
                st.rerun()
            else:
                st.warning("Por favor, preencha todos os campos necessários.")

    with st.expander("Editar registro existente"):
        all_ids = df['id'].tolist()
        selected_id = st.selectbox("Selecione a linha para editar:", all_ids, key="id_edit")

        if selected_id:
            selected_row = df[df['id'] == selected_id].iloc[0]
            value_float = selected_row.get('value', 0.0)
            epi_name_edit = st.text_input("Nome do EPI:", value=selected_row["epi_name"], key="epi_name_edit")
            quantity_edit = st.number_input("Quantidade:", value=int(selected_row.get("quantity", 0)), key="quantity_edit")
            value_edit = st.number_input("Valor:", value=value_float, key="value_edit")
            transaction_type_edit = st.selectbox("Tipo de transação:", ["entrada", "saída"], index=0 if selected_row["transaction_type"] == "entrada" else 1, key="transaction_type_edit")
            image_url_edit = st.text_input("URL da Imagem:", value=selected_row.get("image_url", ""), key="image_url_edit")
            ca_edit = st.text_input("CA:", value=selected_row.get("CA", ""), key="ca_edit")
            requester_edit = st.text_input("Requisitante:", value=selected_row.get("requester", ""), key="requester_edit")

            if st.button("Salvar Edições", key="btn_edit"):
                updated_data = [epi_name_edit, quantity_edit, transaction_type_edit, str(selected_row["date"].date()), value_edit, requester_edit, ca_edit, image_url_edit]
                if sheet_operations.editar_dados(selected_id, updated_data):
                    st.success("Registro editado com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao editar o registro.")

    with st.expander("Excluir registro existente"):
        all_epi_ids = df['id'].tolist()
        if all_epi_ids:
            selected_id = st.selectbox("Selecione o ID para excluir:", all_epi_ids, key="id_delete")
            if st.button("Excluir", key="btn_delete"):
                if sheet_operations.excluir_dados(selected_id):
                    st.success(f"A entrada/saída com ID {selected_id} foi excluída com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao excluir o registro.")




