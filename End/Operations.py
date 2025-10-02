import streamlit as st
import pandas as pd
import logging
import random
from API.conection import connect_sheet


class SheetOperations:
    
    def __init__(self):
        """
        O código define uma classe com métodos para conectar-se a um documento Google Sheets, carregar dados de
        uma planilha específica, adicionar novos dados com um ID único, editar dados existentes com base no ID
        e excluir dados com base no ID.
        """
        self.credentials, self.my_archive_google_sheets = connect_sheet()
        if not self.credentials or not self.my_archive_google_sheets:
            logging.error("Credenciais ou URL do Google Sheets inválidos.")

    def carregar_dados(self):
        return self.carregar_dados_aba('control_stock')
    
    def carregar_dados_funcionarios(self):
        """
        Carrega os dados dos funcionários da aba 'funcionarios' do Google Sheets.
        
        Returns:
            list: Lista com os dados dos funcionários, onde o primeiro item são os cabeçalhos
                 e os demais são os dados de cada funcionário.
        """
        return self.carregar_dados_aba('funcionarios')

    def carregar_dados_aba(self, aba_name):
        if not self.credentials or not self.my_archive_google_sheets:
            return None
        try:
            logging.info(f"Tentando ler dados da aba '{aba_name}'...")
            
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            
            if aba_name not in [sheet.title for sheet in archive.worksheets()]:
                logging.error(f"A aba '{aba_name}' não existe no Google Sheets.")
                st.error(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return None
            
            aba = archive.worksheet_by_title(aba_name)
            data = aba.get_all_values()
            
            logging.info(f"Dados da aba '{aba_name}' lidos com sucesso.")
            return data
        
        except Exception as e:
            logging.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            st.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            return None
        
        
    def adc_dados(self, new_data):
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            logging.info(f"Tentando adicionar dados: {new_data}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba_name = 'control_stock'
            if aba_name not in [sheet.title for sheet in archive.worksheets()]:
                logging.error(f"A aba '{aba_name}' não existe no Google Sheets.")
                st.error(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return
            aba = archive.worksheet_by_title(aba_name)

            # Esta parte do código está gerando um novo ID único para os dados a serem adicionados ao
            # Google Sheets. O ID é um número aleatório de 4 dígitos que não pode ser repetido.
            existing_ids = [row[0] for row in aba.get_all_values()[1:]]  #
            while True:
                new_id = random.randint(1000, 9999)
                if str(new_id) not in existing_ids:
                    break

            new_data.insert(0, new_id)  # Insere o novo ID no início da lista new_data
            aba.append_table(values=new_data)  # Adiciona a linha à tabela dinamicamente
            logging.info("Dados adicionados com sucesso.")
            st.success("Dados adicionados com sucesso!")
        except Exception as e:
            logging.error(f"Erro ao adicionar dados: {e}", exc_info=True)
            st.error(f"Erro ao adicionar dados: {e}")

    def editar_dados(self, id, updated_data):
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            logging.info(f"Tentando editar dados do ID {id}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('control_stock')
            data = aba.get_all_values()
            
            # Procurar a linha com o ID correspondente
            for i, row in enumerate(data):
                if row[0] == str(id):  # ID está na primeira coluna
                    # Atualizar a linha com os novos dados, mantendo o ID original
                    updated_row = [str(id)] + updated_data
                    aba.update_row(i + 1, updated_row)  # +1 porque as linhas começam em 1
                    logging.info("Dados editados com sucesso.")
                    return True
                    
            logging.error(f"ID {id} não encontrado.")
            return False
            
        except Exception as e:
            logging.error(f"Erro ao editar dados: {e}", exc_info=True)
            return False

    def excluir_dados(self, id):
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            logging.info(f"Tentando excluir dados do ID {id}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('control_stock')
            data = aba.get_all_values()
            
            # Procurar a linha com o ID correspondente
            for i, row in enumerate(data):
                if row[0] == str(id):  # ID está na primeira coluna
                    aba.delete_rows(i + 1)  # +1 porque as linhas começam em 1
                    logging.info("Dados excluídos com sucesso.")
                    return True
                    
            logging.error(f"ID {id} não encontrado.")
            return False
            
        except Exception as e:
            logging.error(f"Erro ao excluir dados: {e}", exc_info=True)
            return False
        
    def ensure_emission_history_sheet_exists(self):
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            sheet_title = 'emission_history'
            if sheet_title not in [sheet.title for sheet in archive.worksheets()]:
                aba = archive.add_worksheet(sheet_title, rows=1, cols=3)
                aba.update_row(1, ['employee_name', 'emission_date', 'emitter_name'])
                logging.info(f"Aba '{sheet_title}' criada com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao verificar/criar a aba 'emission_history': {e}", exc_info=True)

    def add_emission_history(self, employee_name, emitter_name):
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            self.ensure_emission_history_sheet_exists()
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('emission_history')
            emission_date = pd.to_datetime('today').strftime('%Y-%m-%d %H:%M:%S')
            new_row = [employee_name, emission_date, emitter_name]
            aba.append_table(values=new_row)
            logging.info(f"Histórico de emissão adicionado para {employee_name}.")
        except Exception as e:
            logging.error(f"Erro ao adicionar histórico de emissão: {e}", exc_info=True)

# Em implemação -----------------------------------------------------------------------------
    def add_user(self, user_data):
        
        """
        O código Python fornecido define métodos para adicionar e remover usuários de um documento Google Sheets,
        tratando erros e mensagens de log de acordo.

        :param user_data: O parâmetro `user_data` provavelmente contém informações sobre um usuário que você deseja
        adicionar a um documento Google Sheets. Essas informações podem incluir detalhes como o nome do usuário,
        e-mail, função ou quaisquer outros dados relevantes que você deseja armazenar na planilha 'users' dentro do
        Google Sheets especificado.
        :return: Tanto nos métodos `add_user` quanto `remove_user`, se as condições `if not
        self.credentials or not self.my_archive_google_sheets` forem atendidas, os métodos retornarão
        sem executar nenhuma ação adicional.
        """
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            logging.info(f"Tentando adicionar usuário: {user_data}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba_name = 'users'
            if aba_name not in [sheet.title for sheet in archive.worksheets()]:
                logging.error(f"A aba '{aba_name}' não existe no Google Sheets.")
                st.error(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return
            aba = archive.worksheet_by_title(aba_name)
            aba.append_table(values=[user_data])
            logging.info("Usuário adicionado com sucesso.")
            st.success("Usuário adicionado com sucesso!")
        except Exception as e:
            logging.error(f"Erro ao adicionar usuário: {e}", exc_info=True)
            st.error(f"Erro ao adicionar usuário: {e}")

    def remove_user(self, user_name):
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            logging.info(f"Tentando remover usuário: {user_name}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba_name = 'users'
            if aba_name not in [sheet.title for sheet in archive.worksheets()]:
                logging.error(f"A aba '{aba_name}' não existe no Google Sheets.")
                st.error(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return
            aba = archive.worksheet_by_title(aba_name)
            data = aba.get_all_values()
            
            # Find the row to delete
            for i, row in enumerate(data):
                if user_name in row:  # Assuming username is a unique identifier
                    aba.delete_rows(i+1)  # i+1 because sheet indices start at 1
                    logging.info("Usuário removido com sucesso.")
                    st.success("Usuário removido com sucesso!")
                    return
            st.error("Usuário não encontrado na aba 'users'.")
        except Exception as e:
            logging.error(f"Erro ao remover usuário: {e}", exc_info=True)
            st.error(f"Erro ao remover usuário: {e}")

    def ensure_budget_sheet_exists(self):
        """Garante que a aba 'budget' existe com as colunas corretas"""
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            sheet_title = 'budget'
            if sheet_title not in [sheet.title for sheet in archive.worksheets()]:
                aba = archive.add_worksheet(sheet_title, rows=1, cols=3)
                aba.update_row(1, ['id', 'ano', 'valor'])
                logging.info(f"Aba '{sheet_title}' criada com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao verificar/criar a aba 'budget': {e}", exc_info=True)
    
    def carregar_dados_budget(self):
        """Carrega os dados da aba 'budget'"""
        return self.carregar_dados_aba('budget')
    
    def adc_budget(self, ano, valor):
        """Adiciona um novo registro de orçamento"""
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            self.ensure_budget_sheet_exists()
            logging.info(f"Tentando adicionar orçamento: Ano {ano}, Valor {valor}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('budget')
            
            # Gera ID único
            existing_ids = [row[0] for row in aba.get_all_values()[1:]]
            while True:
                new_id = random.randint(1000, 9999)
                if str(new_id) not in existing_ids:
                    break
            
            new_data = [new_id, ano, valor]
            aba.append_table(values=[new_data])
            logging.info("Orçamento adicionado com sucesso.")
            return True
        except Exception as e:
            logging.error(f"Erro ao adicionar orçamento: {e}", exc_info=True)
            return False
    
    def editar_budget(self, id, ano, valor):
        """Edita um registro de orçamento existente"""
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            logging.info(f"Tentando editar orçamento ID {id}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('budget')
            data = aba.get_all_values()
            
            for i, row in enumerate(data):
                if row[0] == str(id):
                    updated_row = [str(id), ano, valor]
                    aba.update_row(i + 1, updated_row)
                    logging.info("Orçamento editado com sucesso.")
                    return True
                    
            logging.error(f"ID {id} não encontrado.")
            return False
        except Exception as e:
            logging.error(f"Erro ao editar orçamento: {e}", exc_info=True)
            return False
    
    def excluir_budget(self, id):
        """Exclui um registro de orçamento"""
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            logging.info(f"Tentando excluir orçamento ID {id}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('budget')
            data = aba.get_all_values()
            
            for i, row in enumerate(data):
                if row[0] == str(id):
                    aba.delete_rows(i + 1)
                    logging.info("Orçamento excluído com sucesso.")
                    return True
                    
            logging.error(f"ID {id} não encontrado.")
            return False
        except Exception as e:
            logging.error(f"Erro ao excluir orçamento: {e}", exc_info=True)
            return False
                
