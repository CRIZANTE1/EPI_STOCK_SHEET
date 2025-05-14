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
        critical_df = pd.DataFrame({'Estoque': critical_stock})
        st.bar_chart(critical_df, use_container_width=True)
        
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
        
        # Adicionar uma tabela com os valores exatos
        st.write("Detalhamento do estoque:")
        stock_details = pd.DataFrame({
            'EPI': normal_stock.index,
            'Quantidade': normal_stock.values
        }).sort_values('Quantidade', ascending=False)
        
        st.dataframe(stock_details.style.format({'Quantidade': '{:.0f}'}), use_container_width=True)
    else:
        st.warning("Não há itens com estoque positivo.")

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
def analyze_epi_usage_minimalist(df: pd.DataFrame, short_interval_days: int = 7):
    """
    Realiza uma análise do uso de EPIs com apresentação minimalista,
    permitindo filtrar por ano e mês.

    Inclui:
    1. Top 3 EPIs mais requisitados (Lista de Texto).
    2. Top 3 Usuários que mais requisitaram (Lista de Texto).
    3. Análise cruzada: EPIs mais requisitados pelos top usuários (Tabelas Simples).
    4. Análise de frequência: Identificação de requisições frequentes (Texto/Tabela).

    Args:
        df (pd.DataFrame): DataFrame com colunas: 'date', 'transaction_type',
                           'epi_name', 'quantity', 'requester'.
        short_interval_days (int): Limite em dias para requisições frequentes.

    Returns:
        None: Exibe os resultados na interface do Streamlit.

    Raises:
        TypeError: Se df não for um DataFrame.
        ValueError: Se colunas essenciais faltarem ou dados forem inválidos.
    """
    st.subheader("Filtros de Análise")

    # --- 1. Validação de Entrada ---
    if not isinstance(df, pd.DataFrame):
        st.error("Erro: O input fornecido não é um DataFrame do Pandas.")
        raise TypeError("O input deve ser um DataFrame do Pandas.")

    required_columns = ['date', 'transaction_type', 'epi_name', 'quantity', 'requester']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Erro: Colunas essenciais ausentes: {', '.join(missing_columns)}")
        raise ValueError(f"Colunas ausentes: {', '.join(missing_columns)}")

    # --- 2. Pré-processamento Inicial e Limpeza ---
    try:
        df_processed = df.copy()
        # Padronizar tipo de transação
        df_processed['transaction_type'] = df_processed['transaction_type'].fillna('').astype(str).str.lower().str.strip()
        df_saidas = df_processed[df_processed['transaction_type'] == 'saída'].copy()

        if df_saidas.empty:
            st.warning("Nenhuma transação do tipo 'saída' encontrada no DataFrame original.")
            return

        # Limpeza e conversão de 'date' - FAZER ANTES DA FILTRAGEM
        original_rows_date = len(df_saidas)
        df_saidas['date'] = pd.to_datetime(df_saidas['date'], errors='coerce')
        df_saidas.dropna(subset=['date'], inplace=True)
        removed_date = original_rows_date - len(df_saidas)
        if removed_date > 0:
            st.warning(f"Atenção: {removed_date} linha(s) de 'saída' com 'date' inválida ou vazia foram removidas ANTES da filtragem.")

        if df_saidas.empty:
            st.warning("Nenhum dado válido de 'saída' com data válida restante.")
            return

        # Extrair Ano e Mês para filtragem
        df_saidas['year'] = df_saidas['date'].dt.year
        df_saidas['month'] = df_saidas['date'].dt.month

        # --- 3. Widgets de Filtragem (Ano e Mês) ---
        available_years = sorted(df_saidas['year'].unique(), reverse=True)
        if not available_years:
             st.warning("Não foi possível extrair anos válidos das datas.")
             return

        selected_year = st.selectbox("Selecione o Ano:", options=available_years)

        # Filtrar meses disponíveis PARA o ano selecionado
        months_in_year = sorted(df_saidas[df_saidas['year'] == selected_year]['month'].unique())
        # Criar dicionário para mapear número do mês para nome (Português)
        # Usando calendar para obter nomes em inglês e traduzindo manualmente (simplificado)
        # Uma biblioteca de localização seria mais robusta (ex: Babel)
        month_map_pt = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
            7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        available_month_names = ["Todos os Meses"] + [month_map_pt.get(m, f"Mês {m}") for m in months_in_year]

        selected_month_name = st.selectbox("Selecione o Mês:", options=available_month_names)

        # --- 4. Filtragem Efetiva dos Dados ---
        df_filtered = df_saidas[df_saidas['year'] == selected_year].copy()

        if selected_month_name != "Todos os Meses":
            # Encontrar o número do mês correspondente ao nome selecionado
            selected_month_number = None
            for num, name in month_map_pt.items():
                if name == selected_month_name:
                    selected_month_number = num
                    break
            if selected_month_number:
                df_filtered = df_filtered[df_filtered['month'] == selected_month_number].copy()
            else:
                st.error("Erro ao identificar o mês selecionado.") # Should not happen with selectbox
                return

        if df_filtered.empty:
            st.info(f"Nenhum dado de 'saída' encontrado para {selected_month_name} / {selected_year}.")
            return

        # --- 5. Limpeza Adicional nos Dados Filtrados ---

        # Limpeza e conversão de 'quantity'
        original_rows_qty = len(df_filtered)
        df_filtered['quantity'] = pd.to_numeric(df_filtered['quantity'], errors='coerce')
        df_filtered.dropna(subset=['quantity'], inplace=True)
        removed_quantity = original_rows_qty - len(df_filtered)
        if removed_quantity > 0:
            st.warning(f"Atenção: {removed_quantity} linha(s) com 'quantity' inválida ou vazia foram removidas do período selecionado.")

        # Tentar converter 'quantity' para int se todos forem inteiros
        if not df_filtered.empty and pd.api.types.is_float_dtype(df_filtered['quantity']):
             if (df_filtered['quantity'].fillna(0) % 1 == 0).all(): # Handle potential NaNs introduced by coerce before dropna
                 try:
                     df_filtered['quantity'] = df_filtered['quantity'].astype(int)
                 except ValueError:
                     pass # Mantém como float se a conversão falhar

        # Limpeza de texto (remover espaços extras)
        df_filtered['epi_name'] = df_filtered['epi_name'].fillna('').astype(str).str.strip()
        df_filtered['requester'] = df_filtered['requester'].fillna('').astype(str).str.strip()

        # Remover linhas onde EPI ou requisitante ficou vazio após strip
        df_filtered = df_filtered[(df_filtered['epi_name'] != '') & (df_filtered['requester'] != '')]

        if df_filtered.empty:
            st.info(f"Nenhum dado válido (com EPI, Requisitante e Quantidade válidos) encontrado para {selected_month_name} / {selected_year} após limpeza final.")
            return

    except Exception as e:
        st.error(f"Erro durante o pré-processamento ou filtragem: {e}")
        # Optionally re-raise if debugging: raise e
        return # Impede a continuação se houver erro aqui

    # --- 6. Análises e Apresentação Minimalista (usando df_filtered) ---
    st.divider() # Linha divisória após os filtros
    period_str = f"{selected_month_name} / {selected_year}" if selected_month_name != "Todos os Meses" else f"Todo o ano de {selected_year}"
    st.header(f"Análise de Utilização de EPIs (Saídas) - {period_str}")

    # 6.1. Top EPIs (Texto)
    st.subheader("Top 3 EPIs Utilizados")
    try:
        top_epis_series = df_filtered.groupby('epi_name')['quantity'].sum().sort_values(ascending=False).head(3)
        if not top_epis_series.empty:
            for i, (epi, quantity) in enumerate(top_epis_series.items(), 1):
                 qty_str = f"{int(quantity):,}" if quantity == int(quantity) else f"{quantity:,.2f}"
                 st.text(f"{i}. {epi}: {qty_str}")
        else:
            st.info(f"Sem dados de EPIs para listar no período ({period_str}).")
    except Exception as e:
        st.error(f"Erro na análise de top EPIs: {e}")

    # 6.2. Top Usuários (Texto)
    st.subheader("Top 3 Usuários (Requisições)")
    try:
        top_users_series = df_filtered.groupby('requester')['quantity'].sum().sort_values(ascending=False).head(3)
        if not top_users_series.empty:
            top_users_list = top_users_series.index.tolist()
            for i, (user, quantity) in enumerate(top_users_series.items(), 1):
                 qty_str = f"{int(quantity):,}" if quantity == int(quantity) else f"{quantity:,.2f}"
                 st.text(f"{i}. {user}: {qty_str}")
        else:
            st.info(f"Sem dados de usuários para listar no período ({period_str}).")
            top_users_list = []
    except Exception as e:
        st.error(f"Erro na análise de top usuários: {e}")
        top_users_list = []

    # 6.3. Análise Cruzada: EPIs por Top Usuário (Tabelas Simples)
    st.subheader("Análise: EPIs por Top Usuário") # 'Crossed Swords' Emoji
    if not top_users_list:
        st.info(f"Análise não disponível (sem top usuários identificados no período {period_str}).")
    else:
        try:
            # Filtrar novamente o df_filtered SÓ para os top usuários (já está filtrado por período)
            df_top_users_data = df_filtered[df_filtered['requester'].isin(top_users_list)]

            if df_top_users_data.empty:
                 # Isso não deveria acontecer se top_users_list foi gerado de df_filtered, mas é uma checagem segura
                 st.info(f"Não há dados de requisição para os top usuários identificados no período ({period_str}).")
            else:
                # Calcular uso por EPI para os top usuários NO PERÍODO
                user_epi_usage = df_top_users_data.groupby(['requester', 'epi_name'])['quantity'].sum().reset_index()

                # Iterar sobre a lista ordenada de top usuários (mantém a ordem do top 3)
                for user in top_users_list:
                    st.markdown(f"**{user}**") # Nome do usuário em negrito
                    # Pegar os dados DESTE usuário NO PERÍODO
                    user_data = user_epi_usage[user_epi_usage['requester'] == user].sort_values(by='quantity', ascending=False).head(5) # Top 5 EPIs por usuário no período

                    if not user_data.empty:
                        user_data_display = user_data[['epi_name', 'quantity']].rename(columns={'epi_name': 'EPI', 'quantity': 'Quantidade'})
                        # Formatar quantidade na tabela
                        user_data_display['Quantidade'] = user_data_display['Quantidade'].apply(
                            lambda x: f"{int(x):,}" if x == int(x) else f"{x:,.2f}"
                        )
                        st.table(user_data_display.set_index('EPI'))
                    else:
                        # Mensagem se o usuário (que está no top 3 geral do período) não tiver dados *cruzados* (raro, mas possível se dados foram limpos entre etapas)
                        st.caption(f"Nenhum EPI específico registrado para este usuário no período {period_str}.")
                    # st.markdown("---") # Remover divisória entre usuários

        except Exception as e:
            st.error(f"Erro na análise cruzada usuário x EPI: {e}")

    # 6.4. Análise de Frequência (Texto e Tabela opcional)
    st.subheader(f"Requisições Frequentes (Intervalo ≤ {short_interval_days} dias)")
    try:
        if len(df_filtered) < 2:
             st.info(f"Dados insuficientes para análise de frequência no período ({period_str}).")
             # Não retorna aqui, pois pode haver outras análises válidas.
        else:
            # Ordenar dentro do período filtrado
            df_sorted = df_filtered.sort_values(by=['requester', 'epi_name', 'date']).copy()
            # Calcular diferença apenas para o mesmo usuário e mesmo EPI DENTRO DO PERÍODO
            df_sorted['time_since_prev_request'] = df_sorted.groupby(['requester', 'epi_name'])['date'].diff()
            threshold_timedelta = pd.Timedelta(days=short_interval_days)

            # Filtrar requisições frequentes (não nulas e dentro do threshold) NO PERÍODO
            frequent_requests = df_sorted[
                df_sorted['time_since_prev_request'].notna() &
                (df_sorted['time_since_prev_request'] <= threshold_timedelta)
            ].copy()

            if not frequent_requests.empty:
                count = len(frequent_requests)
                st.warning(f"Identificada(s) {count} requisição(ões) feita(s) em intervalo curto no período ({period_str}).")

                # Resumo textual simples
                st.markdown("**Resumo:**")
                top_freq_users = frequent_requests['requester'].value_counts().head(3)
                top_freq_epis = frequent_requests['epi_name'].value_counts().head(3)

                if not top_freq_users.empty:
                    st.text("Usuários mais envolvidos:")
                    for user, num in top_freq_users.items():
                        st.text(f"- {user} ({num} ocorrência(s))")

                if not top_freq_epis.empty:
                    st.text("EPIs mais envolvidos:")
                    for epi, num in top_freq_epis.items():
                        st.text(f"- {epi} ({num} ocorrência(s))")

                # Detalhes em um expander
                with st.expander(f"Ver detalhes das {count} requisições frequentes ({period_str})"):
                    frequent_requests_display = frequent_requests[[
                        'date', 'requester', 'epi_name', 'quantity', 'time_since_prev_request'
                    ]].rename(columns={
                        'date': 'Data',
                        'requester': 'Requisitante',
                        'epi_name': 'EPI',
                        'quantity': 'Qtd.',
                        'time_since_prev_request': 'Intervalo Anterior' # Renomeado para clareza
                    }).sort_values(by='Data', ascending=False) # Ordenar por data recente

                    # Formatar colunas para melhor leitura
                    frequent_requests_display['Data'] = frequent_requests_display['Data'].dt.strftime('%d/%m/%Y')
                    frequent_requests_display['Intervalo Anterior'] = frequent_requests_display['Intervalo Anterior'].apply(lambda x: f"{x.days} dias")
                    frequent_requests_display['Qtd.'] = frequent_requests_display['Qtd.'].apply(
                        lambda x: f"{int(x):,}" if x == int(x) else f"{x:,.2f}"
                    )

                    st.dataframe(frequent_requests_display, hide_index=True, use_container_width=True)

            else:
                st.success(f"Nenhuma requisição frequente identificada no período ({period_str}, intervalo ≤ {short_interval_days} dias).")

    except KeyError as e:
         st.error(f"Erro na análise de frequência: Coluna necessária não encontrada ({e}). Verifique os nomes das colunas.")
    except Exception as e:
        st.error(f"Erro inesperado na análise de frequência: {e}")





