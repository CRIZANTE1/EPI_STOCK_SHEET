import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from datetime import datetime
from fuzzywuzzy import process
import altair as alt

def configurar_pagina():
    st.set_page_config(
        page_title="Página Inicial",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def sidebar():
    with st.sidebar:
        page = st.sidebar.selectbox("Selecione a página:", ["Página Inicial", "Administração"])
        if page == "Página Inicial":  # Página inicial da aplicação
            st.caption('EPI Stock Management')
            
        
        
def front_page():
    
    st.title("Controle de Estoque de EPIs") 
       
    sheet_operations = SheetOperations()

    if 'data' not in st.session_state:
        data = sheet_operations.carregar_dados()
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            st.session_state['data'] = df
        else:
            st.error("Não foi possível carregar a planilha")
            return

    if 'data' in st.session_state:
        df = st.session_state['data']
        
    # Converter a coluna 'Date' para o formato datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Tratar valores vazios na coluna 'value' antes de converter
    df['value'] = df['value'].apply(lambda x: 0 if x == '' else float(str(x).replace('.', '').replace(',', '.')))

    # Primeiro mostrar as funções de edição
    entrance_exit_edit_delete()

    # Depois mostrar o DataFrame
    st.write("### Registros de Entradas e Saídas")
    st.dataframe(data=df,
                 column_config={
                     'value': st.column_config.NumberColumn(
                         "Valor",
                         help="O preço do material em Reais",
                         min_value=0,
                         max_value=100000,
                         step=1,
                         format='$ %.2f'
                     ),
                     'epi_name': st.column_config.TextColumn(
                         'Equipamento',
                         help='Nome do EPI',
                         default='st.',
                         max_chars=50,
                     ),
                     'quantity': st.column_config.NumberColumn(
                         'Quantidade',
                         help='Quantidade de EPI',
                         min_value=0,
                         max_value=1000000,
                         step=1,
                         format='%.0f',
                     ),
                     'transaction_type': st.column_config.TextColumn(
                         'Transação',
                         help='Entrada ou Saída',
                         default='st.',
                         max_chars=50,
                     ),
                     'CA': st.column_config.NumberColumn(
                         'CA',
                         help='Certificado de Aprovação se aplicável',
                         min_value=0,
                         max_value=1000000,
                         step=1,
                         format='%.0f',
                     ),
                     'date': st.column_config.DateColumn(
                         'Data',
                         help='Data da transação',
                         format='DD/MM/YYYY',
                         step=1,
                     ),
                     'requester': st.column_config.TextColumn(
                         'Requisitante',
                         help='Requisitante do Equipamento',
                         default='st.',
                         max_chars=50,
                     ),
                 }, hide_index=True)    
    
    # Por último, mostrar o gráfico
    st.write("### Análise do Estoque")
    calc_position(df)

#-----------------------------------------------------------------------------------------------------------------------
    """
    A função `calc_position` calcula a posição atual do estoque de itens com base nos dados de entrada e
    visualiza os resultados usando Altair para exibir um gráfico de barras.
    
    :param name: O parâmetro `name` na função `get_closest_match_name` é o nome para o qual você
    deseja encontrar a correspondência mais próxima na lista de opções
    :param choices: O parâmetro `choices` na função `get_closest_match_name` representa uma lista
    de opções ou nomes para comparar com o `name` de entrada a fim de encontrar a correspondência mais próxima usando
    correspondência de string difusa
    :return: A função `calc_position` retorna uma visualização da posição atual do estoque para
    os 10 menores valores, incluindo valores negativos e zero, usando Altair. A função calcula
    o estoque atual subtraindo as saídas totais das entradas totais de itens de Equipamento de Proteção Individual (EPI) em um DataFrame, 
    depois seleciona os 10 menores valores para visualização em um gráfico de barras. Se os valores de estoque calculados
    """
def get_closest_match_name(name, choices):
    # Retorna o nome mais aproximado usando a função `extractOne` do fuzzywuzzy
    closest_match, score = process.extractOne(name, choices)
    return closest_match if score > 99 else name

def calc_position(df):
    # Garantir que a coluna 'quantity' seja numérica, forçando erros a se tornarem NaN
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    
    # Obter os nomes únicos dos EPIs e mapear para o nome mais próximo
    unique_epi_names = df['epi_name'].unique()
    name_mapping = {name: get_closest_match_name(name, unique_epi_names) for name in unique_epi_names}
    df['epi_name'] = df['epi_name'].map(name_mapping)
    
    # Calcular o estoque atual (entrada - saída)
    epi_entries = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
    epi_exits = df[df['transaction_type'] == 'saida'].groupby('epi_name')['quantity'].sum()
    
    # Subtrair as saídas das entradas para obter o estoque
    total_epi = epi_entries - epi_exits
    
    # Selecionar os 10 menores valores, incluindo negativos e zerados
    total_epi = total_epi.sort_values().head(10)
    
    # Verifique se o total_epi está vazio ou contém valores válidos
    if total_epi.empty:
        st.warning("O cálculo do estoque resultou em nenhum valor ou todos os valores são iguais.")
        return
    
    # Criar um dataframe para o gráfico
    total_epi_df = total_epi.reset_index()
    total_epi_df.columns = ['EPI', 'Estoque']
    
    # Criar o gráfico com Altair
    chart = alt.Chart(total_epi_df).mark_bar().encode(
        x=alt.X('EPI:N', title='Tipo de EPI'),
        y=alt.Y('Estoque:Q', title='Estoque'),
        color=alt.Color('Estoque:Q', scale=alt.Scale(scheme='redyellowgreen')),  # Alterar o esquema de cores
        tooltip=['EPI', 'Estoque']
    ).properties(
        title='Demonstrativo da posição do estoque atual (10 menores valores)'
    )
    
    # Exibir o gráfico
    st.altair_chart(chart, use_container_width=True)
    

#-----------------------------------------------------------------------------------------------------------------------
"""
    Esta função Python carrega dados de empregados de uma planilha especificada e retorna uma lista de
    nomes de empregados, exibindo uma mensagem de erro se os dados não puderem ser carregados.
    
    :param sheet_operations: `sheet_operations` é provavelmente um objeto ou módulo que contém métodos para
    carregar dados de uma planilha ou worksheet. Nesta função específica `carregar_empregados`, parece ser
    usado para carregar dados de empregados de uma aba específica chamada 'empregados'. A função tenta
    carregar os dados,
    :return: A função `carregar_empregados` retorna uma lista de nomes de empregados extraídos da
    coluna 'name_empregado' do DataFrame `df_empregados`. Se houver um problema ao carregar os dados dos
    empregados, uma lista vazia é retornada e uma mensagem de erro é exibida usando `st.error`.
    """        
def carregar_empregados(sheet_operations):
    
    empregados_data = sheet_operations.carregar_dados_aba('empregados')
    if empregados_data:
        df_empregados = pd.DataFrame(empregados_data[1:], columns=empregados_data[0])
        return df_empregados['name_empregado'].tolist()
    else:
        st.error("Não foi possível carregar os dados dos empregados")
        return []
    
#-----------------------------------------------------------------------------------------------------------------------    

from auth import is_admin

def entrance_exit_edit_delete():
    if not is_admin():
        st.error("Acesso negado. Apenas administradores podem realizar esta ação.")
        return

    sheet_operations = SheetOperations()
    data = sheet_operations.carregar_dados()
    if data:
        df = pd.DataFrame(data[1:], columns=data[0])
    else:
        st.error("Não foi possível carregar a planilha")
        return

    required_columns = ['id', 'epi_name', 'quantity', 'transaction_type', 'date', 'value', 'requester', 'CA']
    if not all(column in df.columns for column in required_columns):
        st.error("A planilha não contém todas as colunas necessárias.")
        return

    # Verificar a presença da coluna 'Date' e renomeá-la se necessário
    if 'date' in df.columns:
        df.rename(columns={'date': 'Date'}, inplace=True)

    all_entrance_epi_names = df[df['transaction_type'] == 'entrada']['epi_name'].unique()
    empregados = carregar_empregados(sheet_operations)

    with st.expander("Inserir novo registro"):  # Expander para inserção
        requester = None
        transaction_type = st.selectbox("Tipo de transação:", ["entrada", "saída"])

        if transaction_type == "entrada":
            epi_name = st.text_input("Nome do EPI:", "")
        elif transaction_type == "saída":
            if len(all_entrance_epi_names) > 0:
                epi_name = st.selectbox("Nome do EPI:", all_entrance_epi_names)
                ca_value = df[df['epi_name'] == epi_name]['CA'].values[0]
                st.text_input("CA:", value=ca_value, disabled=True)
            else:
                st.write("Não há entradas registradas no banco de dados.")

        quantity = st.number_input("Quantidade:", min_value=0, step=1)
        value = st.number_input("Valor:", min_value=0.0, step=0.01) if transaction_type == "entrada" else 0
        ca = st.text_input("CA:", "") if transaction_type == "entrada" else ca_value
        if transaction_type == "saída":
            requester = st.selectbox("Solicitante:", empregados)
            exit_date = st.date_input("Data da saída:")
        
        if st.button("Adicionar"):
            if epi_name and quantity:
                new_data = [epi_name, quantity, transaction_type, str(datetime.now().date()), value, requester, ca]
                sheet_operations.adc_dados(new_data)
            else:
                st.warning("Por favor, preencha todos os campos.")

    with st.expander("Editar registro existente"):  # Expander para edição
        all_ids = df['id'].tolist()
        selected_id = st.selectbox("Selecione a linha que será editada:", all_ids)

        if selected_id:
            st.session_state.id = selected_id

        if st.session_state.get('id'):
            id = st.session_state.id
            selected_row = df[df['id'] == id].iloc[0]
            epi_name = st.text_input("Nome do EPI:", value=selected_row["epi_name"])
            quantity = st.number_input("Quantidade:", value=int(selected_row["quantity"]))
            value = st.number_input("Valor:", value=float(selected_row["value"]))
            transaction_type = st.text_input("Tipo de transação:", value=selected_row["transaction_type"])

            if st.button("Editar"):
                df.loc[df['id'] == id, ["epi_name", "quantity", "value", "transaction_type"]] = [epi_name, quantity, value, transaction_type]
                st.success("EPI editado com sucesso!")
                del st.session_state['id']

    with st.expander("Excluir registro existente"):  # Expander para exclusão
        all_epi_ids = df['id'].tolist()

        if all_epi_ids:
            selected_id = st.selectbox("Com Cautela! Selecione o ID da entrada ou saída para excluir:", all_epi_ids)
            if st.button("Excluir"):
                df = df[df['id'] != selected_id]
                st.success(f"A entrada/saída com ID {selected_id} foi excluída com sucesso!")
        else:
            st.write("Não há entradas/saídas registradas no banco de dados.")
