import sys
import json
import time
import logging
from datetime import datetime, timedelta 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd

from End.Operations import SheetOperations

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CAQuery:
    BASE_URL = "https://caepi.mte.gov.br/internet/consultacainternet.aspx"

    def __init__(self):
        self.sheet_ops = SheetOperations()
        self.db_ca_df = self._load_ca_database()

    def _load_ca_database(self):
        """Carrega a aba 'db_ca' em um DataFrame do Pandas."""
        try:
            data = self.sheet_ops.carregar_dados_aba('db_ca')
            if data and len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                df['ca'] = df['ca'].astype(str)
                # Converte a data da última consulta para o formato datetime
                df['ultima_consulta_dt'] = pd.to_datetime(df['ultima_consulta'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
                return df
        except Exception as e:
            logging.error(f"Erro ao carregar banco de dados de CAs: {e}")
        return pd.DataFrame()

    def _save_ca_to_sheet(self, ca_data: dict):
        """Salva um novo registro de CA na planilha."""
        ca_data['ultima_consulta'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        new_row_values = [
            ca_data.get('ca', ''),
            ca_data.get('situacao', ''),
            ca_data.get('validade', ''),
            ca_data.get('nome_equipamento', ''),
            ca_data.get('descricao_equipamento', ''),
            ca_data.get('ultima_consulta', '')
        ]
        try:
            # Esta lógica adiciona uma nova linha. O sistema sempre pegará a mais recente.
            archive = self.sheet_ops.credentials.open_by_url(self.sheet_ops.my_archive_google_sheets)
            aba = archive.worksheet_by_title('db_ca')
            aba.append_table(values=[new_row_values], overwrite=False) # Adiciona sem sobrescrever
            logging.info(f"CA {ca_data['ca']} salvo na planilha com sucesso.")
        except Exception as e:
            logging.error(f"Falha ao salvar CA {ca_data['ca']} na planilha: {e}")

    def query_ca(self, ca_number: str, cache_expiry_days: int = 30) -> dict:
        """
        Consulta um CA com lógica de expiração de cache.
        """
        ca_number = str(ca_number).strip()
        
        # 1. Verifica no cache primeiro
        if not self.db_ca_df.empty:
            cached_result = self.db_ca_df[self.db_ca_df['ca'] == ca_number]
            if not cached_result.empty:
                latest_entry = cached_result.sort_values(by='ultima_consulta_dt', ascending=False).iloc[0]
                
                # ---- LÓGICA DE EXPIRAÇÃO DO CACHE ----
                last_query_date = latest_entry['ultima_consulta_dt']
                
                # Verifica se a data é válida e se o cache ainda não expirou
                if pd.notna(last_query_date) and (datetime.now() - last_query_date) < timedelta(days=cache_expiry_days):
                    logging.info(f"CA {ca_number} encontrado no cache (ainda válido).")
                    return latest_entry.to_dict()
                else:
                    logging.info(f"CA {ca_number} encontrado no cache, mas está expirado. Reconsultando...")
        
        # 2. Se não encontrou no cache ou o cache expirou, busca no site
        logging.info(f"CA {ca_number} não encontrado ou expirado. Buscando no site do governo...")
        result = self._scrape_ca_website(ca_number)

        # 3. Se a busca no site foi bem-sucedida, salva o novo resultado na planilha
        if "erro" not in result:
            self._save_ca_to_sheet(result)
        
        return result

    def _scrape_ca_website(self, ca_number: str, timeout=30) -> dict:
        """Lógica de web scraping robusta para ambientes na nuvem."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        
        try:
            with webdriver.Chrome(options=options) as driver:
                wait = WebDriverWait(driver, timeout)
                driver.get(self.BASE_URL)
                
                wait.until(EC.presence_of_element_located((By.ID, 'txtNumeroCA'))).send_keys(ca_number)
                wait.until(EC.element_to_be_clickable((By.ID, 'btnConsultar'))).click()
                
                detalhar_xpath = '//*[@id="PlaceHolderConteudo_grdListaResultado_btnDetalhar_0"]'
                botao_detalhar = wait.until(EC.visibility_of_element_located((By.XPATH, detalhar_xpath)))
                time.sleep(1)
                driver.execute_script("arguments[0].click();", botao_detalhar)
                           
                wait.until(EC.presence_of_element_located((By.ID, "PlaceHolderConteudo_TDSituacao")))
                
                dados = {
                    "ca": ca_number,
                    "situacao": driver.find_element(By.ID, "PlaceHolderConteudo_TDSituacao").text.replace('Situação:', '').strip(),
                    "validade": driver.find_element(By.ID, "PlaceHolderConteudo_TDDTValidade").text.replace('Validade:', '').strip(),
                    "nome_equipamento": driver.find_element(By.ID, "PlaceHolderConteudo_lblNOEquipamento").text.strip(),
                    "descricao_equipamento": driver.find_element(By.ID, "PlaceHolderConteudo_TDEquipamentoDSEquipamentoTexto").text.strip()
                }
                return dados
                
        except TimeoutException:
            return {"erro": f"CA {ca_number} não encontrado ou o site de consulta está indisponível."}
        except Exception as e:
            return {"erro": f"Um erro inesperado ocorreu durante a consulta web: {e}"}
