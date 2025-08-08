import streamlit as st
from Utils.consultaca import CAQuery
from auth import can_edit # Apenas editores e admins podem consultar

def ca_lookup_page():
    st.title("🔎 Consulta de Certificado de Aprovação (CA)")

    if not can_edit():
        st.error("Acesso negado.")
        st.info("Apenas usuários com permissão de edição podem acessar esta funcionalidade.")
        return

    # Inicializa o consultor em session_state para evitar recarregar a planilha a cada ação
    if 'ca_consultor' not in st.session_state:
        st.session_state.ca_consultor = CAQuery()
    
    ca_consultor = st.session_state.ca_consultor

    st.markdown("Digite o número do CA para consultar sua validade e detalhes. O sistema primeiro busca em nosso banco de dados local e, se não encontrar, consulta o site do governo em tempo real.")

    ca_number_input = st.text_input("Número do CA:", placeholder="Ex: 28011")

    if st.button("Consultar CA"):
        if not ca_number_input.isdigit():
            st.error("Por favor, insira apenas números para o CA.")
        else:
            with st.spinner(f"Consultando CA {ca_number_input}... Isso pode levar alguns segundos."):
                result = ca_consultor.query_ca(ca_number_input)

            st.markdown("---")
            if "erro" in result:
                st.error(f"**Falha na Consulta:** {result['erro']}")
            else:
                st.success(f"**Resultado para o CA {result['ca']}**")
                
                # Exibe o status com cor
                status = result.get('situacao', 'N/A')
                if "VÁLIDO" in status.upper():
                    st.success(f"**Situação:** {status}")
                else:
                    st.error(f"**Situação:** {status}")
                
                st.info(f"**Validade:** {result.get('validade', 'N/A')}")
                st.subheader(result.get('nome_equipamento', 'N/A'))
                with st.expander("Ver descrição completa"):
                    st.write(result.get('descricao_equipamento', 'N/A'))
                
                # Informa se o dado veio do cache
                if 'ultima_consulta' in result:
                    st.caption(f"Este dado foi obtido do nosso banco de dados em {result['ultima_consulta']}.")
