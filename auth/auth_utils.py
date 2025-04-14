import streamlit as st
import os
import json
import bcrypt

def is_oidc_available():
    """Verifica se o login OIDC está configurado e disponível"""
    try:
        return hasattr(st.experimental_user, 'is_logged_in')
    except Exception:
        return False

def is_user_logged_in():
    """Verifica se o usuário está logado"""
    try:
        return st.experimental_user.is_logged_in
    except Exception:
        return False

def get_user_display_name():
    """Retorna o nome de exibição do usuário"""
    try:
        if hasattr(st.experimental_user, 'name'):
            return st.experimental_user.name
        elif hasattr(st.experimental_user, 'email'):
            return st.experimental_user.email
        return "Usuário"
    except Exception:
        return "Usuário"

def get_user_role():
    """Retorna o papel do usuário (admin ou usuário normal)"""
    try:
        if hasattr(st.experimental_user, 'role'):
            return st.experimental_user.role
        return "user"
    except Exception:
        return "user"

def is_admin():
    """Verifica se o usuário atual é um administrador"""
    try:
        # Verifica se o usuário está logado e tem nome
        if hasattr(st.experimental_user, 'name'):
            user_name = st.experimental_user.name
            # Verifica se o nome do usuário é "Cristian ferreira"
            if user_name == "Cristian ferreira":
                return True
        return False
    except Exception as e:
        st.error(f"Erro na verificação de admin: {str(e)}")
        return False

def alterar_senha_db(usuario, senha_atual, nova_senha):
    """Altera a senha do usuário no banco de dados"""
    try:
        # Caminho para o arquivo de banco de dados
        users_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users_db.json')
        
        # Verificar se o arquivo existe
        if not os.path.exists(users_db_path):
            st.error("Arquivo de banco de dados de usuários não encontrado!")
            return False
            
        # Carregar dados dos usuários
        with open(users_db_path, 'r') as file:
            users_db = json.load(file)
        
        # Verificar se o usuário existe
        if usuario not in users_db:
            st.error("Usuário não encontrado no banco de dados!")
            return False
            
        # Verificar senha atual
        stored_hash = users_db[usuario]["password"]
        if not bcrypt.checkpw(senha_atual.encode('utf-8'), stored_hash.encode('utf-8')):
            st.error("Senha atual incorreta!")
            return False
            
        # Gerar hash da nova senha
        hashed_new_password = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Atualizar senha no banco de dados
        users_db[usuario]["password"] = hashed_new_password
        
        # Salvar alterações
        with open(users_db_path, 'w') as file:
            json.dump(users_db, file, indent=4)
            
        st.success("Senha alterada com sucesso!")
        return True
        
    except Exception as e:
        st.error(f"Erro ao alterar senha: {str(e)}")
        return False 