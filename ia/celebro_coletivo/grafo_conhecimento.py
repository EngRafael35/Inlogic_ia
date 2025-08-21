# ia/cerebro_coletivo/grafo_conhecimento.py

from typing import Dict, Any, List, Optional
from multiprocessing import Manager
from datetime import datetime
from modulos.logger import log

class GrafoDeConhecimento:
    """
    Representa o Cérebro Coletivo ou a Memória Global do Ecossistema de IA.
    É um repositório distribuído e seguro para os Nós Cognitivos
    publicarem e consultarem o estado e os insights do ecossistema.
    """
    
    def __init__(self, manager: Manager):
        self.manager = manager
        self.fonte_log = "GRAFO_CONHECIMENTO"
        
        # Mapa em tempo real do estado de cada nó no ecossistema.
        self.estados_dos_nos = self.manager.dict()
        
        # "Quadro de avisos" para descobertas importantes.
        self.insights_compartilhados = self.manager.dict({
            'anomalias': self.manager.list(),
            'correlacoes': self.manager.list(),
            'otimizacoes': self.manager.list(),
        })
        
        # Contador de versão para otimizar consultas futuras.
        self.versao_conhecimento = self.manager.Value('i', 0)
        
        log('SUCCESS', self.fonte_log, "Cérebro Coletivo (Grafo de Conhecimento) inicializado.")

    # --- MÉTODO CORRIGIDO ---
    def registrar_no(self, id_no: str, tipo_no: str):
        """
        Adiciona um novo Nó Cognitivo ao mapa de estados do ecossistema.
        """
        if id_no not in self.estados_dos_nos:
            self.estados_dos_nos[id_no] = self.manager.dict({
                'tipo': tipo_no,
                'saude': 'INICIANDO',
                'metricas': {},
                'ultima_atualizacao': datetime.now().isoformat()
            })
            log('INFO', self.fonte_log, f"Novo nó '{id_no}' registrado no ecossistema.")

    def atualizar_estado_no(self, id_no: str, novo_estado: Dict):
        """
        Atualiza as informações de um nó específico no mapa de estados.
        """
        if id_no in self.estados_dos_nos:
            self.estados_dos_nos[id_no].update(novo_estado)
            self.estados_dos_nos[id_no]['ultima_atualizacao'] = datetime.now().isoformat()
        else:
            log('WARN', self.fonte_log, f"Tentativa de atualizar o estado de um nó não registrado: {id_no}")

    def compartilhar_conhecimento(self, id_no_origem: str, tipo_insight: str, dados: Dict):
        """
        Permite que um nó publique uma nova descoberta no quadro de avisos global.
        """
        if tipo_insight in self.insights_compartilhados:
            insight = {'origem': id_no_origem, 'dados': dados, 'timestamp': datetime.now().isoformat()}
            self.insights_compartilhados[tipo_insight].append(insight)
            self.versao_conhecimento.value += 1
            log('IA_INFO', self.fonte_log, f"Nó '{id_no_origem}' compartilhou novo conhecimento: '{tipo_insight}'.")
        else:
            log('WARN', self.fonte_log, f"Nó '{id_no_origem}' tentou compartilhar um tipo de insight desconhecido: '{tipo_insight}'.")

    def consultar_conhecimento_recente(self, tipo_insight: str, limite: int = 10) -> List:
        """
        Permite que um nó consulte as descobertas mais recentes de outros nós.
        """
        if tipo_insight in self.insights_compartilhados:
            return list(self.insights_compartilhados[tipo_insight])[-limite:]
        return []

    def consultar_estados_dos_nos(self, ids_dos_nos: Optional[List[str]] = None) -> Dict:
        """
        Permite a consulta ao estado de nós específicos ou de todo o ecossistema.
        """
        if ids_dos_nos:
            return {id_no: dict(self.estados_dos_nos.get(id_no, {})) for id_no in ids_dos_nos}
        return {id_no: dict(estado) for id_no, estado in self.estados_dos_nos.items()}