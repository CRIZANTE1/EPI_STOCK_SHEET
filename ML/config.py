"""
Configurações para o sistema de Machine Learning
"""
import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ModelConfig:
    """Configurações dos modelos de ML"""
    
    # XGBoost
    xgboost_params: Dict = None
    
    # Prophet
    prophet_params: Dict = None
    
    # Ensemble
    ensemble_weights: Dict = None
    
    # Features
    lag_periods: List[int] = None
    rolling_windows: List[int] = None
    
    # Treino
    test_size: float = 0.2
    random_state: int = 42
    
    # Cache
    cache_ttl: int = 3600  # 1 hora
    
    def __post_init__(self):
        if self.xgboost_params is None:
            self.xgboost_params = {
                'n_estimators': 100,
                'max_depth': 5,
                'learning_rate': 0.1,
                'random_state': self.random_state,
                'objective': 'reg:squarederror',
                'n_jobs': -1
            }
        
        if self.prophet_params is None:
            self.prophet_params = {
                'yearly_seasonality': True,
                'weekly_seasonality': True,
                'daily_seasonality': False,
                'seasonality_mode': 'multiplicative',
                'changepoint_prior_scale': 0.05
            }
        
        if self.ensemble_weights is None:
            self.ensemble_weights = {
                'xgboost': 0.5,
                'prophet': 0.5
            }
        
        if self.lag_periods is None:
            self.lag_periods = [7, 14, 30]
        
        if self.rolling_windows is None:
            self.rolling_windows = [7, 30]


@dataclass
class ForecastConfig:
    """Configurações de previsão"""
    
    # Horizonte padrão
    default_forecast_days: int = 90
    max_forecast_days: int = 180
    min_forecast_days: int = 7
    
    # Estoque de segurança
    default_safety_stock_days: int = 30
    min_safety_stock_days: int = 7
    max_safety_stock_days: int = 60
    
    # Níveis de prioridade (dias de cobertura)
    priority_levels: Dict = None
    
    def __post_init__(self):
        if self.priority_levels is None:
            self.priority_levels = {
                'CRÍTICA': 0,      # Sem estoque
                'ALTA': 7,         # Menos de 7 dias
                'MÉDIA': 30,       # Menos de 30 dias
                'BAIXA': 60        # Menos de 60 dias
            }


@dataclass
class DataConfig:
    """Configurações de dados"""
    
    # Requisitos mínimos
    min_data_points: int = 30
    min_data_points_for_seasonality: int = 90
    
    # Limpeza de dados
    outlier_threshold: float = 3.0  # Desvios padrão
    remove_zeros: bool = False
    interpolate_missing: bool = True
    
    # Agregação
    aggregation_frequency: str = 'D'  # Diário
    
    # Validação
    validate_dates: bool = True
    validate_quantities: bool = True


@dataclass
class PerformanceConfig:
    """Configurações de análise de performance"""
    
    # Backtest
    default_train_size: int = 180
    default_test_size: int = 30
    max_backtest_iterations: int = 10
    
    # Métricas
    primary_metric: str = 'mae'  # mae, rmse, mape
    acceptable_mape: float = 20.0  # %
    good_mape: float = 10.0  # %
    excellent_mape: float = 5.0  # %
    
    # Relatórios
    report_format: str = 'json'  # json, csv, pdf


@dataclass
class SchedulerConfig:
    """Configurações do agendador"""
    
    # Frequência de retreinamento
    retrain_frequency: str = 'weekly'  # daily, weekly, monthly
    retrain_day: str = 'monday'
    retrain_time: str = '02:00'
    
    # Modelos a retreinar
    retrain_all_epis: bool = True
    priority_epis: List[str] = None
    
    # Armazenamento
    models_dir: str = 'ML/saved_models'
    keep_n_versions: int = 3  # Manter últimas N versões
    
    # Notificações
    send_notifications: bool = False
    notification_email: str = None
    
    def __post_init__(self):
        if self.priority_epis is None:
            self.priority_epis = []


@dataclass
class SystemConfig:
    """Configuração geral do sistema"""
    
    model: ModelConfig = None
    forecast: ForecastConfig = None
    data: DataConfig = None
    performance: PerformanceConfig = None
    scheduler: SchedulerConfig = None
    
    # Paths
    base_dir: str = os.path.dirname(os.path.abspath(__file__))
    cache_dir: str = None
    logs_dir: str = None
    
    # Logging
    log_level: str = 'INFO'
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Otimizações
    use_multiprocessing: bool = True
    max_workers: int = 4
    
    def __post_init__(self):
        if self.model is None:
            self.model = ModelConfig()
        
        if self.forecast is None:
            self.forecast = ForecastConfig()
        
        if self.data is None:
            self.data = DataConfig()
        
        if self.performance is None:
            self.performance = PerformanceConfig()
        
        if self.scheduler is None:
            self.scheduler = SchedulerConfig()
        
        if self.cache_dir is None:
            self.cache_dir = os.path.join(self.base_dir, 'cache')
        
        if self.logs_dir is None:
            self.logs_dir = os.path.join(self.base_dir, '../logs')
        
        # Criar diretórios se não existirem
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.scheduler.models_dir, exist_ok=True)


# Instância global de configuração
config = SystemConfig()


# Funções auxiliares para obter configurações
def get_model_config() -> ModelConfig:
    """Retorna configurações dos modelos"""
    return config.model


def get_forecast_config() -> ForecastConfig:
    """Retorna configurações de previsão"""
    return config.forecast


def get_data_config() -> DataConfig:
    """Retorna configurações de dados"""
    return config.data


def get_performance_config() -> PerformanceConfig:
    """Retorna configurações de performance"""
    return config.performance


def get_scheduler_config() -> SchedulerConfig:
    """Retorna configurações do agendador"""
    return config.scheduler


# Função para carregar configuração customizada
def load_custom_config(config_file: str):
    """
    Carrega configuração de arquivo YAML ou JSON
    
    Args:
        config_file: Caminho para arquivo de configuração
    """
    import json
    import yaml
    
    _, ext = os.path.splitext(config_file)
    
    with open(config_file, 'r') as f:
        if ext in ['.yaml', '.yml']:
            custom_config = yaml.safe_load(f)
        elif ext == '.json':
            custom_config = json.load(f)
        else:
            raise ValueError(f"Formato não suportado: {ext}")
    
    # Atualizar configuração global
    global config
    
    if 'model' in custom_config:
        config.model = ModelConfig(**custom_config['model'])
    
    if 'forecast' in custom_config:
        config.forecast = ForecastConfig(**custom_config['forecast'])
    
    if 'data' in custom_config:
        config.data = DataConfig(**custom_config['data'])
    
    if 'performance' in custom_config:
        config.performance = PerformanceConfig(**custom_config['performance'])
    
    if 'scheduler' in custom_config:
        config.scheduler = SchedulerConfig(**custom_config['scheduler'])
    
    return config


# Função para salvar configuração atual
def save_config(output_file: str):
    """
    Salva configuração atual em arquivo
    
    Args:
        output_file: Caminho para salvar configuração
    """
    import json
    from dataclasses import asdict
    
    config_dict = {
        'model': asdict(config.model),
        'forecast': asdict(config.forecast),
        'data': asdict(config.data),
        'performance': asdict(config.performance),
        'scheduler': asdict(config.scheduler)
    }
    
    _, ext = os.path.splitext(output_file)
    
    with open(output_file, 'w') as f:
        if ext in ['.yaml', '.yml']:
            import yaml
            yaml.dump(config_dict, f, default_flow_style=False)
        elif ext == '.json':
            json.dump(config_dict, f, indent=2)
        else:
            raise ValueError(f"Formato não suportado: {ext}")


# Exemplo de uso
if __name__ == "__main__":
    # Usar configuração padrão
    print("Configuração Padrão:")
    print(f"XGBoost params: {config.model.xgboost_params}")
    print(f"Forecast days: {config.forecast.default_forecast_days}")
    print(f"Min data points: {config.data.min_data_points}")
    
    # Salvar configuração
    save_config('ML/config_default.json')
    print("\nConfiguração salva em: ML/config_default.json")
    
    # Carregar configuração customizada (exemplo)
    # load_custom_config('ML/config_custom.yaml')
