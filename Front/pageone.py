import streamlit as st
import pandas as pd
from End.Operations import SheetOperations
from datetime import datetime
from fuzzywuzzy import process
import altair as alt
import plotly.express as px 
import calendar
from auth import is_admin


def configurar_pagina():
    st.set_page_config(
        page_title="Página Inicial",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
       
        
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

    # Adicionando a seção de análise de uso de EPI
    st.write("### Insights de Uso de EPI")
    analyze_epi_usage_minimalist(df)

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
    # Retorna o nome mais aproximado usando a função `extractOne` do fuzzywuzzy
    # Aumenta o limiar para maior precisão, se necessário, ou diminui se estiver agrupando demais
    closest_match, score = process.extractOne(name, choices, score_cutoff=90) # Ajustado score_cutoff
    return closest_match if score >= 90 else name # Retorna o original se a pontuação for baixa

def calc_position(df):
    # Fazer uma cópia para evitar SettingWithCopyWarning
    df = df.copy()

    # Garantir que a coluna 'quantity' seja numérica, preenchendo NaNs com 0
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)

    # Normalizar nomes dos EPIs usando uma nova coluna
    unique_epi_names = df['epi_name'].dropna().unique()  # Ignorar NaNs nos nomes
    if len(unique_epi_names) == 0:
        st.warning("Não há nomes de EPI válidos nos dados.")
        return
        
    name_mapping = {name: get_closest_match_name(name, unique_epi_names) for name in unique_epi_names}
    df['epi_name_normalized'] = df['epi_name'].map(name_mapping)

    # Filtrar linhas onde a normalização falhou (raro, mas possível se 'epi_name' for NaN)
    df.dropna(subset=['epi_name_normalized'], inplace=True)

    # Calcular entradas e saídas usando o nome normalizado e preencher NaNs com 0
    epi_entries = df[df['transaction_type'].str.lower() == 'entrada'].groupby('epi_name_normalized')['quantity'].sum().fillna(0)
    epi_exits = df[df['transaction_type'].str.lower() == 'saida'].groupby('epi_name_normalized')['quantity'].sum().fillna(0)

    # Usar reindex().add() para garantir que todos os EPIs sejam considerados
    all_epis = epi_entries.index.union(epi_exits.index)
    total_epi = epi_entries.reindex(all_epis, fill_value=0) - epi_exits.reindex(all_epis, fill_value=0)

    # Verificar se há dados para plotar após o cálculo
    if total_epi.empty or total_epi.isnull().all():
        st.warning("Não há dados de estoque válidos para exibir no gráfico após o cálculo.")
        return

    # Criar dois DataFrames separados: um para itens com estoque baixo/crítico e outro para o resto
    total_epi_sorted = total_epi.sort_values()
    
    # Identificar itens com estoque crítico (negativos ou zero)
    critical_stock = total_epi_sorted[total_epi_sorted <= 0]
    if not critical_stock.empty:
        st.error("### EPIs com Estoque Crítico ⚠️")
               
        
        # Mostrar lista detalhada dos itens críticos
        st.write("Detalhamento dos itens críticos:")
        for epi, qty in critical_stock.items():
            st.write(f"- {epi}: {int(qty) if qty == int(qty) else qty:.2f}")
    
    # Criar DataFrame com todos os itens em estoque (positivos)
    normal_stock = total_epi_sorted[total_epi_sorted > 0]
    if not normal_stock.empty:
        st.write("### Posição Atual do Estoque 📊")
        normal_df = pd.DataFrame({'Estoque': normal_stock})
        st.bar_chart(normal_df, use_container_width=True)
        

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

def entrance_exit_edit_delete():
    """
    Esta função Python gerencia a inserção, edição e exclusão de registros de entrada e saída em uma planilha,
    com verificações de validação e campos de entrada para o usuário.
    :return: A função `entrance_exit_edit_delete()` retorna mensagens diferentes com base nas condições
    atendidas durante sua execução.  Os possíveis valores retornados são: mensagens de sucesso, erro ou
    avisos, dependendo se a operação foi bem sucedida, se houve algum erro durante a operação ou se
    algum campo obrigatório não foi preenchido.  A função também pode não retornar explicitamente nada
    (None) em alguns casos.
    """
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

    all_entrance_epi_names = df[df['transaction_type'] == 'entrada']['epi_name'].unique()
    empregados = carregar_empregados(sheet_operations)

    with st.expander("Inserir novo registro"):
        requester = None
        transaction_type = st.selectbox("Tipo de transação:", ["entrada", "saída"], key="transaction_type_add")

        if transaction_type == "entrada":
            epi_name = st.text_input("Nome do EPI:", "", key="epi_name_add")
        elif transaction_type == "saída":
            if len(all_entrance_epi_names) > 0:
                epi_name = st.selectbox("Nome do EPI:", all_entrance_epi_names, key="epi_name_select_add")
                ca_value = df[df['epi_name'] == epi_name]['CA'].values[0]
                st.text_input("CA:", value=ca_value, disabled=True, key="ca_display_add")
            else:
                st.write("Não há entradas registradas no banco de dados.")

        quantity = st.number_input("Quantidade:", min_value=0, step=1, key="quantity_add")
        value = st.number_input("Valor:", min_value=0.0, step=0.01, key="value_add") if transaction_type == "entrada" else 0
        ca = st.text_input("CA:", "", key="ca_add") if transaction_type == "entrada" else ca_value
        if transaction_type == "saída":
            requester = st.selectbox("Solicitante:", empregados, key="requester_add")
            exit_date = st.date_input("Data da saída:", key="date_add")
        
        if st.button("Adicionar", key="btn_add"):
            if epi_name and quantity:
                new_data = [epi_name, quantity, transaction_type, str(datetime.now().date()), value, requester, ca]
                sheet_operations.adc_dados(new_data)
                st.rerun()
            else:
                st.warning("Por favor, preencha todos os campos.")

    with st.expander("Editar registro existente"):
        all_ids = df['id'].tolist()
        selected_id = st.selectbox("Selecione a linha que será editada:", all_ids, key="id_edit")

        if selected_id:
            selected_row = df[df['id'] == selected_id].iloc[0]
            epi_name = st.text_input("Nome do EPI:", value=selected_row["epi_name"], key="epi_name_edit")
            quantity = st.number_input("Quantidade:", value=int(selected_row["quantity"]), key="quantity_edit")
            value = st.number_input("Valor:", value=float(selected_row["value"]), key="value_edit")
            transaction_type = st.selectbox("Tipo de transação:", ["entrada", "saída"], 
                                         index=0 if selected_row["transaction_type"] == "entrada" else 1,
                                         key="transaction_type_edit")

            if st.button("Editar", key="btn_edit"):
                updated_data = [epi_name, quantity, transaction_type, selected_row["date"], value, selected_row["requester"], selected_row["CA"]]
                if sheet_operations.editar_dados(selected_id, updated_data):
                    st.success("EPI editado com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao editar o registro.")

    with st.expander("Excluir registro existente"):
        all_epi_ids = df['id'].tolist()
        if all_epi_ids:
            selected_id = st.selectbox("Com Cautela! Selecione o ID da entrada ou saída para excluir:", 
                                     all_epi_ids, 
                                     key="id_delete")
            if st.button("Excluir", key="btn_delete"):
                if sheet_operations.excluir_dados(selected_id):
                    st.success(f"A entrada/saída com ID {selected_id} foi excluída com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao excluir o registro.")
        else:
            st.write("Não há entradas/saídas registradas no banco de dados.")


#-----------------------------------------------------------------------------------------------------------------------









