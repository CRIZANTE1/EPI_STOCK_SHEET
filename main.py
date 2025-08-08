import streamlit as st
from Front.pageone import front_page, configurar_pagina
from Front.admin_page import admin_page
from Front.ai_recommendations_page import ai_recommendations_page
from Front.generate_ficha_page import generate_ficha_page
from Front.alerts_page import alerts_page

from auth import (
    show_login_page,
    show_user_header,
    show_logout_button,
    is_admin,
    can_edit, 
    can_view  
)

def main():
    """Função principal do aplicativo"""
    configurar_pagina()
    
    # Define a página padrão se não estiver definida
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 'principal'

    # Se o usuário não estiver logado, mostra a página de login e para a execução.
    if not show_login_page():
        return

    # Se logado, mostra o cabeçalho do usuário e o botão de logout.
    show_user_header()
    show_logout_button()
    
    # ---- MENU DE NAVEGAÇÃO REESTRUTURADO ----
    with st.sidebar:
        st.markdown("### Menu de Navegação")

  
        if can_view():
            if st.button("📋 Página Principal", use_container_width=True):
                st.session_state.pagina_atual = 'principal'
            
            if st.button("🚨 Alertas de Troca", use_container_width=True):
                st.session_state.pagina_atual = 'alertas'

        # Páginas que exigem permissão de edição (role 'editor' ou 'admin')
        if can_edit():
            if st.button("💡 Análise e Recomendações", use_container_width=True):
                st.session_state.pagina_atual = 'ai_recommendations'
            
            if st.button("📄 Gerar Ficha de EPI", use_container_width=True):
                st.session_state.pagina_atual = 'gerar_ficha'

        # Seção exclusiva para administradores (role 'admin')
        if is_admin():
            st.markdown("---")
            st.subheader("Administração")
            if st.button("⚙️ Painel Administrativo", use_container_width=True):
                st.session_state.pagina_atual = 'admin'
    
    pagina = st.session_state.get('pagina_atual', 'principal')

    if pagina == 'principal' and can_view():
        front_page()
    elif pagina == 'alertas' and can_view():
        alerts_page()
    elif pagina == 'ai_recommendations' and can_edit():
        ai_recommendations_page()
    elif pagina == 'gerar_ficha' and can_edit():
        generate_ficha_page()
    elif pagina == 'admin' and is_admin():
        admin_page()
    else:
        st.session_state.pagina_atual = 'principal'
        st.warning("Você não tem permissão para acessar esta página ou a página não existe.")
        st.rerun() # O rerun força o redirecionamento para a página principal

if __name__ == "__main__":
    try:
        main()
        st.caption('Copyright 2024, Cristian Ferreira Carlos, Todos os direitos reservados.')
        st.caption('https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/')
    except Exception as e:
        st.error(f"Erro inesperado no sistema: {str(e)}")
        st.stop()
        

