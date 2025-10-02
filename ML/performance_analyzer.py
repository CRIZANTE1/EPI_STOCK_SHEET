import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Analisa a performance dos modelos de ML ao longo do tempo.
    """
    
    def __init__(self):
        self.performance_history = []
    
    def backtest_model(self, df: pd.DataFrame, epi_name: str, 
                       train_size: int = 180, test_size: int = 30):
        """
        Realiza backtest do modelo simulando previsões no passado.
        
        Args:
            df: DataFrame com dados históricos
            epi_name: Nome do EPI
            train_size: Dias para treino
            test_size: Dias para teste
            
        Returns:
            Dict com métricas de performance
        """
        from ML.demand_forecasting import DemandForecasting
        
        logger.info(f"Iniciando backtest para {epi_name}")
        
        # Filtrar dados do EPI
        df_epi = df[df['epi_name'] == epi_name].copy()
        df_epi = df_epi.sort_values('date')
        
        if len(df_epi) < train_size + test_size:
            logger.warning(f"Dados insuficientes para backtest de {epi_name}")
            return None
        
        # Criar janelas deslizantes
        results = []
        forecaster = DemandForecasting()
        
        # Número de iterações (mover a janela de teste)
        num_iterations = min(10, len(df_epi) - train_size - test_size)
        
        for i in range(num_iterations):
            # Definir período de treino e teste
            train_end_idx = -(test_size + (num_iterations - i - 1) * test_size)
            if train_end_idx == 0:
                train_end_idx = len(df_epi)
                
            train_start_idx = max(0, train_end_idx - train_size)
            
            df_train = df_epi.iloc[train_start_idx:train_end_idx]
            df_test = df_epi.iloc[train_end_idx:train_end_idx + test_size]
            
            if len(df_test) == 0:
                continue
            
            # Preparar dados de treino
            df_train_prep = forecaster.prepare_data(
                pd.DataFrame([{'transaction_type': 'saída', 'epi_name': epi_name, 
                              'date': row['date'], 'quantity': row['quantity']} 
                             for _, row in df_train.iterrows()])
            )
            
            # Treinar modelo
            xgb_result = forecaster.train_xgboost_model(df_train_prep, epi_name)
            
            if xgb_result:
                # Fazer previsões
                predictions = forecaster.predict_future_demand(
                    df_train_prep, 
                    epi_name, 
                    len(df_test)
                )
                
                if predictions is not None:
                    # Comparar com valores reais
                    actual_values = df_test['quantity'].values
                    predicted_values = predictions['ensemble_prediction'].values[:len(actual_values)]
                    
                    # Calcular métricas
                    mae = np.mean(np.abs(actual_values - predicted_values))
                    rmse = np.sqrt(np.mean((actual_values - predicted_values) ** 2))
                    mape = np.mean(np.abs((actual_values - predicted_values) / 
                                         (actual_values + 1e-10))) * 100
                    
                    results.append({
                        'iteration': i + 1,
                        'train_start': df_train.iloc[0]['date'],
                        'train_end': df_train.iloc[-1]['date'],
                        'test_start': df_test.iloc[0]['date'],
                        'test_end': df_test.iloc[-1]['date'],
                        'mae': mae,
                        'rmse': rmse,
                        'mape': mape,
                        'actual_mean': np.mean(actual_values),
                        'predicted_mean': np.mean(predicted_values)
                    })
        
        if results:
            results_df = pd.DataFrame(results)
            
            summary = {
                'epi_name': epi_name,
                'num_backtests': len(results),
                'avg_mae': results_df['mae'].mean(),
                'avg_rmse': results_df['rmse'].mean(),
                'avg_mape': results_df['mape'].mean(),
                'mae_std': results_df['mae'].std(),
                'rmse_std': results_df['rmse'].std(),
                'results': results_df
            }
            
            logger.info(f"Backtest concluído para {epi_name}")
            logger.info(f"  MAE médio: {summary['avg_mae']:.2f}")
            logger.info(f"  RMSE médio: {summary['avg_rmse']:.2f}")
            logger.info(f"  MAPE médio: {summary['avg_mape']:.2f}%")
            
            return summary
        
        return None
    
    def compare_forecast_methods(self, df: pd.DataFrame, epi_name: str):
        """
        Compara diferentes métodos de previsão.
        """
        from ML.demand_forecasting import DemandForecasting
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        
        logger.info(f"Comparando métodos de previsão para {epi_name}")
        
        df_epi = df[df['epi_name'] == epi_name].copy()
        df_epi = df_epi.sort_values('date')
        
        if len(df_epi) < 90:
            return None
        
        # Dividir em treino e teste
        train_size = int(len(df_epi) * 0.8)
        df_train = df_epi.iloc[:train_size]
        df_test = df_epi.iloc[train_size:]
        
        forecaster = DemandForecasting()
        df_train_prep = forecaster.prepare_data(
            pd.DataFrame([{'transaction_type': 'saída', 'epi_name': epi_name,
                          'date': row['date'], 'quantity': row['quantity']}
                         for _, row in df_train.iterrows()])
        )
        
        results = {}
        
        # 1. Método Naive (última observação)
        naive_pred = np.full(len(df_test), df_train.iloc[-1]['quantity'])
        results['Naive'] = {
            'predictions': naive_pred,
            'mae': np.mean(np.abs(df_test['quantity'].values - naive_pred)),
            'rmse': np.sqrt(np.mean((df_test['quantity'].values - naive_pred) ** 2))
        }
        
        # 2. Média Móvel (últimos 7 dias)
        ma_pred = np.full(len(df_test), df_train.tail(7)['quantity'].mean())
        results['Moving Average'] = {
            'predictions': ma_pred,
            'mae': np.mean(np.abs(df_test['quantity'].values - ma_pred)),
            'rmse': np.sqrt(np.mean((df_test['quantity'].values - ma_pred) ** 2))
        }
        
        # 3. Exponential Smoothing
        try:
            model_es = ExponentialSmoothing(
                df_train['quantity'],
                trend='add',
                seasonal=None
            )
            fitted_es = model_es.fit()
            es_pred = fitted_es.forecast(len(df_test))
            results['Exponential Smoothing'] = {
                'predictions': es_pred.values,
                'mae': np.mean(np.abs(df_test['quantity'].values - es_pred.values)),
                'rmse': np.sqrt(np.mean((df_test['quantity'].values - es_pred.values) ** 2))
            }
        except:
            logger.warning("Exponential Smoothing falhou")
        
        # 4. XGBoost + Prophet (Ensemble)
        predictions = forecaster.predict_future_demand(
            df_train_prep,
            epi_name,
            len(df_test)
        )
        
        if predictions is not None:
            ensemble_pred = predictions['ensemble_prediction'].values[:len(df_test)]
            results['ML Ensemble'] = {
                'predictions': ensemble_pred,
                'mae': np.mean(np.abs(df_test['quantity'].values - ensemble_pred)),
                'rmse': np.sqrt(np.mean((df_test['quantity'].values - ensemble_pred) ** 2))
            }
        
        # Criar DataFrame comparativo
        comparison = pd.DataFrame({
            method: {'MAE': data['mae'], 'RMSE': data['rmse']}
            for method, data in results.items()
        }).T
        
        comparison['Rank'] = comparison['MAE'].rank()
        comparison = comparison.sort_values('Rank')
        
        return {
            'comparison_table': comparison,
            'results': results,
            'actual_values': df_test['quantity'].values,
            'test_dates': df_test['date'].values
        }
    
    def plot_backtest_results(self, backtest_result: Dict):
        """
        Visualiza os resultados do backtest.
        """
        if not backtest_result or 'results' not in backtest_result:
            return None
        
        results_df = backtest_result['results']
        
        # Criar subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'MAE ao Longo do Tempo',
                'RMSE ao Longo do Tempo',
                'MAPE ao Longo do Tempo',
                'Média Real vs Prevista'
            )
        )
        
        # MAE
        fig.add_trace(
            go.Scatter(
                x=results_df['iteration'],
                y=results_df['mae'],
                mode='lines+markers',
                name='MAE',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # RMSE
        fig.add_trace(
            go.Scatter(
                x=results_df['iteration'],
                y=results_df['rmse'],
                mode='lines+markers',
                name='RMSE',
                line=dict(color='red')
            ),
            row=1, col=2
        )
        
        # MAPE
        fig.add_trace(
            go.Scatter(
                x=results_df['iteration'],
                y=results_df['mape'],
                mode='lines+markers',
                name='MAPE (%)',
                line=dict(color='green')
            ),
            row=2, col=1
        )
        
        # Real vs Previsto
        fig.add_trace(
            go.Scatter(
                x=results_df['actual_mean'],
                y=results_df['predicted_mean'],
                mode='markers',
                name='Previsto vs Real',
                marker=dict(size=10, color='purple')
            ),
            row=2, col=2
        )
        
        # Linha de previsão perfeita
        max_val = max(results_df['actual_mean'].max(), results_df['predicted_mean'].max())
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode='lines',
                name='Previsão Perfeita',
                line=dict(dash='dash', color='gray'),
                showlegend=False
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title=f"Análise de Backtest - {backtest_result['epi_name']}",
            showlegend=True,
            height=800
        )
        
        fig.update_xaxes(title_text="Iteração", row=1, col=1)
        fig.update_xaxes(title_text="Iteração", row=1, col=2)
        fig.update_xaxes(title_text="Iteração", row=2, col=1)
        fig.update_xaxes(title_text="Valor Real Médio", row=2, col=2)
        
        fig.update_yaxes(title_text="MAE", row=1, col=1)
        fig.update_yaxes(title_text="RMSE", row=1, col=2)
        fig.update_yaxes(title_text="MAPE (%)", row=2, col=1)
        fig.update_yaxes(title_text="Valor Previsto Médio", row=2, col=2)
        
        return fig
    
    def plot_method_comparison(self, comparison_result: Dict):
        """
        Visualiza comparação entre métodos de previsão.
        """
        if not comparison_result:
            return None
        
        # Criar figura com subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Comparação de Métricas por Método',
                'Previsões vs Valores Reais'
            ),
            specs=[[{"type": "bar"}], [{"type": "scatter"}]],
            row_heights=[0.4, 0.6]
        )
        
        # Gráfico de barras com métricas
        comparison_table = comparison_result['comparison_table']
        methods = comparison_table.index.tolist()
        
        fig.add_trace(
            go.Bar(
                x=methods,
                y=comparison_table['MAE'],
                name='MAE',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=methods,
                y=comparison_table['RMSE'],
                name='RMSE',
                marker_color='lightcoral'
            ),
            row=1, col=1
        )
        
        # Gráfico de linhas com previsões
        actual_values = comparison_result['actual_values']
        test_dates = comparison_result['test_dates']
        
        # Valores reais
        fig.add_trace(
            go.Scatter(
                x=test_dates,
                y=actual_values,
                mode='lines+markers',
                name='Real',
                line=dict(color='black', width=3)
            ),
            row=2, col=1
        )
        
        # Previsões de cada método
        colors = ['blue', 'green', 'orange', 'red', 'purple']
        for idx, (method, data) in enumerate(comparison_result['results'].items()):
            fig.add_trace(
                go.Scatter(
                    x=test_dates,
                    y=data['predictions'],
                    mode='lines',
                    name=method,
                    line=dict(color=colors[idx % len(colors)], dash='dash')
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title="Comparação de Métodos de Previsão",
            showlegend=True,
            height=900
        )
        
        fig.update_xaxes(title_text="Método", row=1, col=1)
        fig.update_xaxes(title_text="Data", row=2, col=1)
        fig.update_yaxes(title_text="Erro", row=1, col=1)
        fig.update_yaxes(title_text="Quantidade", row=2, col=1)
        
        return fig
    
    def generate_performance_report(self, df: pd.DataFrame, epi_list: List[str]):
        """
        Gera relatório completo de performance para múltiplos EPIs.
        """
        logger.info("Gerando relatório de performance...")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'epis_analyzed': len(epi_list),
            'individual_results': {},
            'summary_statistics': {}
        }
        
        all_maes = []
        all_rmses = []
        all_mapes = []
        
        for epi in epi_list:
            logger.info(f"Analisando {epi}...")
            
            backtest_result = self.backtest_model(df, epi)
            
            if backtest_result:
                report['individual_results'][epi] = {
                    'avg_mae': backtest_result['avg_mae'],
                    'avg_rmse': backtest_result['avg_rmse'],
                    'avg_mape': backtest_result['avg_mape'],
                    'num_tests': backtest_result['num_backtests']
                }
                
                all_maes.append(backtest_result['avg_mae'])
                all_rmses.append(backtest_result['avg_rmse'])
                all_mapes.append(backtest_result['avg_mape'])
        
        # Estatísticas gerais
        if all_maes:
            report['summary_statistics'] = {
                'overall_mae': np.mean(all_maes),
                'overall_rmse': np.mean(all_rmses),
                'overall_mape': np.mean(all_mapes),
                'mae_std': np.std(all_maes),
                'rmse_std': np.std(all_rmses),
                'mape_std': np.std(all_mapes),
                'best_epi': min(report['individual_results'].items(), 
                              key=lambda x: x[1]['avg_mae'])[0],
                'worst_epi': max(report['individual_results'].items(), 
                               key=lambda x: x[1]['avg_mae'])[0]
            }
        
        logger.info("Relatório de performance gerado com sucesso")
        
        return report
    
    def plot_performance_summary(self, report: Dict):
        """
        Visualiza resumo de performance de todos os EPIs.
        """
        if not report or 'individual_results' not in report:
            return None
        
        # Preparar dados
        epis = list(report['individual_results'].keys())
        maes = [report['individual_results'][epi]['avg_mae'] for epi in epis]
        rmses = [report['individual_results'][epi]['avg_rmse'] for epi in epis]
        mapes = [report['individual_results'][epi]['avg_mape'] for epi in epis]
        
        # Criar figura
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=('MAE por EPI', 'RMSE por EPI', 'MAPE (%) por EPI')
        )
        
        # MAE
        fig.add_trace(
            go.Bar(x=epis, y=maes, name='MAE', marker_color='lightblue'),
            row=1, col=1
        )
        
        # RMSE
        fig.add_trace(
            go.Bar(x=epis, y=rmses, name='RMSE', marker_color='lightcoral'),
            row=1, col=2
        )
        
        # MAPE
        fig.add_trace(
            go.Bar(x=epis, y=mapes, name='MAPE', marker_color='lightgreen'),
            row=1, col=3
        )
        
        fig.update_layout(
            title="Resumo de Performance por EPI",
            showlegend=False,
            height=500
        )
        
        fig.update_xaxes(tickangle=-45)
        
        return fig


# Função auxiliar para executar análise completa
def run_complete_analysis(df: pd.DataFrame, epi_name: str):
    """
    Executa análise completa de performance para um EPI.
    """
    analyzer = PerformanceAnalyzer()
    
    results = {
        'backtest': analyzer.backtest_model(df, epi_name),
        'comparison': analyzer.compare_forecast_methods(df, epi_name)
    }
    
    return results
