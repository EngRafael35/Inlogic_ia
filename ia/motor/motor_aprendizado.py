# ia/motores/motor_aprendizado.py

from typing import Dict, Any, Optional
from datetime import datetime
from modulos.logger import log

# --- INÍCIO DA CORREÇÃO ---
# Importa os módulos específicos necessários da biblioteca river
from river import metrics, anomaly
# RandomForests agora estão no módulo 'tree'
from river.tree import HoeffdingTreeRegressor, HoeffdingTreeClassifier
# --- FIM DA CORREÇÃOn ---

class MotorDeAprendizado:
    """
    Motor Cognitivo focado em Aprendizado de Máquina Online (Online ML),
    utilizando a biblioteca River com caminhos de importação atualizados.
    """
    def __init__(self, config_no: Dict, fonte_log: str):
        self.config = config_no
        self.fonte_log = f"{fonte_log}.MotorAprendizado"

        # ARSENAL DE MODELOS ATUALIZADO
        self.modelos = {
            # --- CORREÇÃO: Usa HoeffdingTreeRegressor do módulo 'tree' ---
            'regressor': HoeffdingTreeRegressor(
                grace_period=100, # Número de amostras antes de permitir splits na árvore
                leaf_prediction='adaptive' # Usa um modelo adaptativo nas folhas
            ),
            
            # --- CORREÇÃO: Usa HoeffdingTreeClassifier do módulo 'tree' ---
            'classificador': HoeffdingTreeClassifier(
                grace_period=100
            ),
            
            'anomalia': anomaly.HalfSpaceTrees(
                n_trees=25, 
                height=8, 
                window_size=100, 
                seed=42
            )
        }

        # SISTEMA DE AVALIAÇÃO DE PERFORMANCE
        self.metricas = {'rmse': metrics.RMSE(), 'acuracia': metrics.Accuracy()}
        self.estado = {'amostras_processadas': 0, 'ultima_atualizacao': None, 'performance_atual': {}}
        
        log('IA_INFO', self.fonte_log, "Motor de Aprendizado Online inicializado com sucesso (modelos atualizados).")

    def analisar_amostra(self, features: Dict, valor_real: Optional[Any] = None) -> Dict:
        """
        Processa uma nova amostra de dados, orquestrando o ciclo de
        previsão, aprendizado e avaliação.
        """
        insights = {}
        
        # ETAPA 1: INFERÊNCIA
        try:
            # Não tentamos prever se as features estiverem vazias
            if features:
                insights['previsao_numerica'] = self.modelos['regressor'].predict_one(features)
                insights['previsao_classe'] = self.modelos['classificador'].predict_one(features)
                insights['score_anomalia'] = self.modelos['anomalia'].score_one(features)
                insights['confianca'] = 1.0 - insights.get('score_anomalia', 1.0)
        except Exception as e:
            insights['erro_inferencia'] = str(e)

        # ETAPA 2: APRENDIZADO
        if valor_real is not None and features:
            try:
                valor_numerico = float(valor_real)
                valor_categorico = str(valor_real)

                self.modelos['regressor'].learn_one(features, valor_numerico)
                self.modelos['classificador'].learn_one(features, valor_categorico)
                self.modelos['anomalia'].learn_one(features)

                # ETAPA 3: AVALIAÇÃO DE PERFORMANCE
                if 'previsao_numerica' in insights:
                    self.metricas['rmse'].update(valor_numerico, insights['previsao_numerica'])
                    self.estado['performance_atual']['rmse'] = self.metricas['rmse'].get()
                
                if 'previsao_classe' in insights:
                    self.metricas['acuracia'].update(valor_categorico, insights['previsao_classe'])
                    self.estado['performance_atual']['acuracia'] = self.metricas['acuracia'].get()

                self.estado['amostras_processadas'] += 1

            except (ValueError, TypeError) as e:
                # Se o valor_real não puder ser convertido para float/str
                log('IA_DEBUG', self.fonte_log, "Amostra ignorada para aprendizado devido a tipo de dado inválido.", details={'valor_real': valor_real, 'erro': str(e)})
            except Exception as e:
                log('IA_WARN', self.fonte_log, "Erro durante a etapa de aprendizado.", details={'erro': str(e)})

        self.estado['ultima_atualizacao'] = datetime.now().isoformat()
        return insights

    # Métodos para Persistência (exportar_estado e importar_estado)
    def exportar_estado(self) -> Dict:
        return {'modelos': self.modelos, 'metricas': self.metricas, 'estado_geral': self.estado}

    def importar_estado(self, estado: Dict):
        if estado.get('modelos'): self.modelos = estado['models']
        if estado.get('metricas'): self.metricas = estado['metricas']
        if estado.get('estado_geral'): self.estado = estado['estado_geral']
        log('IA_INFO', self.fonte_log, "Estado de aprendizado importado com sucesso.")