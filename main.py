import streamlit as st
from Front.pageone import front_page, configurar_pagina
from Front.admin_page import admin_page
from auth import (
    show_login_page,
    show_user_header,
    show_logout_button,
    is_admin
)

def main():
    """Função principal do aplicativo"""
    configurar_pagina()
    
    # Inicializar estado para controle de páginas
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 'principal'
    
    # Verificar login e mostrar página apropriada
    if not show_login_page():
        return
    
    # Usuário está logado
    show_user_header()
    show_logout_button()
    
    # Adicionar botão de administração se o client_secret for o correto
    if is_admin():
        with st.sidebar:
            st.markdown("---")
            st.subheader("Administração")
            if st.button("Acessar Painel Administrativo"):
                st.session_state.pagina_atual = 'admin'
                st.rerun()
    
    # Mostrar a página apropriada
    if st.session_state.pagina_atual == 'admin' and is_admin():
        admin_page()
    else:
        front_page()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro no sistema: {str(e)}")
        st.stop()
