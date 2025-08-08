import sys
import json
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import pandas as pd

# Adicionado para interagir com a planilha
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
                # Garante que a coluna 'ca' seja string para a comparação
                df['ca'] = df['ca'].astype(str)
                return df
        except Exception as e:
            logging.error(f"Erro ao carregar banco de dados de CAs: {e}")
        return pd.DataFrame(columns=['ca', 'situacao', 'validade', 'nome_equipamento', 'descricao_equipamento', 'ultima_consulta'])

    def _save_ca_to_sheet(self, ca_data: dict):
        """Salva ou atualiza um registro de CA na planilha."""
        ca_number = str(ca_data['ca'])
        ca_data['ultima_consulta'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # Converte o dicionário para a ordem correta das colunas
        new_row_values = [
            ca_data.get('ca', ''),
            ca_data.get('situacao', ''),
            ca_data.get('validade', ''),
            ca_data.get('nome_equipamento', ''),
            ca_data.get('descricao_equipamento', ''),
            ca_data.get('ultima_consulta', '')
        ]


        try:
            archive = self.sheet_ops.credentials.open_by_url(self.sheet_ops.my_archive_google_sheets)
            aba = archive.worksheet_by_title('db_ca')
            aba.append_table(values=[new_row_values])
            logging.info(f"CA {ca_number} salvo na planilha com sucesso.")
        except Exception as e:
            logging.error(f"Falha ao salvar CA {ca_number} na planilha: {e}")

    def query_ca(self, ca_number: str) -> dict:
        """
        Consulta um CA. Primeiro verifica o cache na planilha, depois o site do governo.
        """
        ca_number = str(ca_number).strip()
        
        if not self.db_ca_df.empty:
            cached_result = self.db_ca_df[self.db_ca_df['ca'] == ca_number]
            if not cached_result.empty:
                latest_entry = cached_result.iloc[-1].to_dict()
                logging.info(f"CA {ca_number} encontrado no cache da planilha.")
                return latest_entry

        logging.info(f"CA {ca_number} não encontrado no cache. Buscando no site do governo...")
        result = self._scrape_ca_website(ca_number)

        # 3. Se a busca no site foi bem-sucedida, salva no cache
        if "erro" not in result:
            self._save_ca_to_sheet(result)
        
        return result

    def _scrape_ca_website(self, ca_number: str, headless=True, timeout=20) -> dict:
        """Lógica de web scraping (sua implementação original)."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        try:
            service = Service(ChromeDriverManager().install())
            with webdriver.Chrome(service=service, options=options) as driver:
                wait = WebDriverWait(driver, timeout)
                logging.info(f"Iniciando consulta web para o CA: {ca_number}")
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
                logging.info(f"Consulta web para o CA {ca_number} concluída com sucesso.")
                return dados
                
        except TimeoutException:
            logging.error(f"CA {ca_number} não encontrado no site do governo ou o site falhou.")
            return {"erro": f"CA {ca_number} não encontrado ou o site de consulta está indisponível."}
        except Exception as e:
            logging.error(f"Erro inesperado durante o scraping do CA {ca_number}: {e}")
            return {"erro": f"Um erro inesperado ocorreu: {e}"}
