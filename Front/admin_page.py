import streamlit as st
import pandas as pd
import os
import json
import bcrypt
from datetime import datetime
from auth import is_admin

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
        ["Configurações do Sistema", "Voltar para Principal"]
    )

    if opcao_admin == "Voltar para Principal":
        st.session_state.pagina_atual = 'principal'
        st.rerun()
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
