import streamlit as st
import pandas as pd
from End.Operations import SheetOperations

def is_oidc_available():
    """Verifica se o login OIDC está configurado e disponível"""
    try:
        return hasattr(st.user, 'is_logged_in')
    except Exception:
        return False

def is_user_logged_in():
    """Verifica se o usuário está logado"""
    try:
        return st.user.is_logged_in
    except Exception:
        return False

def get_user_display_name():
    """Retorna o nome de exibição do usuário"""
    try:
        if hasattr(st.user, 'name'):
            return st.user.name
        elif hasattr(st.user, 'email'):
            return st.user.email
        return "Usuário"
    except Exception:
        return "Usuário"


def get_user_email() -> str | None:
    """Retorna o e-mail do usuário logado, normalizado para minúsculas."""
    try:
        if hasattr(st.user, 'email') and st.user.email:
            return st.user.email.lower().strip()
        return None
    except Exception:
        return None

@st.cache_data(ttl=300) # Cache de 5 minutos para a tabela de permissões
def get_user_permissions_df() -> pd.DataFrame:
    """
    Carrega a lista de usuários e suas permissões da planilha 'users'.
    Retorna um DataFrame com as colunas 'email' e 'role'.
    """
    try:
        sheet_operations = SheetOperations()
        users_data = sheet_operations.carregar_dados_aba('users')
        
        if not users_data or len(users_data) < 2:
            st.warning("Aba de usuários ('users') não encontrada ou vazia.")
            return pd.DataFrame(columns=['email', 'role'])
        
        permissions_df = pd.DataFrame(users_data[1:], columns=users_data[0])
        
        if 'email' not in permissions_df.columns or 'role' not in permissions_df.columns:
            st.error("A aba 'users' precisa conter as colunas 'email' e 'role'.")
            return pd.DataFrame(columns=['email', 'role'])
            
        # Normaliza os dados para evitar erros de digitação
        permissions_df['email'] = permissions_df['email'].str.lower().str.strip()
        permissions_df['role'] = permissions_df['role'].str.lower().str.strip()
            
        return permissions_df[['email', 'role']]

    except Exception as e:
        st.error(f"Erro ao carregar permissões de usuário: {e}")
        return pd.DataFrame(columns=['email', 'role'])

def get_user_role() -> str:
    """
    Retorna o papel (role) do usuário logado.
    O padrão para usuários não listados na planilha é 'viewer'.
    """
    user_email = get_user_email()
    if not user_email:
        return 'viewer' # Padrão para não logado ou sem e-mail

    permissions_df = get_user_permissions_df()
    if permissions_df.empty:
        return 'viewer'

    user_entry = permissions_df[permissions_df['email'] == user_email]
    
    if not user_entry.empty:
        return user_entry.iloc[0]['role']
    
    return 'viewer'

# --- FUNÇÕES DE VERIFICAÇÃO DE PERMISSÃO ---

def is_admin() -> bool:
    """Verifica se o usuário tem o papel de 'admin'."""
    return get_user_role() == 'admin'

def can_edit() -> bool:
    """Verifica se o usuário pode editar (admin ou editor)."""
    # Se você quiser que apenas admins editem, remova 'editor' desta lista.
    return get_user_role() in ['admin', 'editor']

def can_view() -> bool:
    """Verifica se o usuário pode visualizar (qualquer papel listado ou não)."""
    # Qualquer usuário logado pode visualizar.
    return is_user_logged_in()

