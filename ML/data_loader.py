"""
Utilitário para carregar e processar dados do Google Sheets
Corrige problemas de formato e validação
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """
    Carrega e processa dados do sistema de EPIs
    """
    
    EXPECTED_COLUMNS = [
        'id', 'epi_name', 'quantity', 'transaction_type', 
        'date', 'value', 'requester', 'CA', 'image_url'
    ]
    
    def __init__(self, sheet_operations=None):
        """
        Inicializa o DataLoader
        
        Args:
            sheet_operations: Instância de SheetOperations
        """
        self.sheet_operations = sheet_operations
    
    def load_data(self) -> pd.DataFrame:
        """
        Carrega dados da planilha e retorna DataFrame processado
        
        Returns:
            DataFrame com dados limpos e validados
        """
        if not self.sheet_operations:
            from End.Operations import SheetOperations
            self.sheet_operations = SheetOperations()
        
        # Carregar dados brutos
        data = self.sheet_operations.carregar_dados()
        
        if not data or len(data) <= 1:
            logger.warning("Nenhum dado encontrado na planilha")
            return pd.DataFrame(columns=self.EXPECTED_COLUMNS)
        
        # Verificar estrutura
        headers = data[0]
        rows = data[1:]
        
        logger.info(f"Cabeçalhos encontrados: {headers}")
        logger.info(f"Total de registros: {len(rows)}")
        
        # Criar DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        # Verificar se todas as colunas esperadas existem
        missing_cols = set(self.EXPECTED_COLUMNS) - set(df.columns)
        if missing_cols:
            logger.error(f"Colunas faltando: {missing_cols}")
            # Adicionar colunas faltantes
            for col in missing_cols:
                df[col] = ''
        
        # Processar dados
        df = self._process_dataframe(df)
        
        return df
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa e limpa o DataFrame
        
        Args:
            df: DataFrame bruto
            
        Returns:
            DataFrame processado
        """
        logger.info("Processando DataFrame...")
        
        # Criar cópia para não modificar original
        df = df.copy()
        
        # Remover linhas completamente vazias
        df = df.dropna(how='all')
        
        # Processar cada coluna
        df = self._process_id(df)
        df = self._process_epi_name(df)
        df = self._process_quantity(df)
        df = self._process_transaction_type(df)
        df = self._process_date(df)
        df = self._process_value(df)
        df = self._process_requester(df)
        df = self._process_ca(df)
        df = self._process_image_url(df)
        
        # Validar dados
        df = self._validate_data(df)
        
        logger.info(f"DataFrame processado: {len(df)} registros válidos")
        
        return df
    
    def _process_id(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de ID"""
        df['id'] = df['id'].astype(str).str.strip()
        return df
    
    def _process_epi_name(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de nome do EPI"""
        df['epi_name'] = df['epi_name'].astype(str).str.strip()
        # Remover caracteres especiais problemáticos
        df['epi_name'] = df['epi_name'].str.replace(r'[^\w\s\(\)\-]', '', regex=True)
        return df
    
    def _process_quantity(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de quantidade"""
        # Converter para numérico, valores inválidos viram NaN
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        # Preencher NaN com 0
        df['quantity'] = df['quantity'].fillna(0)
        # Garantir que seja inteiro e positivo
        df['quantity'] = df['quantity'].abs().astype(int)
        return df
    
    def _process_transaction_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de tipo de transação"""
        df['transaction_type'] = df['transaction_type'].astype(str).str.lower().str.strip()
        
        # Normalizar variações
        df['transaction_type'] = df['transaction_type'].replace({
            'entrada': 'entrada',
            'entradas': 'entrada',
            'input': 'entrada',
            'saida': 'saída',
            'saída': 'saída',
            'saidas': 'saída',
            'saídas': 'saída',
            'output': 'saída',
            'exit': 'saída'
        })
        
        # Marcar valores inválidos
        valid_types = ['entrada', 'saída']
        df.loc[~df['transaction_type'].isin(valid_types), 'transaction_type'] = 'saída'
        
        return df
    
    def _process_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de data"""
        # Tentar converter para datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
        
        # Para datas inválidas, usar data atual
        df.loc[df['date'].isna(), 'date'] = datetime.now()
        
        # Verificar datas futuras (provavelmente erro)
        future_mask = df['date'] > datetime.now()
        if future_mask.any():
            logger.warning(f"Encontradas {future_mask.sum()} datas futuras. Corrigindo para data atual.")
            df.loc[future_mask, 'date'] = datetime.now()
        
        return df
    
    def _process_value(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de valor"""
        # Função para limpar valor monetário
        def clean_value(val):
            if pd.isna(val) or val == '':
                return 0.0
            
            val_str = str(val).strip()
            
            # Remover símbolos de moeda
            val_str = val_str.replace('R$', '').replace('$', '')
            
            # Se tem vírgula e ponto, assumir formato brasileiro
            if ',' in val_str and '.' in val_str:
                val_str = val_str.replace('.', '').replace(',', '.')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            
            try:
                return float(val_str)
            except:
                return 0.0
        
        df['value'] = df['value'].apply(clean_value)
        df['value'] = df['value'].abs()  # Garantir positivo
        
        return df
    
    def _process_requester(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de requisitante"""
        df['requester'] = df['requester'].astype(str).str.strip()
        # Capitalizar nomes
        df['requester'] = df['requester'].str.title()
        return df
    
    def _process_ca(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de CA"""
        df['CA'] = df['CA'].astype(str).str.strip()
        # Remover caracteres não numéricos
        df['CA'] = df['CA'].str.replace(r'\D', '', regex=True)
        return df
    
    def _process_image_url(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa coluna de URL de imagem"""
        if 'image_url' not in df.columns:
            df['image_url'] = ''
        else:
            df['image_url'] = df['image_url'].astype(str).str.strip()
            df['image_url'] = df['image_url'].replace('nan', '')
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida e remove registros inválidos"""
        initial_count = len(df)
        
        # Remover registros sem EPI
        df = df[df['epi_name'] != '']
        df = df[df['epi_name'] != 'nan']
        
        # Remover registros com quantidade 0 ou negativa
        df = df[df['quantity'] > 0]
        
        # Remover registros muito antigos (mais de 5 anos)
        five_years_ago = datetime.now() - pd.Timedelta(days=365*5)
        df = df[df['date'] >= five_years_ago]
        
        removed = initial_count - len(df)
        if removed > 0:
            logger.info(f"Removidos {removed} registros inválidos")
        
        return df
    
    def get_stock_summary(self, df: pd.DataFrame) -> Dict:
        """
        Gera resumo do estoque atual
        
        Args:
            df: DataFrame com dados processados
            
        Returns:
            Dicionário com resumo do estoque
        """
        # Calcular estoque atual por EPI
        df_entrada = df[df['transaction_type'] == 'entrada'].groupby('epi_name')['quantity'].sum()
        df_saida = df[df['transaction_type'] == 'saída'].groupby('epi_name')['quantity'].sum()
        
        # Unir índices
        all_epis = df_entrada.index.union(df_saida.index)
        estoque_atual = df_entrada.reindex(all_epis, fill_value=0) - df_saida.reindex(all_epis, fill_value=0)
        
        summary = {
            'total_epis': len(estoque_atual),
            'epis_em_estoque': len(estoque_atual[estoque_atual > 0]),
            'epis_zerados': len(estoque_atual[estoque_atual <= 0]),
            'total_entradas': df_entrada.sum(),
            'total_saidas': df_saida.sum(),
            'estoque_por_epi': estoque_atual.to_dict(),
            'periodo_dados': {
                'inicio': df['date'].min().strftime('%Y-%m-%d'),
                'fim': df['date'].max().strftime('%Y-%m-%d'),
                'dias': (df['date'].max() - df['date'].min()).days
            }
        }
        
        return summary
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = 'estoque_epi.csv'):
        """
        Exporta DataFrame para CSV
        
        Args:
            df: DataFrame a exportar
            filename: Nome do arquivo
        """
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"Dados exportados para {filename}")
    
    def get_data_quality_report(self, df: pd.DataFrame) -> Dict:
        """
        Gera relatório de qualidade dos dados
        
        Args:
            df: DataFrame processado
            
        Returns:
            Dicionário com métricas de qualidade
        """
        report = {
            'total_registros': len(df),
            'colunas': list(df.columns),
            'tipos_transacao': df['transaction_type'].value_counts().to_dict(),
            'periodo': {
                'inicio': df['date'].min().strftime('%Y-%m-%d'),
                'fim': df['date'].max().strftime('%Y-%m-%d')
            },
            'estatisticas_quantidade': {
                'media': float(df['quantity'].mean()),
                'mediana': float(df['quantity'].median()),
                'min': int(df['quantity'].min()),
                'max': int(df['quantity'].max())
            },
            'epis_unicos': df['epi_name'].nunique(),
            'requisitantes_unicos': df['requester'].nunique(),
            'registros_sem_ca': len(df[df['CA'] == '']),
            'registros_sem_valor': len(df[df['value'] == 0])
        }
        
        return report


# Função auxiliar para uso direto
def load_and_process_data(sheet_operations=None) -> pd.DataFrame:
    """
    Função de conveniência para carregar dados
    
    Args:
        sheet_operations: Instância opcional de SheetOperations
        
    Returns:
        DataFrame processado
    """
    loader = DataLoader(sheet_operations)
    return loader.load_data()


# Teste do módulo
if __name__ == "__main__":
    from End.Operations import SheetOperations
    
    print("Carregando dados...")
    sheet_ops = SheetOperations()
    loader = DataLoader(sheet_ops)
    
    # Carregar dados
    df = loader.load_data()
    
    print(f"\n✓ Dados carregados: {len(df)} registros")
    print(f"\nColunas: {list(df.columns)}")
    
    # Mostrar primeiras linhas
    print("\nPrimeiras 5 linhas:")
    print(df.head())
    
    # Resumo do estoque
    summary = loader.get_stock_summary(df)
    print(f"\n📊 Resumo do Estoque:")
    print(f"  - Total de EPIs: {summary['total_epis']}")
    print(f"  - EPIs em estoque: {summary['epis_em_estoque']}")
    print(f"  - EPIs zerados: {summary['epis_zerados']}")
    print(f"  - Período dos dados: {summary['periodo_dados']['dias']} dias")
    
    # Relatório de qualidade
    quality = loader.get_data_quality_report(df)
    print(f"\n📋 Qualidade dos Dados:")
    print(f"  - Registros totais: {quality['total_registros']}")
    print(f"  - EPIs únicos: {quality['epis_unicos']}")
    print(f"  - Requisitantes únicos: {quality['requisitantes_unicos']}")
    print(f"  - Registros sem CA: {quality['registros_sem_ca']}")
