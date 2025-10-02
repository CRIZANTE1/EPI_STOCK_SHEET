import streamlit as st
import pandas as pd
from datetime import datetime
from auth import is_admin
from End.Operations import SheetOperations

def admin_page():
    if not is_admin():
        st.error("Acesso negado. Esta página é restrita a administradores.")
        if st.button("Voltar para Página Principal"):
            st.session_state.pagina_atual = 'principal'
            st.rerun()
        return

    st.title("Painel de Administração")
    opcao_admin = st.sidebar.radio(
        "Selecione a função:",
        ["Configurações do Sistema", "Gestão de Orçamento", "Voltar para Principal"]
    )

    if opcao_admin == "Voltar para Principal":
        st.session_state.pagina_atual = 'principal'
        st.rerun()
    elif opcao_admin == "Gestão de Orçamento":
        budget_management_page()
    else:
        st.header("Configurações do Sistema")
        
        st.subheader("Informações de Login OIDC")
        st.json({
            "status": "Ativo",
            "provedor": "Configurado no secrets.toml"
        })

        st.markdown("""
        Para alterar as configurações de login OIDC:

        1. Edite o arquivo `.streamlit/secrets.toml`
        2. Configure as credenciais do provedor OIDC desejado
        3. Reinicie a aplicação para que as alterações tenham efeito
        """)

        st.subheader("Status do Sistema")
        st.json({
            "sistema": "Controle de Estoque de EPIs",
            "versão": "1.0.0",
            "modo_login": "OIDC (OpenID Connect)",
            "status": "Ativo",
            "Developer": "Cristian Ferreira Carlos",
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

def budget_management_page():
    st.header("💰 Gestão de Orçamento Anual")
    
    sheet_operations = SheetOperations()
    sheet_operations.ensure_budget_sheet_exists()
    
    # Carregar dados de orçamento
    @st.cache_data(ttl=60)
    def load_budget_data():
        budget_data = sheet_operations.carregar_dados_budget()
        if budget_data and len(budget_data) > 1:
            df = pd.DataFrame(budget_data[1:], columns=budget_data[0])
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
            df['ano'] = pd.to_numeric(df['ano'], errors='coerce').astype('Int64')
            return df
        return pd.DataFrame(columns=['id', 'ano', 'valor'])
    
    df_budget = load_budget_data()
    
    # Calcular gastos por ano
    @st.cache_data(ttl=60)
    def calculate_spending_by_year():
        stock_data = sheet_operations.carregar_dados()
        if not stock_data or len(stock_data) <= 1:
            return pd.DataFrame(columns=['ano', 'gasto_total'])
        
        df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['value'] = df['value'].apply(lambda x: 0 if x == '' else float(str(x).replace('.', '').replace(',', '.')))
        df['transaction_type'] = df['transaction_type'].str.lower().str.strip()
        
        # Filtrar apenas entradas
        df_entradas = df[df['transaction_type'] == 'entrada'].copy()
        df_entradas['ano'] = df_entradas['date'].dt.year
        df_entradas['valor_total'] = df_entradas['quantity'] * df_entradas['value']
        
        gastos = df_entradas.groupby('ano')['valor_total'].sum().reset_index()
        gastos.columns = ['ano', 'gasto_total']
        return gastos
    
    df_gastos = calculate_spending_by_year()
    
    # Abas para organizar funcionalidades
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "➕ Gerenciar Orçamentos", "📈 Análise Detalhada"])
    
    with tab1:
        st.subheader("Acompanhamento de Orçamento")
        
        if df_budget.empty:
            st.info("📝 Nenhum orçamento cadastrado ainda. Use a aba 'Gerenciar Orçamentos' para adicionar.")
        else:
            # Seletor de ano
            anos_disponiveis = sorted(df_budget['ano'].dropna().unique(), reverse=True)
            ano_selecionado = st.selectbox("Selecione o ano para acompanhamento:", anos_disponiveis)
            
            # Buscar orçamento do ano
            orcamento_ano = df_budget[df_budget['ano'] == ano_selecionado]
            
            if orcamento_ano.empty:
                st.warning(f"Nenhum orçamento encontrado para {ano_selecionado}")
            else:
                valor_orcado = orcamento_ano['valor'].iloc[0]
                
                # Buscar gasto do ano
                gasto_ano = df_gastos[df_gastos['ano'] == ano_selecionado]
                valor_gasto = gasto_ano['gasto_total'].iloc[0] if not gasto_ano.empty else 0
                
                # Calcular percentual
                percentual_usado = (valor_gasto / valor_orcado * 100) if valor_orcado > 0 else 0
                valor_restante = valor_orcado - valor_gasto
                
                # Métricas
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Orçamento Total", f"R$ {valor_orcado:,.2f}")
                col2.metric("Gasto Atual", f"R$ {valor_gasto:,.2f}")
                col3.metric("Disponível", f"R$ {valor_restante:,.2f}", 
                           delta=f"{percentual_usado:.1f}% usado")
                
                # Determinar cor da métrica
                if percentual_usado < 70:
                    status_cor = "🟢"
                elif percentual_usado < 90:
                    status_cor = "🟡"
                else:
                    status_cor = "🔴"
                    
                col4.metric("Status", f"{status_cor} {percentual_usado:.1f}%")
                
                # Barra de progresso
                st.markdown("### Progresso do Orçamento")
                st.progress(min(percentual_usado / 100, 1.0))
                
                # Alerta se ultrapassar
                if percentual_usado > 100:
                    st.error(f"⚠️ ATENÇÃO: Orçamento ultrapassado em R$ {abs(valor_restante):,.2f}!")
                elif percentual_usado > 90:
                    st.warning(f"⚠️ Atenção: Restam apenas {100 - percentual_usado:.1f}% do orçamento!")
                elif percentual_usado > 70:
                    st.info(f"ℹ️ Você já utilizou {percentual_usado:.1f}% do orçamento anual.")
                
                # Gráfico de evolução mensal (se ano atual)
                if ano_selecionado == datetime.now().year:
                    st.markdown("### Evolução Mensal")
                    
                    stock_data = sheet_operations.carregar_dados()
                    if stock_data and len(stock_data) > 1:
                        df = pd.DataFrame(stock_data[1:], columns=stock_data[0])
                        df['date'] = pd.to_datetime(df['date'], errors='coerce')
                        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
                        df['value'] = df['value'].apply(lambda x: 0 if x == '' else float(str(x).replace('.', '').replace(',', '.')))
                        df['transaction_type'] = df['transaction_type'].str.lower().str.strip()
                        
                        df_ano = df[(df['date'].dt.year == ano_selecionado) & (df['transaction_type'] == 'entrada')].copy()
                        df_ano['mes'] = df_ano['date'].dt.month
                        df_ano['valor_total'] = df_ano['quantity'] * df_ano['value']
                        
                        gastos_mensais = df_ano.groupby('mes')['valor_total'].sum().reindex(range(1, 13), fill_value=0)
                        gastos_acumulados = gastos_mensais.cumsum()
                        
                        chart_data = pd.DataFrame({
                            'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                            'Gasto Acumulado': gastos_acumulados.values,
                            'Orçamento': [valor_orcado] * 12
                        })
                        
                        st.line_chart(chart_data.set_index('Mês'))
    
    with tab2:
        st.subheader("Gerenciar Orçamentos")
        
        # Adicionar novo orçamento
        with st.expander("➕ Adicionar Novo Orçamento", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                novo_ano = st.number_input("Ano:", min_value=2020, max_value=2050, 
                                          value=datetime.now().year, key="add_ano")
            with col2:
                novo_valor = st.number_input("Valor Orçado (R$):", min_value=0.0, 
                                            step=1000.0, format="%.2f", key="add_valor")
            
            if st.button("Adicionar Orçamento", type="primary"):
                # Verificar se já existe orçamento para o ano
                if not df_budget.empty and novo_ano in df_budget['ano'].values:
                    st.error(f"Já existe um orçamento cadastrado para o ano {novo_ano}. Use a opção de editar.")
                else:
                    if sheet_operations.adc_budget(int(novo_ano), float(novo_valor)):
                        st.success(f"Orçamento de R$ {novo_valor:,.2f} adicionado para {novo_ano}!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao adicionar orçamento.")
        
        # Editar orçamento existente
        if not df_budget.empty:
            with st.expander("✏️ Editar Orçamento Existente", expanded=False):
                ids_disponiveis = df_budget['id'].tolist()
                
                # Criar dicionário para exibição mais amigável
                display_dict = {f"{row['ano']} - R$ {row['valor']:,.2f} (ID: {row['id']})": row['id'] 
                               for _, row in df_budget.iterrows()}
                
                selected_display = st.selectbox("Selecione o orçamento:", list(display_dict.keys()))
                selected_id = display_dict[selected_display]
                
                row = df_budget[df_budget['id'] == selected_id].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    edit_ano = st.number_input("Ano:", min_value=2020, max_value=2050, 
                                              value=int(row['ano']), key="edit_ano")
                with col2:
                    edit_valor = st.number_input("Valor Orçado (R$):", min_value=0.0, 
                                                value=float(row['valor']), step=1000.0, 
                                                format="%.2f", key="edit_valor")
                
                if st.button("Salvar Alterações", type="primary"):
                    if sheet_operations.editar_budget(selected_id, int(edit_ano), float(edit_valor)):
                        st.success("Orçamento atualizado com sucesso!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar orçamento.")
            
            # Excluir orçamento
            with st.expander("🗑️ Excluir Orçamento", expanded=False):
                selected_display_del = st.selectbox("Selecione o orçamento para excluir:", 
                                                   list(display_dict.keys()), key="del_select")
                selected_id_del = display_dict[selected_display_del]
                
                st.warning("⚠️ Esta ação não pode ser desfeita!")
                
                if st.button("Confirmar Exclusão", type="primary"):
                    if sheet_operations.excluir_budget(selected_id_del):
                        st.success("Orçamento excluído com sucesso!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao excluir orçamento.")
        
        # Exibir tabela de orçamentos
        st.markdown("---")
        st.subheader("Orçamentos Cadastrados")
        if df_budget.empty:
            st.info("Nenhum orçamento cadastrado.")
        else:
            df_display = df_budget.sort_values('ano', ascending=False).copy()
            df_display['valor'] = df_display['valor'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_display[['ano', 'valor']], hide_index=True, use_container_width=True)
    
    with tab3:
        st.subheader("Análise Comparativa")
        
        if df_budget.empty or df_gastos.empty:
            st.info("Dados insuficientes para análise comparativa.")
        else:
            # Merge dos dados
            df_comparacao = pd.merge(df_budget, df_gastos, on='ano', how='left')
            df_comparacao['gasto_total'] = df_comparacao['gasto_total'].fillna(0)
            df_comparacao['percentual'] = (df_comparacao['gasto_total'] / df_comparacao['valor'] * 100).round(2)
            df_comparacao['diferenca'] = df_comparacao['valor'] - df_comparacao['gasto_total']
            
            # Métricas gerais
            st.markdown("### Resumo Geral")
            col1, col2, col3 = st.columns(3)
            col1.metric("Anos com Orçamento", len(df_comparacao))
            col2.metric("Orçamento Total", f"R$ {df_comparacao['valor'].sum():,.2f}")
            col3.metric("Gasto Total", f"R$ {df_comparacao['gasto_total'].sum():,.2f}")
            
            # Tabela comparativa
            st.markdown("### Comparação Ano a Ano")
            df_display_comp = df_comparacao[['ano', 'valor', 'gasto_total', 'diferenca', 'percentual']].copy()
            df_display_comp.columns = ['Ano', 'Orçado', 'Gasto', 'Diferença', '% Usado']
            df_display_comp = df_display_comp.sort_values('Ano', ascending=False)
            
            st.dataframe(
                df_display_comp,
                hide_index=True,
                use_container_width=True,
                column_config={
                    'Orçado': st.column_config.NumberColumn(format="R$ %.2f"),
                    'Gasto': st.column_config.NumberColumn(format="R$ %.2f"),
                    'Diferença': st.column_config.NumberColumn(format="R$ %.2f"),
                    '% Usado': st.column_config.NumberColumn(format="%.1f%%")
                }
            )
            
            # Gráfico comparativo
            st.markdown("### Gráfico Comparativo")
            chart_data_comp = df_comparacao[['ano', 'valor', 'gasto_total']].copy()
            chart_data_comp.columns = ['Ano', 'Orçado', 'Gasto Real']
            chart_data_comp = chart_data_comp.set_index('Ano')
            st.bar_chart(chart_data_comp)
