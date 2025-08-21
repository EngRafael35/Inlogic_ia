# ia/nos/no_base.py

"""
A Fundação do Ecossistema Cognitivo InLogic.
Este módulo define a arquitetura base para todos os Agentes de IA (Nós).

Contém:
- CognitiveNode: O "DNA" de um agente, definindo seu ciclo de vida cognitivo.
- PersistentNodeMixin: A "habilidade" de memória de longo prazo (salvar/carregar).
- ActionExecutorMixin: A "habilidade" de interagir com o mundo físico (ex: escrita).
- CommunicatorNodeMixin: A "habilidade" de se comunicar com o cérebro coletivo.
"""
import os
import pickle
import shutil
from typing import Dict, Any
from collections import deque
from datetime import datetime
from modulos.logger import log

# ==============================================================================
# HABILIDADE 1: PERSISTÊNCIA (MEMÓRIA DE LONGO PRAZO)
# ==============================================================================
class PersistentNodeMixin:
    """Habilidade que permite a um nó salvar e carregar seu estado."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formato_persistencia = self.config.get('persistencia_formato', 'pkl')
        self.caminho_estado = os.path.join(self.diretorios['dados'], f'estado.{self.formato_persistencia}')
        log('IA_DEBUG', self.fonte_log, "Habilidade de Persistência ativada.")
        self.carregar_estado()

    def _get_estado_para_salvar(self) -> Dict:
        """Coleta o estado do nó que precisa ser salvo."""
        estado = {
            'fase_operacional': self.fase_operacional, 'saude': self.saude,
            'metricas': self.metricas, 'historico': list(self.historico),
        }
        for nome_motor, motor in self.motores.items():
            if hasattr(motor, 'exportar_estado'):
                estado[f'estado_{nome_motor}'] = motor.exportar_estado()
        return estado

    def _carregar_do_estado(self, estado: Dict):
        """Aplica o estado carregado ao nó."""
        self.fase_operacional = estado.get('fase_operacional', self.fase_operacional)
        self.saude = estado.get('saude', self.saude)
        self.metricas = estado.get('metricas', self.metricas)
        for nome_motor, motor in self.motores.items():
            estado_motor = estado.get(f'estado_{nome_motor}')
            if estado_motor and hasattr(motor, 'importar_estado'):
                motor.importar_estado(estado_motor)

    def salvar_estado(self):
        """Salva o estado atual de forma atômica."""
        try:
            caminho_temporario = self.caminho_estado + ".tmp"
            with open(caminho_temporario, 'wb') as f:
                pickle.dump(self._get_estado_para_salvar(), f)
            os.replace(caminho_temporario, self.caminho_estado)
        except Exception as e:
            log('IA_ERROR', self.fonte_log, "Falha ao salvar estado", details={'erro': str(e)})

    def carregar_estado(self):
        """Carrega o último estado salvo de forma segura."""
        if not os.path.exists(self.caminho_estado): return
        try:
            with open(self.caminho_estado, 'rb') as f:
                estado = pickle.load(f)
            self._carregar_do_estado(estado)
        except Exception as e:
            log('IA_WARN', self.fonte_log, "Não foi possível carregar estado. Iniciando do zero.", details={'erro': str(e)})

# ==============================================================================
# HABILIDADE 2: AÇÃO (INTERAÇÃO COM O MUNDO)
# ==============================================================================
class ActionExecutorMixin:
    """Habilidade que permite a um nó executar ações no mundo real."""

    def _executar_acao_local(self, acao: Dict) -> Dict:
        tipo_acao = acao.get('tipo')
        params = acao.get('params')
        if not all([tipo_acao, params]): return {'status': 'falha', 'motivo': 'formato_invalido'}

        if tipo_acao == 'escrita_tag':
            return self._executar_escrita(params)
        return {'status': 'falha', 'motivo': 'tipo_de_acao_desconhecido'}

    def _executar_escrita(self, params: Dict) -> Dict:
        tag_id, valor = params.get('tag_id'), params.get('valor')
        if not all([tag_id, valor is not None]):
            return {'status': 'falha', 'motivo': 'parametros_invalidos'}
        self.ecossistema.escrever_valor_tag(tag_id, valor)
        return {'status': 'sucesso'}

# ==============================================================================
# HABILIDADE 3: COMUNICAÇÃO (INTERAÇÃO COM OUTROS NÓS)
# ==============================================================================
class CommunicatorNodeMixin:
    """Habilidade que permite a um nó comunicar-se com o ecossistema."""

    def compartilhar_conhecimento(self, tipo_conhecimento: str, dados: Dict):
        """Envia um insight descoberto para o Cérebro Global (KnowledgeGraph)."""
        self.ecossistema.ia_manager.knowledge_graph.compartilhar_conhecimento(self.id, tipo_conhecimento, dados)
    
    def propor_acao_ao_consenso(self, acao: Dict) -> Dict:
        """Envia uma proposta de ação para a rede e aguarda o consenso."""
        log('IA_INFO', self.fonte_log, "Propondo ação para consenso.", details=acao)
        # return self.ecossistema.network.propor_consenso(acao) # Futuro
        return {'status_consenso': 'APROVADO_SIMULADO'}

# ==============================================================================
# O DNA: CLASSE BASE COGNITIVA
# ==============================================================================
class CognitiveNode:
    """
    O DNA de um agente de IA. Define o ciclo de vida e a estrutura
    de pensamento de qualquer nó no ecossistema.
    """
    def __init__(self, node_id: str, node_type: str, config: Dict, ecosystem_facade: Any):
        # 1. IDENTIDADE E CONTEXTO
        self.id = node_id; self.type = node_type; self.config = config if config else {}
        self.name = self.config.get('nome', self.id); self.fonte_log = f"NO_{self.id}"
        self.ecossistema = ecosystem_facade
        # 2. ESTADO E OBJETIVOS
        self.fase_operacional = self.config.get('fase_operacao_inicial', 'MONITORAMENTO')
        self.saude = 'BOM'; self.objetivos = self._definir_objetivos()
        # 3. MEMÓRIA E MÉTRICAS
        self.historico = deque(maxlen=1000); self.metricas = self._inicializar_metricas()
        # 4. MOTORES COGNITIVOS E DIRETÓRIOS
        self.motores = {}; self.diretorios = self._configurar_diretorios()
        
        self.ativo = True
        log('IA_INFO', self.fonte_log, f"Nó Cognitivo '{self.name}' criado.",
            details={'tipo': self.type, 'fase': self.fase_operacional})

    def _configurar_diretorios(self):
        base_dir = os.path.join(r"C:\In Logic", "InLogic IA")
        dirs = {
            'dados': os.path.join(base_dir, 'dados', self.id),
            'modelos': os.path.join(base_dir, 'modelos', self.id),
            'checkpoints': os.path.join(base_dir, 'checkpoints', self.id),
        }
        for path in dirs.values(): os.makedirs(path, exist_ok=True)
        return dirs

    def _inicializar_metricas(self): return {'confianca': 0.5, 'acuracia': 0.0}
    def _definir_objetivos(self): raise NotImplementedError
    def ciclo_cognitivo(self, dados: Dict):
        if not self.ativo: return
        inicio = datetime.now()
        try:
            percepcao = self.perceber(dados)
            insights, acao = self.pensar(percepcao)
            resultado = self.agir(acao, insights)
            self.refletir(insights, resultado)
        except Exception as e:
            log('IA_ERROR', self.fonte_log, "Falha no ciclo cognitivo", details={'erro': str(e)})
        finally:
            self._finalizar_ciclo(dados, inicio)
            
    def perceber(self, dados): return {'dados_limpos': dados}
    def pensar(self, percepcao): raise NotImplementedError
    def agir(self, acao, insights): return self._executar_acao_local(acao) if acao else {'status': 'sem_acao'}
    def refletir(self, insights, resultado): pass
    def _executar_acao_local(self, acao): log('IA_WARN', self.fonte_log, "Habilidade de Ação não herdada."); return {'status': 'falha'}
    def parar(self): self.ativo = False
    def _finalizar_ciclo(self, dados, inicio):
        self.metricas['latencia_ms'] = (datetime.now() - inicio).total_seconds() * 1000
        self.metricas['ultima_atualizacao'] = datetime.now().isoformat()