import streamlit as st
import pandas as pd
import pygsheets
import os
import logging
import random
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_sheet():
    try:
        logging.info("Tentando conectar ao Google Sheets...")
        
        # Verifica se está rodando no Streamlit Cloud
        if 'gcp_service_account' in st.secrets:
            credentials = pygsheets.authorize(service_account_env_var='gcp_service_account')
            my_archive_google_sheets = st.secrets.get('GOOGLE_SHEETS_URL', '')
        else:
            # Fallback para desenvolvimento local
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'cred.json')
            credentials = pygsheets.authorize(service_file=credentials_path)
            my_archive_google_sheets = "https://docs.google.com/spreadsheets/d/1r0nZdGCgVp_6Ti8MaHFBbtKSaK-EOezxLjSzl9pKmdc/edit?gid=0#gid=0"
        
        if not my_archive_google_sheets:
            raise ValueError("URL do Google Sheets não configurada")
            
        logging.info("Conexão ao Google Sheets bem sucedida.")
        return credentials, my_archive_google_sheets
    
    except Exception as e:
        logging.error(f"Erro durante a autorização do Google Sheets: {e}")
        st.error(f"Erro durante a autorização do Google Sheets: {e}")
        return None, None

