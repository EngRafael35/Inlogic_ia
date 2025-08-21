"""
InLogic Studio - Módulo de IA - Gerenciador de Nós
--------------------------------
Este módulo contém a implementação do Gerenciador de Nós para o sistema de IA do InLogic.
Responsável por gerenciar a configuração e o ciclo de vida dos nós de IA.

Funcionalidades principais:
- Carregamento de configurações de nós
- Inicialização e gerenciamento de nós de IA
"""
import os
import sys
# Adiciona o diretório raiz do projeto ao PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from modulos.logger import log

from typing import Dict
from ia.core.no_tag_ia import NoTagIA
from ia.core.no_driver_ia import NoDriverIA
from ia.core.no_processo_ia import NoProcessoIA

class GerenciadorIA:
    """
    Classe responsável por gerenciar os nós de IA no sistema InLogic.
    
    Esta classe é responsável por:
    - Carregar as configurações dos nós de IA a partir dos dados compartilhados
    - Iniciar e gerenciar o ciclo de vida dos nós de IA (tags, drivers, processos)
    - Integrar com o sistema principal para comunicação e controle
    
    A classe espera que as configurações dos nós estejam disponíveis nos dados compartilhados
    sob a chave 'config'. As configurações devem incluir informações sobre os nós de tag,
    driver e processo que devem ser iniciados pelo sistema de IA.
    """

    def __init__(self, shared_data):
        """
        Inicializa o gerenciador de IA.
        
        Args:
            shared_data (multiprocessing.Manager.dict): Dicionário gerenciado que contém
                                                       os dados compartilhados entre processos
        """
        self.shared_data = shared_data
        self.source_name = "IA_MANAGER"  # Identificador para logs
        self.nos_ia = {}  # Armazena referências para os nós de IA (tags, drivers, processos)

    def _carregar_configuracoes_nos(self) -> Dict:
        """Carrega configurações dos nós de IA a partir dos dados compartilhados."""
        nos_config = {
            'tags': [],
            'drivers': [],
            'processos': []  # Manter para futuras expansões
        }
        
        # Acessa a configuração principal através do shared_data
        config_completa = self.shared_data.get('config', {})
        
        if not config_completa:
            log('WARN', self.source_name, "Configuração de projetos não encontrada nos dados compartilhados.")
            return nos_config
            
        for projeto in config_completa.get('projetos', []):
            # Carrega configurações dos drivers
            for driver_config in projeto.get('drivers', []):
                nos_config['drivers'].append(driver_config)
            
            # Carrega configurações das tags
            for tag_config in projeto.get('tags', []):
                nos_config['tags'].append(tag_config)
                
        log('INFO', self.source_name, f"Configurações carregadas para {len(nos_config['drivers'])} drivers e {len(nos_config['tags'])} tags.")
        return nos_config

    def _iniciar_nos_ia(self):
        """Inicia os nós de IA do sistema."""
        try:
            # Recupera configurações dos nós
            configs = self._carregar_configuracoes_nos()
            
            # Passa 'self' como a referência para o sistema_principal
            
            # Inicia nós de tag
            for config in configs.get('tags', []):
                no = NoTagIA(config['id'], config, self) # <-- MUDANÇA AQUI
                self.nos_ia[config['id']] = no
                no.iniciar()
                
            # Inicia nós de driver
            for config in configs.get('drivers', []):
                no = NoDriverIA(config['id'], config, self) # <-- MUDANÇA AQUI
                self.nos_ia[config['id']] = no
                no.iniciar()
                
            # Inicia nós de processo
            for config in configs.get('processos', []):
                no = NoProcessoIA(config['id'], config, self) # <-- MUDANÇA AQUI
                self.nos_ia[config['id']] = no
                no.iniciar()
                
            log('INFO', self.source_name, f'Iniciados {len(self.nos_ia)} nós de IA')
            
        except Exception as e:
            log('ERROR', self.source_name, f'Erro ao iniciar nós de IA: {str(e)}')
            raise

    def parar_nos_ia(self):
        """Para todos os nós de IA em execução."""
        for no_id, no in self.nos_ia.items():
            try:
                no.parar()
                log('INFO', self.source_name, f'Nós de IA {no_id} parado com sucesso.')
            except Exception as e:
                log('ERROR', self.source_name, f'Erro ao parar nó de IA {no_id}: {str(e)}')

    def reiniciar_nos_ia(self):
        """Reinicia todos os nós de IA."""
        self.parar_nos_ia()
        self._iniciar_nos_ia()

    # Métodos adicionais para gerenciamento de nós podem ser adicionados aqui