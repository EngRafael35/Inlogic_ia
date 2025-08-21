# ia/nos/base/no_cognitivo.py

from typing import Dict, Any
from collections import deque
from datetime import datetime
from modulos.registrador import log
import os

class NoCognitivo:
    """
    O DNA de um agente de IA no ecossistema. Define o ciclo de vida cognitivo
    e as capacidades fundamentais para qualquer nó (Tag, Driver, Processo).
    """
    def __init__(self, id_no: str, tipo_no: str, config: Dict, fachada_ecossistema: Any):
        # 1. IDENTIDADE E CONTEXTO
        self.id = id_no
        self.tipo = tipo_no
        self.config = config if config else {}
        self.nome = self.config.get('nome', self.id)
        self.fonte_log = f"NO_{self.id}"
        self.ecossistema = fachada_ecossistema

        # 2. ESTADO E OBJETIVOS
        self.fase_operacional = self.config.get('fase_operacional_inicial', 'MONITORAMENTO')
        self.saude = 'INICIANDO'
        self.objetivos = self._definir_objetivos()

        # 3. MEMÓRIA DE CURTO PRAZO E MÉTRICAS
        self.historico = deque(maxlen=self.config.get('tamanho_historico', 1000))
        self.metricas = self._inicializar_metricas()
        
        # 4. DIRETÓRIOS E MOTORES
        self.diretorios = self._configurar_diretorios()
        self.motores = {} # Motores (cérebros) são adicionados pelas subclasses

        self.ativo = True
        log('IA_INFO', self.fonte_log, f"Nó Cognitivo '{self.nome}' criado.",
            details={'tipo': self.tipo, 'fase': self.fase_operacional})

    def _inicializar_metricas(self) -> Dict:
        """Inicializa o dicionário de métricas do nó."""
        return {
            'confianca': 0.5, 'acuracia': 0.0, 'latencia_ms': 0.0, 'erros_ciclo': 0,
            'ultima_atualizacao': None,
        }
    
    def _configurar_diretorios(self):
        """Cria e retorna os diretórios necessários para a persistência do nó."""
        base_dir = os.path.join(r"C:\In Logic", "InLogic IA")
        diretorios = {
            'dados': os.path.join(base_dir, 'dados', self.id),
            'modelos': os.path.join(base_dir, 'modelos', self.id),
            'checkpoints': os.path.join(base_dir, 'checkpoints', self.id),
        }
        try:
            for caminho in diretorios.values():
                os.makedirs(caminho, exist_ok=True)
        except OSError as e:
            log('IA_FATAL', self.fonte_log, f"Não foi possível criar diretórios: {e}")
            raise RuntimeError(f"Falha de permissão para o nó {self.id}: {e}")
        return diretorios

    # --- CICLO DE VIDA DO NÓ ---
    
    def ciclo_cognitivo(self, dados: Dict):
        """O pulsar do nó. Orquestra o fluxo perceber-pensar-agir-refletir."""
        if not self.ativo: return
        
        inicio_ciclo = datetime.now()
        try:
            percepcao = self.perceber(dados)
            insights, acao_proposta = self.pensar(percepcao)
            resultado_acao = self.agir(acao_proposta, insights)
            self.refletir(insights, resultado_acao)
        except Exception as e:
            self.metricas['erros_ciclo'] += 1
            self.saude = 'DEGRADADO'
            log('IA_ERROR', self.fonte_log, "Falha no ciclo cognitivo", details={'erro': str(e)})
        finally:
            self._finalizar_ciclo(dados, inicio_ciclo)

    # --- ESQUELETO DO CICLO COGNITIVO (A SER IMPLEMENTADO NAS SUBCLASSES) ---

    def perceber(self, dados_brutos: Dict) -> Dict:
        """Fase 1: Transformar dados brutos em percepções úteis."""
        log('IA_DEBUG', self.fonte_log, f"Percebendo dados: {dados_brutos}")
        return {'dados_limpos': dados_brutos}

    def pensar(self, percepcao: Dict) -> (Dict, Any):
        """Fase 2: Analisar percepções, gerar insights e decidir uma ação."""
        raise NotImplementedError(f"{self.__class__.__name__} deve implementar o método 'pensar'.")

    def agir(self, acao: Any, insights: Dict) -> Any:
        """Fase 3: Executar a ação proposta ou submetê-la ao consenso."""
        if not acao:
            return {'status': 'sem_acao'}
        
        # Aqui entrará a lógica de consenso. Por agora, executa diretamente.
        return self._executar_acao_local(acao)

    def refletir(self, insights: Dict, resultado_acao: Any):
        """Fase 4: Meta-aprendizado. Avaliar o próprio desempenho e se auto-ajustar."""
        pass # Placeholder

    # --- MÉTODOS A SEREM IMPLEMENTADOS OBRIGATORIAMENTE ---

    def _definir_objetivos(self) -> Dict:
        """Cada subclasse DEVE definir sua função multi-objetivo."""
        raise NotImplementedError(f"{self.__class__.__name__} deve implementar _definir_objetivos")

    def _executar_acao_local(self, acao: Dict) -> Dict:
        """Como o nó executa uma ação aprovada."""
        raise NotImplementedError(f"{self.__class__.__name__} deve implementar _executar_acao_local")

    def parar(self):
        self.ativo = False
        log('IA_INFO', self.fonte_log, "Nó sinalizado para parada.")

    def _finalizar_ciclo(self, dados, inicio_ciclo):
        """Atualiza métricas e histórico ao final do ciclo."""
        latencia = (datetime.now() - inicio_ciclo).total_seconds() * 1000
        self.metricas['latencia_ms'] = (self.metricas.get('latencia_ms', latencia) * 0.9) + (latencia * 0.1) # Média móvel
        self.metricas['ultima_atualizacao'] = datetime.now().isoformat()
        self.historico.append({'entrada': dados, 'timestamp': self.metricas['ultima_atualizacao']})