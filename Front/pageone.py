import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from datetime import datetime
from fuzzywuzzy import process
import altair as alt
import plotly.express as px 
import calendar
from auth import (
    is_admin,
    can_edit, 
    can_view  
)

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

    df = st.session_state['data'].copy()
    if can_edit():
        entrance_exit_edit_delete()
    else:
        st.info("Você tem permissão de visualização. Para adicionar ou editar registros, contate um administrador.")

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
                     'epi_name': st.column_config.TextColumn('Equipamento'),
                     'quantity': st.column_config.NumberColumn('Quantidade'),
                     'transaction_type': st.column_config.TextColumn('Transação'),
                     'CA': st.column_config.NumberColumn('CA'),
                     'date': st.column_config.DateColumn('Data', format='DD/MM/YYYY'),
                     'requester': st.column_config.TextColumn('Requisitante'),
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
        return
    name_mapping = {name: get_closest_match_name(name, unique_epi_names) for name in unique_epi_names}
    df['epi_name_normalized'] = df['epi_name'].map(name_mapping)
    df.dropna(subset=['epi_name_normalized'], inplace=True)
    epi_entries = df[df['transaction_type'].str.lower() == 'entrada'].groupby('epi_name_normalized')['quantity'].sum().fillna(0)
    epi_exits = df[df['transaction_type'].str.lower() == 'saída'].groupby('epi_name_normalized')['quantity'].sum().fillna(0)
    total_epi = epi_entries.reindex(epi_entries.index.union(epi_exits.index), fill_value=0) - epi_exits.reindex(epi_entries.index.union(epi_exits.index), fill_value=0)
    if not total_epi.empty:
        st.bar_chart(total_epi[total_epi > 0].sort_values())

def carregar_empregados(sheet_operations):
    empregados_data = sheet_operations.carregar_dados_aba('empregados')
    if empregados_data and len(empregados_data) > 1:
        df_empregados = pd.DataFrame(empregados_data[1:], columns=empregados_data[0])
        return df_empregados['name_empregado'].tolist()
    else:
        st.warning("Não foi possível carregar a lista de empregados. Verifique a aba 'empregados'.")
        return []

def entrance_exit_edit_delete():
    
    sheet_operations = SheetOperations()
    data = sheet_operations.carregar_dados()
    if data:
        df = pd.DataFrame(data[1:], columns=data[0])
        if 'value' in df.columns: df['value'] = df['value'].apply(clean_value)
    else:
        st.error("Não foi possível carregar a planilha"); return

    required_columns = ['id', 'epi_name', 'quantity', 'transaction_type', 'date', 'value', 'requester', 'CA', 'image_url']
    if not all(column in df.columns for column in required_columns):
        st.error("Colunas necessárias não encontradas na planilha. Verifique a documentação."); return

    empregados = carregar_empregados(sheet_operations)

    with st.expander("Inserir novo registro"):
        transaction_type = st.selectbox("Tipo de transação:", ["entrada", "saída"], key="transaction_type_add")
        
        epi_name, ca, image_url, requester = "", "", "", None

        if transaction_type == "entrada":
            df_ep_unicos = df[df['transaction_type'] == 'entrada'].drop_duplicates(subset=['epi_name'], keep='last')
            opcoes_epi = ["Adicionar Novo EPI"] + sorted(df_ep_unicos['epi_name'].tolist())
            selecao_epi = st.selectbox("Selecionar EPI ou Adicionar Novo:", options=opcoes_epi, key="epi_choice_add")

            if selecao_epi == "Adicionar Novo EPI":
                st.write("---"); st.subheader("Cadastro de Novo EPI")
                epi_name = st.text_input("Nome do Novo EPI:", key="epi_name_add_new")
                ca = st.text_input("CA do Novo EPI:", key="ca_add_new")
                image_url = st.text_input("URL da Imagem:", placeholder="https://...", key="image_url_add_new")
            else:
                dados = df_ep_unicos[df_ep_unicos['epi_name'] == selecao_epi].iloc[0]
                epi_name, ca, image_url = dados.get('epi_name', ''), dados.get('CA', ''), dados.get('image_url', '')
                col1, col2 = st.columns([1, 2])
                with col1: st.image(image_url, use_container_width=True) if image_url else st.info("Sem imagem.")
                with col2: st.text_input("Nome", value=epi_name, disabled=True), st.text_input("CA", value=ca, disabled=True)

        elif transaction_type == "saída":
            df['CA'] = df['CA'].fillna('')
            itens = df[df['transaction_type'] == 'entrada'].drop_duplicates(subset=['epi_name', 'CA'], keep='last')
            if not itens.empty:
                lookup = {f"CA: {item.get('CA', 'N/A')} - {item.get('epi_name', '')}": item for _, item in itens.iterrows()}
                selecao = st.selectbox("Selecione o Item (por CA):", sorted(lookup.keys()), key="saida_choice_add")
                if selecao:
                    dados = lookup[selecao]
                    epi_name, ca, image_url = dados.get('epi_name', ''), dados.get('CA', ''), dados.get('image_url', '')
                    if image_url: st.image(image_url, width=200)
                    st.text_input("CA selecionado:", value=ca or "N/A", disabled=True)
            else:
                st.write("Nenhum item de entrada no banco de dados.")
            requester = st.selectbox("Solicitante:", empregados, key="requester_add")
            exit_date = st.date_input("Data da saída:", key="date_add")

        quantity = st.number_input("Quantidade:", min_value=1, step=1, key="quantity_add")
        value = st.number_input("Valor (unidade):", min_value=0.0, step=0.01, key="value_add") if transaction_type == "entrada" else 0.0
        
        if st.button("Adicionar Registro", key="btn_add"):
            data_transacao = str(exit_date) if transaction_type == "saída" else str(datetime.now().date())
            if epi_name and quantity:

                new_data = [
                    epi_name or '',          # Coluna epi_name
                    quantity,                # Coluna quantity
                    transaction_type or '',  # Coluna transaction_type
                    data_transacao,          # Coluna date
                    value,                   # Coluna value
                    requester or '',         # Coluna requester
                    ca or '',                # Coluna CA
                    image_url or ''          # Coluna image_url
                ]
                sheet_operations.adc_dados(new_data)
                st.rerun()
            else:
                st.warning("Preencha todos os campos obrigatórios.")

    with st.expander("Editar registro existente"):
        all_ids = df['id'].tolist()
        if not all_ids: return
        selected_id = st.selectbox("Selecione o ID para editar:", all_ids, key="id_edit")
        if selected_id:
            row = df[df['id'] == selected_id].iloc[0]
            with st.form(key="edit_form"):
                st.subheader(f"Editando ID: {selected_id}")
                cols = st.columns(2)
                epi_name_edit = cols[0].text_input("Nome EPI", value=row.get("epi_name", ''))
                ca_edit = cols[1].text_input("CA", value=row.get("CA", ''))
                quantity_edit = cols[0].number_input("Quantidade", value=int(row.get("quantity", 0)))
                value_edit = cols[1].number_input("Valor", value=float(row.get("value", 0.0)))
                transaction_type_edit = cols[0].selectbox("Transação", ["entrada", "saída"], index=0 if row.get("transaction_type") == "entrada" else 1)
                requester_edit = cols[1].text_input("Requisitante", value=row.get("requester", ''))
                image_url_edit = st.text_input("URL da Imagem", value=row.get("image_url", ''))
                
                if st.form_submit_button("Salvar Edições"):
                    date_str = str(row["date"].date()) if pd.notna(row["date"]) else ''
                    updated_data = [
                        epi_name_edit or '', quantity_edit, transaction_type_edit or '', date_str,
                        value_edit, requester_edit or '', ca_edit or '', image_url_edit or ''
                    ]
                    if sheet_operations.editar_dados(selected_id, updated_data):
                        st.success("Registro editado com sucesso!"); st.rerun()
                    else: st.error("Erro ao editar registro.")

    with st.expander("Excluir registro existente"):
        if not all_ids: return
        selected_id_del = st.selectbox("Selecione o ID para excluir:", all_ids, key="id_delete")
        if st.button("Excluir", type="primary"):
            if sheet_operations.excluir_dados(selected_id_del):
                st.success(f"ID {selected_id_del} excluído com sucesso!"); st.rerun()
            else: st.error("Erro ao excluir registro.")




