# ia/nos/no_processo.py
from typing import Dict, Any
from modulos.logger import log
from .no_base import CognitiveNode, PersistentNodeMixin, ActionExecutorMixin, CommunicatorNodeMixin
from ia.motor.motor_aprendizado import MotorDeAprendizado

class NoProcessoIA(ActionExecutorMixin, CommunicatorNodeMixin, PersistentNodeMixin, CognitiveNode):
    """Agente Cognitivo de alto nível, especializado em analisar a saúde e performance de um processo."""
    
    def __init__(self, id_no: str, configuracao: Dict[str, Any], sistema_principal: Any):
        super().__init__(id_no, 'processo', configuracao, sistema_principal)

        # --- INÍCIO DA CORREÇÃO ---
        # Passando os dois argumentos necessários para o motor.
        self.motores['aprendizado_estado'] = MotorDeAprendizado(self.config, self.fonte_log)
        # --- FIM DA CORREÇÃO ---
        
        self.nos_monitorados_ids = self.config.get('nos_associados', [])
        log('IA_INFO', self.fonte_log, "Nó de Processo especializado inicializado.")

    def _definir_objetivos(self):
        return {'maximizar': ['OEE'], 'minimizar': ['tempo_parada']}
    
    def perceber(self, dados):
        estados_filhos = self.ecossistema.ia_manager.knowledge_graph.obter_estados_nos(self.nos_monitorados_ids)
        return {'conhecimento_agregado': estados_filhos}


    def pensar(self, percepcao: Dict) -> (Dict, Dict):
        """
        Analisa os dados de saúde do sistema e os estados de outros nós.
        """
        dados_limpos = percepcao.get('dados_limpos')
        
        metricas_saude = dados_limpos.get('health_metrics', {})
        logs_recentes = dados_limpos.get('recent_logs', [])
        estados_dos_nos = dados_limpos.get('node_states', {})
        
        log('IA_DEBUG', self.fonte_log, "Pensando como Nó de Processo (Saúde do Sistema).")
        
        # Lógica de análise simples:
        cpu = metricas_saude.get('cpu_usage_percent', 0)
        num_erros = len([l for l in logs_recentes if l.get('level') == 'ERROR'])
        
        # Usa o motor de aprendizado para classificar a saúde geral do sistema
        features = {'cpu': cpu, 'erros_recentes': num_erros}
        insights = self.motores['aprendizado_estado'].analisar_amostra(features)
        
        self.metricas.update(insights)
        
        # Lógica de Ação:
        # Se o modelo prever um estado "CRITICO", pode propor uma ação.
        # Por exemplo, reduzir a frequência de polling de algum driver.
        acao_proposta = None
        
        return insights, acao_proposta