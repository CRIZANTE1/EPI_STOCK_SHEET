import streamlit as st
from Front.pageone import configurar_pagina
from auth import (
    show_login_page,
    show_user_header,
    show_logout_button,
    is_admin,
    can_edit,
    can_view
)

# Importar as funções das páginas
from pages.home import page_home
from pages.alerts import page_alerts
from pages.ficha import page_ficha
from pages.consulta_ca import page_consulta_ca
from pages.ai_analysis import page_ai_analysis
from pages.analytics import page_analytics
from pages.admin import page_admin

def main():
    """Função principal do aplicativo"""
    configurar_pagina()
    
    # Verificar login
    if not show_login_page():
        return

    # Mostrar informações do usuário
    show_user_header()
    
    # Construir navegação baseada em permissões
    pages = {}
    
    # Seção Principal - Todos usuários autenticados
    if can_view():
        pages["📋 Principal"] = [
            st.Page(page_home, title="Controle de Estoque", icon="🏠", url_path="home"),
            st.Page(page_alerts, title="Alertas de Troca", icon="🚨", url_path="alerts"),
        ]
    
    # Seção Gestão - Apenas Editores e Admins
    if can_edit():
        pages["📝 Gestão de EPIs"] = [
            st.Page(page_ficha, title="Gerar Ficha de EPI", icon="📄", url_path="ficha"),
            st.Page(page_consulta_ca, title="Consultar CA", icon="🔎", url_path="consulta-ca"),
        ]
    
    # Seção Administração - Apenas Admins
    if is_admin():
        pages["⚙️ Administração"] = [
            st.Page(page_ai_analysis, title="Análise por IA", icon="🤖", url_path="ai-analysis"),
            st.Page(page_analytics, title="Análise de Utilização", icon="📊", url_path="analytics"),
            st.Page(page_admin, title="Painel Administrativo", icon="⚙️", url_path="admin"),
        ]
    
    # Criar navegação
    if pages:
        pg = st.navigation(pages, position="top")
        pg.run()
    else:
        st.error("Nenhuma página disponível para o seu nível de permissão.")
    
    # Botão de logout no sidebar
    with st.sidebar:
        st.markdown("---")
        show_logout_button()
    
    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.caption('Copyright 2024, Cristian Ferreira Carlos')
    st.sidebar.caption('[LinkedIn](https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/)')

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro inesperado no sistema: {str(e)}")
        import logging
        logging.exception("Erro no sistema")
        st.stop()
