# ia/ecossistema_projeto.py

from typing import Dict, Any
from .celebro_coletivo.grafo_conhecimento import GrafoDeConhecimento
from .nos.no_tag import NoTagIA
from .nos.no_driver import NoDriverIA
from .nos.no_processo import NoProcessoIA
from modulos.logger import log

class EcossistemaProjeto:
    """
    Representa uma instância de IA totalmente isolada para um único projeto (fábrica).
    Cada ecossistema tem seu próprio cérebro, nós e ciclo de vida.
    """
    def __init__(self, id_projeto: str, config_projeto: Dict, manager, fachada_ecossistema_geral: Any):
        self.id_projeto = id_projeto
        self.nome_projeto = config_projeto.get('nome_projeto', id_projeto)
        self.config = config_projeto
        self.manager = manager

        self.ecossistema_geral = fachada_ecossistema_geral
        self.fonte = f"ECOSSISTEMA_{self.id_projeto}"
        self.fonte_log = self.fonte  # Adicionado para evitar erro de atributo ausente

        self.nos_ia: Dict[str, Any] = {}

        log('IA_INFO', self.fonte, f"Iniciando ecossistema de IA para o projeto '{self.nome_projeto}'.")

        self.grafo_conhecimento = GrafoDeConhecimento(self.manager)
        self._iniciar_nos_cognitivos_do_projeto()

    def _iniciar_nos_cognitivos_do_projeto(self):
        """Inicia todas as 'células' pertencentes a este organismo."""
        
        mapa_de_nos = {
            'driver': (NoDriverIA, self.config.get('drivers', [])),
            'tag': (NoTagIA, self.config.get('tags', [])),
            'processo': (NoProcessoIA, self.config.get('processos', [])),
        }

        nos_iniciados_com_sucesso = 0
        for tipo_no, (classe_no, configs) in mapa_de_nos.items():
            for config in configs:
                try:
                    id_no = config['id']
                    # Passa a fachada do ecossistema GERAL para que o nó possa interagir com o sistema principal.
                    instancia_no = classe_no(id_no, config, self.ecossistema_geral)
                    
                    self.nos_ia[id_no] = instancia_no
                    self.grafo_conhecimento.registrar_no(id_no, tipo_no)
                    nos_iniciados_com_sucesso += 1
                except Exception as e:
                    log('ERROR', self.fonte, f"Falha ao iniciar nó {tipo_no} {config.get('id', 'SEM_ID')}", details={'erro': str(e)})

        # Adiciona um nó de processo padrão para monitorar a saúde geral do sistema
        id_processo = "processo_saude_geral"
        config_processo = {'id': id_processo, 'nome': f'Monitor Saúde {self.nome_projeto}'}
        try:
            # --- INÍCIO DA CORREÇÃO 2 ---
            # Usa 'self.ecossistema_geral' que é o nome correto do atributo.
            self.nos_ia[id_processo] = NoProcessoIA(id_processo, config_processo, self.ecossistema_geral)
            # --- FIM DA CORREÇÃO 2 ---
            self.grafo_conhecimento.registrar_no(id_processo, 'processo')
            nos_iniciados_com_sucesso += 1
        except Exception as e:
            # A linha de log já usava 'self.fonte' que foi corrigido no __init__
            log('ERROR', self.fonte, "Falha ao iniciar nó de processo padrão", details={'erro': str(e)})

        # A linha abaixo causava o erro final, agora vamos removê-la, pois a
        # contagem global deve ser feita pelo GerenciadorIA.
        # self.global_status['nodes_ativos'] = nos_iniciados_com_sucesso # <<--- REMOVER ESTA LINHA
        
        log('IA_INFO', self.fonte, f"Iniciados e registrados {nos_iniciados_com_sucesso} nós cognitivos neste ecossistema.")
        

    def processar_atualizacao_dados(self, tipo_dado: str, id_alvo: str, dados: Dict):
        """Recebe uma atualização de dados e a direciona para o nó correto DENTRO deste ecossistema."""
        no_alvo = self.nos_ia.get(id_alvo)
        if no_alvo:
            no_alvo.ciclo_cognitivo(dados)
            # Os nós atualizam seu estado no grafo de conhecimento local deste ecossistema.
            self.grafo_conhecimento.atualizar_estado_no(id_alvo, {'metricas': no_alvo.metricas, 'saude': no_alvo.saude})

    def parar(self):
        """Para todos os nós deste ecossistema e salva seus estados."""
        log('IA_INFO', self.fonte_log, "Parando ecossistema do projeto...")
        for no in self.nos_ia.values():
            no.parar()
            if hasattr(no, 'salvar_estado'):
                no.salvar_estado()