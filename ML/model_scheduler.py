import schedule
import time
import logging
from datetime import datetime
import joblib
import os
from End.Operations import SheetOperations
from ML.demand_forecasting import DemandForecasting
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelScheduler:
    """
    Agendador para retreinamento automático dos modelos de ML.
    """
    
    def __init__(self, models_dir='ML/saved_models'):
        self.models_dir = models_dir
        self.sheet_ops = SheetOperations()
        self.forecaster = DemandForecasting()
        
        # Criar diretório se não existir
        os.makedirs(self.models_dir, exist_ok=True)
    
    def retrain_all_models(self):
        """
        Retreina todos os modelos com os dados mais recentes.
        """
        try:
            logger.info("=" * 50)
            logger.info(f"Iniciando retreinamento automático em {datetime.now()}")
            logger.info("=" * 50)
            
            # Carregar dados
            data = self.sheet_ops.carregar_dados()
            if not data or len(data) <= 1:
                logger.error("Não foi possível carregar dados")
                return
            
            df = pd.DataFrame(data[1:], columns=data[0])
            df_prepared = self.forecaster.prepare_data(df)
            
            if df_prepared.empty:
                logger.error("Dados preparados estão vazios")
                return
            
            # Lista de EPIs
            epis = df_prepared['epi_name'].unique()
            logger.info(f"Total de EPIs para treinar: {len(epis)}")
            
            success_count = 0
            fail_count = 0
            
            for epi in epis:
                try:
                    logger.info(f"Treinando modelo para: {epi}")
                    
                    # Treinar modelos
                    xgb_result = self.forecaster.train_xgboost_model(df_prepared, epi)
                    prophet_result = self.forecaster.train_prophet_model(df_prepared, epi)
                    
                    if xgb_result and prophet_result:
                        # Salvar modelos
                        model_path = os.path.join(self.models_dir, f"{epi.replace(' ', '_')}")
                        os.makedirs(model_path, exist_ok=True)
                        
                        # Salvar XGBoost
                        joblib.dump(
                            xgb_result['model'],
                            os.path.join(model_path, 'xgboost_model.pkl')
                        )
                        
                        # Salvar Prophet
                        joblib.dump(
                            prophet_result['model'],
                            os.path.join(model_path, 'prophet_model.pkl')
                        )
                        
                        # Salvar métricas
                        metrics = {
                            'xgboost': xgb_result['metrics'],
                            'prophet': prophet_result['metrics'],
                            'trained_at': datetime.now().isoformat(),
                            'data_points': len(df_prepared[df_prepared['epi_name'] == epi])
                        }
                        
                        joblib.dump(
                            metrics,
                            os.path.join(model_path, 'metrics.pkl')
                        )
                        
                        logger.info(f"✓ Modelo salvo para {epi}")
                        logger.info(f"  - XGBoost MAE: {xgb_result['metrics']['mae']:.2f}")
                        logger.info(f"  - Prophet MAE: {prophet_result['metrics']['mae']:.2f}")
                        
                        success_count += 1
                    else:
                        logger.warning(f"✗ Falha ao treinar {epi}")
                        fail_count += 1
                        
                except Exception as e:
                    logger.error(f"✗ Erro ao processar {epi}: {str(e)}")
                    fail_count += 1
            
            logger.info("=" * 50)
            logger.info(f"Retreinamento concluído!")
            logger.info(f"Sucesso: {success_count} | Falhas: {fail_count}")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"Erro geral no retreinamento: {str(e)}")
    
    def load_model(self, epi_name: str):
        """
        Carrega um modelo salvo.
        """
        try:
            model_path = os.path.join(self.models_dir, f"{epi_name.replace(' ', '_')}")
            
            if not os.path.exists(model_path):
                return None
            
            xgb_model = joblib.load(os.path.join(model_path, 'xgboost_model.pkl'))
            prophet_model = joblib.load(os.path.join(model_path, 'prophet_model.pkl'))
            metrics = joblib.load(os.path.join(model_path, 'metrics.pkl'))
            
            return {
                'xgboost': xgb_model,
                'prophet': prophet_model,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo para {epi_name}: {str(e)}")
            return None
    
    def get_model_info(self, epi_name: str):
        """
        Retorna informações sobre um modelo salvo.
        """
        try:
            model_path = os.path.join(self.models_dir, f"{epi_name.replace(' ', '_')}")
            
            if not os.path.exists(model_path):
                return None
            
            metrics = joblib.load(os.path.join(model_path, 'metrics.pkl'))
            return metrics
            
        except Exception as e:
            logger.error(f"Erro ao obter informações do modelo: {str(e)}")
            return None
    
    def schedule_daily_retrain(self, time_str="02:00"):
        """
        Agenda retreinamento diário.
        
        Args:
            time_str: Horário no formato "HH:MM"
        """
        schedule.every().day.at(time_str).do(self.retrain_all_models)
        logger.info(f"Retreinamento agendado para todos os dias às {time_str}")
    
    def schedule_weekly_retrain(self, day="monday", time_str="02:00"):
        """
        Agenda retreinamento semanal.
        
        Args:
            day: Dia da semana (monday, tuesday, etc)
            time_str: Horário no formato "HH:MM"
        """
        getattr(schedule.every(), day).at(time_str).do(self.retrain_all_models)
        logger.info(f"Retreinamento agendado para toda {day} às {time_str}")
    
    def run_scheduler(self):
        """
        Executa o loop do agendador.
        """
        logger.info("Iniciando scheduler de modelos ML...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto


# Script para execução standalone
if __name__ == "__main__":
    scheduler = ModelScheduler()
    
    # Retreinar imediatamente ao iniciar
    logger.info("Executando primeiro retreinamento...")
    scheduler.retrain_all_models()
    
    # Agendar retreinamentos semanais (toda segunda-feira às 2h da manhã)
    scheduler.schedule_weekly_retrain("monday", "02:00")
    
    # Iniciar loop
    try:
        scheduler.run_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler interrompido pelo usuário")
