# ia/nos/no_tag.py
from typing import Any, Dict
from modulos.logger import log
from .no_base import CognitiveNode, PersistentNodeMixin, ActionExecutorMixin, CommunicatorNodeMixin
from ia.motor.motor_aprendizado import MotorDeAprendizado


class NoTagIA(ActionExecutorMixin, CommunicatorNodeMixin, PersistentNodeMixin, CognitiveNode):
    """Agente Cognitivo final para Tags."""
    
    def __init__(self, node_id: str, config: Dict, ecosystem_facade: Any):
        super().__init__(node_id, 'tag', config, ecosystem_facade)

        # --- INÍCIO DA CORREÇÃO ---
        # Agora estamos passando os DOIS argumentos que o motor precisa:
        # 1. A configuração do nó (self.config)
        # 2. A fonte de log do nó (self.fonte_log)
        self.motores['aprendizado'] = MotorDeAprendizado(self.config, self.fonte_log)
        # --- FIM DA CORREÇÃO ---
        
        log('IA_INFO', self.fonte_log, "Nó de Tag (agente completo) inicializado.")
    

    def _definir_objetivos(self) -> Dict:
        return {'maximizar': ['confianca'], 'minimizar': ['score_anomalia']}
    
    def pensar(self, percepcao: Dict) -> (Dict, Dict):
        valor = percepcao.get('dados_limpos', {}).get('valor')
        if not isinstance(valor, (int, float)): return {}, None
        
        features = {'valor': valor}
        valor_real = self.historico[-1]['entrada']['valor'] if self.historico and 'valor' in self.historico[-1]['entrada'] else None
        
        insights = self.motores['aprendizado'].analisar_amostra(features, valor_real)
        acao_proposta = None

        if insights.get('score_anomalia', 0) > 0.95 and self.fase_operacional == 'AUTONOMO':
            self.compartilhar_conhecimento('anomalia_detectada', insights)
            acao_proposta = {'tipo': 'escrita_tag', 'params': {'tag_id': 'tag_alerta', 'valor': 1}}
        
        return insights, acao_proposta