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
            
            # Verificar se o arquivo de banco de dados existe
            users_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users_db.json')
            
            if not os.path.exists(users_db_path):
                st.warning("Banco de dados de usuários não encontrado!")
                
                # Criar banco de dados de exemplo
                if st.button("Criar Banco de Dados de Usuários"):
                    try:
                        # Criar diretório de dados se não existir
                        data_dir = os.path.dirname(users_db_path)
                        os.makedirs(data_dir, exist_ok=True)
                        
                        # Criar banco de dados com usuário admin
                        admin_password = "admin"  # Senha padrão para o admin
                        hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        users_db = {
                            "admin": {
                                "name": "Administrador",
                                "email": "admin@example.com",
                                "role": "admin",
                                "password": hashed_password,
                                "created_at": datetime.now().isoformat()
                            }
                        }
                        
                        with open(users_db_path, 'w') as file:
                            json.dump(users_db, file, indent=4)
                        
                        st.success("Banco de dados de usuários criado com sucesso!")
                        st.info("Usuário padrão: admin / Senha: admin")
                    except Exception as e:
                        st.error(f"Erro ao criar banco de dados: {str(e)}")
                return
                
            # Carregar dados de usuários
            try:
                with open(users_db_path, 'r') as file:
                    users_db = json.load(file)
                
                # Exibir lista de usuários
                st.write(f"Total de usuários: {len(users_db)}")
                
                # Tabela de usuários
                user_data = []
                for username, user_info in users_db.items():
                    user_data.append({
                        "Usuário": username,
                        "Nome": user_info.get("name", ""),
                        "Email": user_info.get("email", ""),
                        "Função": user_info.get("role", "usuário"),
                        "Criado em": user_info.get("created_at", "")
                    })
                
                if user_data:
                    st.dataframe(pd.DataFrame(user_data))
                else:
                    st.info("Nenhum usuário encontrado.")
                
                # Seção para adicionar novo usuário
                with st.expander("Adicionar Novo Usuário"):
                    with st.form("form_novo_usuario"):
                        novo_username = st.text_input("Nome de Usuário")
                        novo_nome = st.text_input("Nome Completo")
                        novo_email = st.text_input("Email")
                        nova_role = st.selectbox("Função", ["usuário", "admin"])
                        nova_senha = st.text_input("Senha", type="password")
                        confirmar_senha = st.text_input("Confirmar Senha", type="password")
                        
                        submit_button = st.form_submit_button("Adicionar Usuário")
                        
                        if submit_button:
                            if not novo_username or not novo_nome or not novo_email or not nova_senha or not confirmar_senha:
                                st.error("Todos os campos são obrigatórios!")
                            elif nova_senha != confirmar_senha:
                                st.error("Senha e confirmação não correspondem!")
                            elif novo_username in users_db:
                                st.error("Nome de usuário já existe!")
                            else:
                                # Adicionar novo usuário
                                hashed_password = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                
                                users_db[novo_username] = {
                                    "name": novo_nome,
                                    "email": novo_email,
                                    "role": nova_role,
                                    "password": hashed_password,
                                    "created_at": datetime.now().isoformat()
                                }
                                
                                # Salvar alterações
                                with open(users_db_path, 'w') as file:
                                    json.dump(users_db, file, indent=4)
                                
                                st.success(f"Usuário '{novo_username}' adicionado com sucesso!")
                                st.rerun()  # Recarregar para atualizar a lista
                
                # Seção para remover usuário
                with st.expander("Remover Usuário"):
                    usuario_para_remover = st.selectbox("Selecione o usuário para remover", list(users_db.keys()))
                    
                    if st.button("Remover Usuário"):
                        if usuario_para_remover in users_db:
                            # Não permitir remover o último admin
                            admins = [u for u, info in users_db.items() if info.get("role") == "admin"]
                            if len(admins) <= 1 and usuario_para_remover in admins:
                                st.error("Não é possível remover o último administrador do sistema!")
                            else:
                                # Remover usuário
                                del users_db[usuario_para_remover]
                                
                                # Salvar alterações
                                with open(users_db_path, 'w') as file:
                                    json.dump(users_db, file, indent=4)
                                
                                st.success(f"Usuário '{usuario_para_remover}' removido com sucesso!")
                                st.rerun()  # Recarregar para atualizar a lista
                
            except Exception as e:
                st.error(f"Erro ao carregar dados de usuários: {str(e)}")
    
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