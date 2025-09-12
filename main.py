import streamlit as st
from Front.pageone import front_page, configurar_pagina
from Front.admin_page import admin_page
from Front.ai_recommendations_page import ai_recommendations_page
from Front.generate_ficha_page import generate_ficha_page
from Front.alerts_page import alerts_page
from Front.analytics_page import analytics_page  
from Front.ca_lookup_page import ca_lookup_page 
from Front.history_page import show_history_page

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
    
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 'principal'

    if not show_login_page():
        return

    show_user_header()
    show_logout_button()
    
    with st.sidebar:
        st.markdown("### Menu de Navegação")

        # -- Acesso Geral 
        if can_view():
            if st.button("📋 Página Principal", use_container_width=True):
                st.session_state.pagina_atual = 'principal'
            
            if st.button("🚨 Alertas de Troca", use_container_width=True):
                st.session_state.pagina_atual = 'alertas'

        # -- Acesso de Edição 
        if can_edit():
            if st.button("📄 Gerar Ficha de EPI", use_container_width=True):
                st.session_state.pagina_atual = 'gerar_ficha'

            if st.button("📜 Histórico de Emissões", use_container_width=True):
                st.session_state.pagina_atual = 'historico'

            if st.button("🔎 Consultar CA", use_container_width=True):
                st.session_state.pagina_atual = 'consulta_ca'

        # -- Seção Exclusiva de Administração 
        if is_admin():
            st.markdown("---")
            st.subheader("Análise e Gestão")
            
            if st.button("💡 Análise por IA", use_container_width=True):
                st.session_state.pagina_atual = 'ai_recommendations'

            if st.button("📊 Análise de Utilização", use_container_width=True):
                st.session_state.pagina_atual = 'analytics'

            if st.button("⚙️ Painel Administrativo", use_container_width=True):
                st.session_state.pagina_atual = 'admin'
                
    # ---- ROTEAMENTO DE PÁGINAS COM PERMISSÕES CONSISTENTES ----
    pagina = st.session_state.get('pagina_atual', 'principal')

    # A ordem dos 'elif' agora corresponde à hierarquia de permissões
    if pagina == 'principal' and can_view():
        front_page()
    elif pagina == 'alertas' and can_view():
        alerts_page()
    elif pagina == 'gerar_ficha' and can_edit():
        generate_ficha_page()
    elif pagina == 'historico' and can_edit():
        show_history_page()
    elif pagina == 'consulta_ca' and can_edit():
        ca_lookup_page()
    elif pagina == 'ai_recommendations' and is_admin(): 
        ai_recommendations_page()
    elif pagina == 'analytics' and is_admin(): 
        analytics_page()
    elif pagina == 'admin' and is_admin(): 
        admin_page()
    else:
        # Se um usuário sem permissão tentar acessar uma página, ele é redirecionado
        st.session_state.pagina_atual = 'principal'
        st.warning("Você não tem permissão para acessar esta página ou a página não existe.")
        st.rerun()

if __name__ == "__main__":
    try:
        main()
        st.caption('Copyright 2024, Cristian Ferreira Carlos, Todos os direitos reservados.')
        st.caption('https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/')
    except Exception as e:
        st.error(f"Erro inesperado no sistema: {str(e)}")
        st.stop()






