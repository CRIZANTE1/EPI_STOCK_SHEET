import streamlit as st
import pandas as pd
import os
import json
import bcrypt
from datetime import datetime
from auth import is_admin

def alterar_senha():
    st.subheader("Alterar Senha")
    
    # Verificar se está usando OIDC ou fallback
    is_oidc = hasattr(st.experimental_user, 'email')
    
    if is_oidc:
        st.info("""
        ### Alteração de Senha no Sistema OIDC
        
        Você está usando o sistema de login OIDC. Para alterar sua senha:
        
        1. Acesse a página do seu provedor de identidade (Google, Microsoft, etc.)
        2. Use a opção de gerenciamento de conta do provedor
        3. Localize a opção de alteração de senha nas configurações de segurança
        """)
        return
    
    # Mostramos a interface de alteração de senha do banco de dados
    usuario = st.experimental_user.email if hasattr(st.experimental_user, 'email') else ""
    
    with st.form("form_alterar_senha"):
        senha_atual = st.text_input("Senha Atual", type="password")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
        
        submit_button = st.form_submit_button("Confirmar Alteração")
        
        if submit_button:
            if not senha_atual or not nova_senha or not confirmar_senha:
                st.error("Todos os campos são obrigatórios!")
                return
                
            if nova_senha != confirmar_senha:
                st.error("Nova senha e confirmação não correspondem!")
                return
                
            # Importar função correta para alterar senha
            from main import alterar_senha_db
            
            # Chamar a função de alteração de senha do módulo principal
            alterar_senha_db(usuario, senha_atual, nova_senha)

def admin_page():
    # Verificar se o usuário é administrador
    if not is_admin():
        st.error("Acesso negado. Esta página é restrita a administradores.")
        # Botão para voltar à página principal
        if st.button("Voltar para Página Principal"):
            st.session_state.pagina_atual = 'principal'
            st.rerun()
        return
        
    st.title("Painel de Administração")
    
    # Menu lateral de navegação administrativa
    with st.sidebar:
        st.subheader("Menu Administrativo")
        opcao_admin = st.radio(
            "Selecione a função:",
            ["Gerenciar Senhas", "Configurações do Sistema", "Voltar para Principal"]
        )
        
        # Botão de voltar para página principal
        if opcao_admin == "Voltar para Principal":
            st.session_state.pagina_atual = 'principal'
            st.rerun()
    
    # Conteúdo principal baseado na seleção do menu
    if opcao_admin == "Gerenciar Senhas":
        st.header("Gerenciamento de Senhas")
        
        # Selecionar usuário ou exibir informações gerais
        opcao_senha = st.radio(
            "Opções:",
            ["Minha Senha", "Gerenciar Usuários"]
        )
        
        if opcao_senha == "Minha Senha":
            alterar_senha()
        else:
            st.subheader("Gerenciamento de Usuários")

            from End.Operations import SheetOperations
            sheet_operations = SheetOperations()
            users_data = sheet_operations.carregar_dados_aba('users')

            if users_data:
                # Assuming the first row is the header
                header = users_data[0]
                user_data = [dict(zip(header, row)) for row in users_data[1:]]

                if user_data:
                    st.dataframe(user_data)
                else:
                    st.info("Nenhum usuário encontrado.")
            else:
                st.error("Não foi possível carregar os dados da aba 'users'.")

            # Seção para adicionar novo usuário
            with st.expander("Adicionar Novo Usuário"):
                with st.form("form_novo_usuario"):
                    novo_nome = st.text_input("Nome Completo")
                    novo_email = st.text_input("Email")
                    nova_role = st.selectbox("Função", ["usuário", "admin"])

                    submit_button = st.form_submit_button("Adicionar Usuário")

                    if submit_button:
                        if not novo_nome or not novo_email:
                            st.error("Todos os campos são obrigatórios!")
                        else:
                            # Adicionar novo usuário
                            user_data = [novo_nome, novo_email, nova_role]
                            sheet_operations.add_user(user_data)
                            st.rerun()  # Recarregar para atualizar a lista

            # Seção para remover usuário
            with st.expander("Remover Usuário"):
                # Get the list of usernames from the 'users' sheet
                users_data = sheet_operations.carregar_dados_aba('users')
                if users_data:
                    header = users_data[0]
                    try:
                        name_index = header.index('Nome Completo')  # Assuming 'Nome Completo' column exists
                    except ValueError:
                        st.error("A coluna 'Nome Completo' não foi encontrada na aba 'users'.")
                        name_index = None

                    if name_index is not None:
                        user_names = [row[name_index] for row in users_data[1:]]
                        usuario_para_remover = st.selectbox("Selecione o usuário para remover", user_names)

                        if st.button("Remover Usuário"):
                            sheet_operations.remove_user(usuario_para_remover)
                            st.rerun()  # Recarregar para atualizar a lista
                    else:
                        st.error("Não foi possível carregar a lista de usuários.")
                else:
                    st.error("Não foi possível carregar os dados da aba 'users'.")

    elif opcao_admin == "Configurações do Sistema":
        st.header("Configurações do Sistema")
        
        # Exibir informações de configuração do sistema
        st.subheader("Informações de Login OIDC")
        
        # Informações sobre o provedor configurado
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
        
        # Geração de cookie_secret
        st.subheader("Gerar Novo Cookie Secret")
        if st.button("Gerar Novo Cookie Secret"):
            try:
                # Importar função de geração de cookie_secret
                from gerar_cookie_secret import gerar_cookie_secret
                
                # Gerar novo cookie_secret
                novo_cookie_secret = gerar_cookie_secret()
                
                st.success("Novo cookie_secret gerado com sucesso!")
                st.code(f"cookie_secret = \"{novo_cookie_secret}\"")
                st.info("Copie este valor para o arquivo .streamlit/secrets.toml")
            except Exception as e:
                st.error(f"Erro ao gerar cookie_secret: {str(e)}")
                
        # Status do sistema
        st.subheader("Status do Sistema")
        st.json({
            "sistema": "Controle de Estoque de EPIs",
            "versão": "1.0.0",
            "modo_login": "OIDC (OpenID Connect)",
            "status": "Ativo"
        })
