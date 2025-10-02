import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb
from prophet import Prophet

# Plotting
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemandForecasting:
    """
    Sistema avançado de previsão de demanda para EPIs usando múltiplos modelos de ML.
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.predictions_cache = {}
        
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara os dados para modelagem ML.
        
        Args:
            df: DataFrame com histórico de transações
            
        Returns:
            DataFrame processado e enriquecido com features
        """
        logger.info("Preparando dados para modelagem...")
        
        # Filtrar apenas saídas
        df_saidas = df[df['transaction_type'].str.lower() == 'saída'].copy()
        
        # Converter datas
        df_saidas['date'] = pd.to_datetime(df_saidas['date'], errors='coerce')
        df_saidas['quantity'] = pd.to_numeric(df_saidas['quantity'], errors='coerce').fillna(0)
        
        # Remover linhas sem data
        df_saidas = df_saidas.dropna(subset=['date'])
        
        # Agregar por dia e EPI
        df_agg = df_saidas.groupby([
            pd.Grouper(key='date', freq='D'),
            'epi_name'
        ])['quantity'].sum().reset_index()
        
        # Criar features temporais
        df_agg['year'] = df_agg['date'].dt.year
        df_agg['month'] = df_agg['date'].dt.month
        df_agg['day'] = df_agg['date'].dt.day
        df_agg['dayofweek'] = df_agg['date'].dt.dayofweek
        df_agg['quarter'] = df_agg['date'].dt.quarter
        df_agg['weekofyear'] = df_agg['date'].dt.isocalendar().week
        df_agg['is_weekend'] = df_agg['dayofweek'].isin([5, 6]).astype(int)
        
        # Features de lag (valores anteriores)
        for epi in df_agg['epi_name'].unique():
            mask = df_agg['epi_name'] == epi
            df_agg.loc[mask, 'lag_7'] = df_agg.loc[mask, 'quantity'].shift(7).fillna(0)
            df_agg.loc[mask, 'lag_14'] = df_agg.loc[mask, 'quantity'].shift(14).fillna(0)
            df_agg.loc[mask, 'lag_30'] = df_agg.loc[mask, 'quantity'].shift(30).fillna(0)
            
            # Médias móveis
            df_agg.loc[mask, 'rolling_mean_7'] = df_agg.loc[mask, 'quantity'].rolling(7, min_periods=1).mean()
            df_agg.loc[mask, 'rolling_mean_30'] = df_agg.loc[mask, 'quantity'].rolling(30, min_periods=1).mean()
            df_agg.loc[mask, 'rolling_std_7'] = df_agg.loc[mask, 'quantity'].rolling(7, min_periods=1).std().fillna(0)
        
        logger.info(f"Dados preparados: {len(df_agg)} registros")
        return df_agg
    
    def train_xgboost_model(self, df: pd.DataFrame, epi_name: str) -> Dict:
        """
        Treina modelo XGBoost para um EPI específico.
        """
        logger.info(f"Treinando XGBoost para {epi_name}...")
        
        # Filtrar dados do EPI
        df_epi = df[df['epi_name'] == epi_name].copy()
        
        if len(df_epi) < 30:
            logger.warning(f"Dados insuficientes para {epi_name}")
            return None
        
        # Preparar features e target
        feature_cols = [
            'year', 'month', 'day', 'dayofweek', 'quarter', 'weekofyear',
            'is_weekend', 'lag_7', 'lag_14', 'lag_30', 
            'rolling_mean_7', 'rolling_mean_30', 'rolling_std_7'
        ]
        
        X = df_epi[feature_cols]
        y = df_epi['quantity']
        
        # Split treino/teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Treinar modelo
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )
        
        model.fit(X_train, y_train)
        
        # Predições
        y_pred = model.predict(X_test)
        
        # Métricas
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # Feature importance
        importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info(f"XGBoost - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R²: {r2:.3f}")
        
        return {
            'model': model,
            'metrics': {'mae': mae, 'rmse': rmse, 'r2': r2},
            'feature_importance': importance,
            'X_test': X_test,
            'y_test': y_test,
            'y_pred': y_pred
        }
    
    def train_prophet_model(self, df: pd.DataFrame, epi_name: str) -> Dict:
        """
        Treina modelo Prophet (Facebook) para série temporal.
        """
        logger.info(f"Treinando Prophet para {epi_name}...")
        
        # Filtrar e preparar dados
        df_epi = df[df['epi_name'] == epi_name][['date', 'quantity']].copy()
        df_epi.columns = ['ds', 'y']
        
        if len(df_epi) < 30:
            logger.warning(f"Dados insuficientes para {epi_name}")
            return None
        
        # Treinar modelo
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode='multiplicative'
        )
        
        model.fit(df_epi)
        
        # Fazer previsão no período de treino para avaliar
        forecast = model.predict(df_epi)
        
        # Métricas
        mae = mean_absolute_error(df_epi['y'], forecast['yhat'])
        rmse = np.sqrt(mean_squared_error(df_epi['y'], forecast['yhat']))
        
        logger.info(f"Prophet - MAE: {mae:.2f}, RMSE: {rmse:.2f}")
        
        return {
            'model': model,
            'metrics': {'mae': mae, 'rmse': rmse},
            'forecast': forecast
        }
    
    def predict_future_demand(
        self, 
        df: pd.DataFrame, 
        epi_name: str, 
        days_ahead: int = 90
    ) -> pd.DataFrame:
        """
        Faz previsão de demanda futura combinando múltiplos modelos.
        """
        logger.info(f"Prevendo demanda para {epi_name} - {days_ahead} dias à frente")
        
        # Treinar modelos
        xgb_result = self.train_xgboost_model(df, epi_name)
        prophet_result = self.train_prophet_model(df, epi_name)
        
        if not xgb_result or not prophet_result:
            return None
        
        # Criar datas futuras
        last_date = df[df['epi_name'] == epi_name]['date'].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=days_ahead,
            freq='D'
        )
        
        # Prophet prediction
        future_df = pd.DataFrame({'ds': future_dates})
        prophet_forecast = prophet_result['model'].predict(future_df)
        
        # XGBoost prediction (precisa de features)
        # Criar features para datas futuras
        future_features = pd.DataFrame({
            'date': future_dates,
            'year': future_dates.year,
            'month': future_dates.month,
            'day': future_dates.day,
            'dayofweek': future_dates.dayofweek,
            'quarter': future_dates.quarter,
            'weekofyear': future_dates.isocalendar().week,
            'is_weekend': future_dates.dayofweek.isin([5, 6]).astype(int)
        })
        
        # Usar últimos valores conhecidos para lags
        last_values = df[df['epi_name'] == epi_name].tail(30)['quantity'].values
        future_features['lag_7'] = np.mean(last_values[-7:]) if len(last_values) >= 7 else 0
        future_features['lag_14'] = np.mean(last_values[-14:]) if len(last_values) >= 14 else 0
        future_features['lag_30'] = np.mean(last_values) if len(last_values) > 0 else 0
        future_features['rolling_mean_7'] = np.mean(last_values[-7:]) if len(last_values) >= 7 else 0
        future_features['rolling_mean_30'] = np.mean(last_values) if len(last_values) > 0 else 0
        future_features['rolling_std_7'] = np.std(last_values[-7:]) if len(last_values) >= 7 else 0
        
        feature_cols = [
            'year', 'month', 'day', 'dayofweek', 'quarter', 'weekofyear',
            'is_weekend', 'lag_7', 'lag_14', 'lag_30',
            'rolling_mean_7', 'rolling_mean_30', 'rolling_std_7'
        ]
        
        xgb_predictions = xgb_result['model'].predict(future_features[feature_cols])
        
        # Combinar previsões (ensemble)
        combined_predictions = (prophet_forecast['yhat'].values + xgb_predictions) / 2
        combined_predictions = np.maximum(combined_predictions, 0)  # Não permitir negativos
        
        # Criar DataFrame com resultados
        results = pd.DataFrame({
            'date': future_dates,
            'epi_name': epi_name,
            'prophet_prediction': prophet_forecast['yhat'].values,
            'xgboost_prediction': xgb_predictions,
            'ensemble_prediction': combined_predictions,
            'lower_bound': prophet_forecast['yhat_lower'].values,
            'upper_bound': prophet_forecast['yhat_upper'].values
        })
        
        return results
    
    def generate_purchase_recommendations(
        self,
        predictions_df: pd.DataFrame,
        current_stock: Dict[str, float],
        safety_stock_days: int = 30
    ) -> Dict:
        """
        Gera recomendações de compra baseadas nas previsões.
        """
        recommendations = []
        
        for epi in predictions_df['epi_name'].unique():
            epi_pred = predictions_df[predictions_df['epi_name'] == epi]
            
            # Demanda prevista para os próximos X dias
            total_demand = epi_pred['ensemble_prediction'].sum()
            
            # Estoque atual
            current = current_stock.get(epi, 0)
            
            # Estoque de segurança baseado na demanda média diária
            avg_daily_demand = epi_pred['ensemble_prediction'].mean()
            safety_stock = avg_daily_demand * safety_stock_days
            
            # Quantidade recomendada
            recommended_qty = max(0, total_demand + safety_stock - current)
            
            # Prioridade (baseada em quão crítico está o estoque)
            if current <= 0:
                priority = "CRÍTICA"
            elif current < avg_daily_demand * 7:
                priority = "ALTA"
            elif current < avg_daily_demand * 30:
                priority = "MÉDIA"
            else:
                priority = "BAIXA"
            
            recommendations.append({
                'epi': epi,
                'estoque_atual': current,
                'demanda_prevista_90d': total_demand,
                'demanda_media_diaria': avg_daily_demand,
                'estoque_seguranca': safety_stock,
                'quantidade_recomendada': np.ceil(recommended_qty),
                'prioridade': priority,
                'dias_cobertura': current / avg_daily_demand if avg_daily_demand > 0 else 999
            })
        
        return pd.DataFrame(recommendations).sort_values('prioridade', ascending=False)
    
    def plot_forecast(self, historical_df: pd.DataFrame, predictions_df: pd.DataFrame, epi_name: str):
        """
        Cria visualização interativa da previsão.
        """
        # Filtrar dados históricos
        hist = historical_df[historical_df['epi_name'] == epi_name].copy()
        
        # Criar figura
        fig = go.Figure()
        
        # Dados históricos
        fig.add_trace(go.Scatter(
            x=hist['date'],
            y=hist['quantity'],
            mode='lines+markers',
            name='Histórico',
            line=dict(color='blue', width=2)
        ))
        
        # Previsão ensemble
        fig.add_trace(go.Scatter(
            x=predictions_df['date'],
            y=predictions_df['ensemble_prediction'],
            mode='lines',
            name='Previsão (Ensemble)',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        # Intervalo de confiança
        fig.add_trace(go.Scatter(
            x=predictions_df['date'],
            y=predictions_df['upper_bound'],
            mode='lines',
            name='Limite Superior',
            line=dict(width=0),
            showlegend=False
        ))
        
        fig.add_trace(go.Scatter(
            x=predictions_df['date'],
            y=predictions_df['lower_bound'],
            mode='lines',
            name='Limite Inferior',
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.2)',
            line=dict(width=0),
            showlegend=True
        ))
        
        fig.update_layout(
            title=f'Previsão de Demanda - {epi_name}',
            xaxis_title='Data',
            yaxis_title='Quantidade',
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
        
        return fig
    
    def analyze_seasonality(self, df: pd.DataFrame, epi_name: str):
        """
        Analisa padrões sazonais na demanda.
        """
        df_epi = df[df['epi_name'] == epi_name].copy()
        
        # Análise mensal
        monthly = df_epi.groupby('month')['quantity'].mean().reset_index()
        
        # Análise por dia da semana
        weekly = df_epi.groupby('dayofweek')['quantity'].mean().reset_index()
        weekly['day_name'] = weekly['dayofweek'].map({
            0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 
            4: 'Sex', 5: 'Sáb', 6: 'Dom'
        })
        
        # Criar subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Sazonalidade Mensal', 'Padrão Semanal')
        )
        
        fig.add_trace(
            go.Bar(x=monthly['month'], y=monthly['quantity'], name='Mensal'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=weekly['day_name'], y=weekly['quantity'], name='Semanal'),
            row=1, col=2
        )
        
        fig.update_layout(
            title=f'Análise de Sazonalidade - {epi_name}',
            showlegend=False,
            height=400
        )
        
        return fig
