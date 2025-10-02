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

# Importar as funções show de cada página
from pages import home, alerts, ficha, consulta_ca, ai_analysis, analytics, admin

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
            st.Page(home.show, title="Controle de Estoque", icon="🏠"),
            st.Page(alerts.show, title="Alertas de Troca", icon="🚨"),
        ]
    
    # Seção Gestão - Apenas Editores e Admins
    if can_edit():
        pages["📝 Gestão de EPIs"] = [
            st.Page(ficha.show, title="Gerar Ficha de EPI", icon="📄"),
            st.Page(consulta_ca.show, title="Consultar CA", icon="🔎"),
        ]
    
    # Seção Administração - Apenas Admins
    if is_admin():
        pages["⚙️ Administração"] = [
            st.Page(ai_analysis.show, title="Análise por IA", icon="🤖"),
            st.Page(analytics.show, title="Análise de Utilização", icon="📊"),
            st.Page(admin.show, title="Painel Administrativo", icon="⚙️"),
        ]
    
    # Criar navegação
    if pages:
        pg = st.navigation(pages, position="sidebar")
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
