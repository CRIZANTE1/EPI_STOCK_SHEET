import pandas as pd
from datetime import datetime, timedelta
from API_Operation import PDFQA 


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


def get_ia_insights_for_alert(requester, epi_name, df_stock):
    """
    Usa a IA Generativa para analisar o histórico de um funcionário/EPI
    e fornecer insights adicionais sobre o consumo.
    """
    try:
        history_df = df_stock[
            (df_stock['requester'] == requester) &
            (df_stock['epi_name'] == epi_name) &
            (df_stock['transaction_type'].str.lower() == 'saída')
        ].copy()

        if len(history_df) < 2:
            return "Histórico insuficiente para análise de padrão de consumo."

        history_df['date'] = pd.to_datetime(history_df['date'], errors='coerce')
        history_df = history_df.sort_values(by='date')
        
        # Calcula os dias entre cada retirada
        history_df['intervalo_dias'] = history_df['date'].diff().dt.days
        
        # Prepara o contexto para a IA
        datas_retirada = history_df['date'].dt.strftime('%d/%m/%Y').tolist()
        intervalos = history_df['intervalo_dias'].dropna().astype(int).tolist()
        media_intervalo = sum(intervalos) / len(intervalos) if intervalos else 0
        regra_troca = get_replacement_period(epi_name) or "Não definida"

        contexto = f"""
        Analise o padrão de consumo do EPI '{epi_name}' para o funcionário '{requester}'.

        Dados:
        - Datas de retirada (do mais antigo ao mais novo): {datas_retirada}
        - Intervalo em dias entre as retiradas: {intervalos}
        - Média de troca observada: {media_intervalo:.1f} dias.
        - Regra de troca esperada: {regra_troca} dias.

        Com base nesses dados, forneça uma análise curta e direta respondendo a:
        1. O consumo deste funcionário é regular, muito frequente (acelerado) ou pouco frequente (lento) em comparação com a regra esperada?
        2. Existe algum comportamento que mereça atenção (ex: um pico de retiradas, ou um longo período sem retirar)?
        3. Dê uma recomendação breve.
        """
        
        # Chama a IA
        ai_engine = PDFQA()
        # Usamos uma função genérica de pergunta/resposta da sua classe de IA
        response = ai_engine.ask_gemini(contexto, "Qual a análise do padrão de consumo?")
        
        return response

    except Exception as e:
        return f"Erro na análise de IA: {str(e)}"  
