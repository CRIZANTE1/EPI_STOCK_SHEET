import streamlit as st
import pandas as pd
import pygsheets
import os
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_sheet():
    try:
        logging.info("Tentando conectar ao Google Sheets...")

        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            # Carrega as credenciais do secrets.toml
            service_account_info = dict(st.secrets["connections"]["gsheets"])
            spreadsheet_url = service_account_info.pop("spreadsheet")
            
            # Autoriza com pygsheets usando o dicionário
            credentials = pygsheets.authorize(service_account_json=service_account_info)
        else:
            # Fallback local
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'cred.json')
            credentials = pygsheets.authorize(service_file=credentials_path)
            spreadsheet_url = "https://docs.google.com/spreadsheets/d/1r0nZdGCgVp_6Ti8MaHFBbtKSaK-EOezxLjSzl9pKmdc/edit#gid=0"

        logging.info("Conexão ao Google Sheets bem sucedida.")
        return credentials, spreadsheet_url

    except Exception as e:
        logging.error(f"Erro durante a autorização do Google Sheets: {e}")
        st.error(f"Erro durante a autorização do Google Sheets: {e}")
        return None, None


