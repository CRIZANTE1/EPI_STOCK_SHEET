import streamlit as st
import pandas as pd
import os
import json
import bcrypt
from datetime import datetime
from auth import is_admin
from Utils.budget_forecast import generate_budget_forecast
import io
from Utils.pdf_generator import create_forecast_pdf_from_report


def forecast_budget_page():
    st.header("Previsão Orçamentária Anual")
    st.write("Esta ferramenta utiliza IA para analisar o histórico de consumo e gerar uma previsão de gastos com EPIs para o próximo ano.")
    
    sheet_operations = SheetOperations()
    
    col1, col2 = st.columns(2)
    with col1:
        ano_base = st.number_input("Ano base para análise:", min_value=2020, max_value=2030, value=datetime.now().year)
    with col2:
        margem_seguranca = st.slider("Margem de segurança (%):", min_value=0, max_value=50, value=15, 
                                     help="Percentual adicional para cobrir imprevistos")
    
    if st.button("Gerar Previsão Orçamentária", type="primary"):
        with st.spinner("Analisando dados históricos e gerando previsão..."):
            resultado = generate_budget_forecast(sheet_operations, ano_base, margem_seguranca)
            
            if "erro" in resultado:
                st.error(resultado["erro"])
            else:
                st.success("✅ Previsão gerada com sucesso!")
                
                # Exibir resumo
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Previsto", f"R$ {resultado['total_previsto']:,.2f}")
                col2.metric("Com Margem de Segurança", f"R$ {resultado['total_com_margem']:,.2f}")
                col3.metric("Margem Aplicada", f"{margem_seguranca}%")
                
                # Exibir relatório completo
                st.markdown("---")
                st.markdown(resultado["relatorio_completo"])
                
                # Botão para download em PDF
                st.markdown("---")
                if st.button("📥 Baixar Relatório em PDF"):
                    pdf_buffer = create_forecast_pdf_from_report(resultado["relatorio_completo"])
                    st.download_button(
                        label="Clique aqui para baixar o PDF",
                        data=pdf_buffer,
                        file_name=f"Previsao_Orcamentaria_{ano_base + 1}.pdf",
                        mime="application/pdf"
                    )

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

