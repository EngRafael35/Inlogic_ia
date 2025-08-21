# ia/nos/no_driver.py
from typing import Dict, Any
from modulos.logger import log
from .no_base import CognitiveNode, PersistentNodeMixin, ActionExecutorMixin, CommunicatorNodeMixin
from ia.motor.motor_aprendizado import MotorDeAprendizado



class NoDriverIA(ActionExecutorMixin, CommunicatorNodeMixin, PersistentNodeMixin, CognitiveNode):
    """Agente Cognitivo final para Drivers."""
    
    def __init__(self, node_id: str, config: Dict, ecosystem_facade: Any):
        super().__init__(node_id, 'driver', config, ecosystem_facade)
        
        # --- INÍCIO DA CORREÇÃO ---
        # Passando os dois argumentos necessários para o motor.
        self.motores['aprendizado_performance'] = MotorDeAprendizado(self.config, self.fonte_log)
        # --- FIM DA CORREÇÃO ---

        log('IA_INFO', self.fonte_log, "Nó de Driver (agente completo) inicializado.")
        
    def _definir_objetivos(self) -> Dict:
        return {'maximizar': ['taxa_sucesso'], 'minimizar': ['latencia_media_ms']}

    def pensar(self, percepcao: Dict) -> (Dict, Dict):
        dados_performance = percepcao.get('dados_limpos')
        features = {
            'latencia': dados_performance.get('latencia_ms', 500),
            'erros': dados_performance.get('erros_ciclo', 0)
        }
        insights = self.motores['aprendizado_performance'].analisar_amostra(features)
        acao_proposta = None
        if insights.get('score_anomalia', 0) > 0.9:
             acao_proposta = {'tipo': 'sugestao_humana', 'descricao': 'Verificar performance do driver'}
        return insights, acao_proposta