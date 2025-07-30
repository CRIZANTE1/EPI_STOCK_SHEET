import pandas as pd
from datetime import datetime, timedelta

EPI_REPLACEMENT_RULES = {

  "Botina de Seguranca": 180,  # 6 meses
    "Mascara de Protecao": 180, # 6 meses
    "Abafador de Ruidos": 180,  # 6 meses
    "Filtro para Mascara": 180, # 6 meses
    "Cinto de Seguranca": 180,  # 6 meses
    
    "keywords": {
        "botina": 180,
        "mascara": 180,
        "abafador": 180,
        "filtro": 180,
        "cinto": 180,
        "luva": 30, # Exemplo: luvas trocadas a cada 30 dias
        "oculos": 365, # Exemplo: óculos a cada 1 ano
    }
}

def get_replacement_period(epi_name):
    """
    Encontra o período de troca para um dado EPI.
    Primeiro busca por nome exato, depois por palavras-chave.
    """
    epi_name_lower = epi_name.lower()
    
    # 1. Busca por nome exato (case-insensitive)
    for name, period in EPI_REPLACEMENT_RULES.items():
        if name.lower() == epi_name_lower:
            return period
    
    # 2. Se não encontrar, busca por palavras-chave
    for keyword, period in EPI_REPLACEMENT_RULES["keywords"].items():
        if keyword in epi_name_lower:
            return period
            
    return None # Retorna None se não houver regra para este EPI

def analyze_replacement_alerts(df_stock):
    """
    Analisa os dados de estoque e retorna uma lista de alertas de troca de EPI.
    """
    if df_stock.empty:
        return []

    # Filtra apenas as transações de saída
    df_saidas = df_stock[df_stock['transaction_type'].str.lower() == 'saída'].copy()
    
    if df_saidas.empty:
        return []

    # Converte a coluna de data e lida com erros
    df_saidas['date'] = pd.to_datetime(df_saidas['date'], errors='coerce')
    df_saidas.dropna(subset=['date', 'requester', 'epi_name'], inplace=True)

    # Agrupa para encontrar a última data de retirada para cada funcionário/EPI
    last_withdrawals = df_saidas.loc[df_saidas.groupby(['requester', 'epi_name'])['date'].idxmax()]

    alerts = []
    today = datetime.now()

    for _, row in last_withdrawals.iterrows():
        requester = row['requester']
        epi_name = row['epi_name']
        last_date = row['date']
        
        # Pega o período de troca para o EPI
        replacement_days = get_replacement_period(epi_name)
        
        # Se existe uma regra para este EPI, calcula a data de vencimento
        if replacement_days:
            due_date = last_date + timedelta(days=replacement_days)
            days_overdue = (today - due_date).days
            
            # Se a data de troca já passou (ou é hoje)
            if days_overdue >= 0:
                alerts.append({
                    "Funcionário": requester,
                    "EPI": epi_name,
                    "Última Retirada": last_date.strftime('%d/%m/%Y'),
                    "Próxima Troca Prevista": due_date.strftime('%d/%m/%Y'),
                    "Status": f"{days_overdue} dias vencido"
                })

    # Ordena os alertas pelos mais vencidos primeiro
    sorted_alerts = sorted(alerts, key=lambda x: (x['Status'].split(' ')[0]), reverse=True)
    return sorted_alerts
