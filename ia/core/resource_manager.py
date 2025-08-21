"""
Gerenciador de recursos e diretórios para modelos de IA
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from modulos.logger import log

class IAResourceManager:
    def __init__(self, base_path: str = None):
        """
        Inicializa o gerenciador de recursos de IA.
        
        Args:
            base_path: Caminho base para os recursos de IA. Se None, usa o diretório padrão.
        """
        self.source_name = "IA_RESOURCE_MGR"
        
        if base_path is None:
            # Cria estrutura padrão na pasta do projeto
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            base_path = os.path.join(project_root, 'ia_resources')
            
        self.base_path = base_path
        self.estrutura_diretorios = {
            'modelos': 'modelos',  # Para modelos treinados
            'dados': 'dados',      # Para dados de treinamento
            'configs': 'configs',  # Para configurações dos modelos
            'checkpoints': 'checkpoints',  # Para checkpoints de treinamento
            'logs': 'logs'        # Para logs específicos de IA
        }
        
        self._inicializar_estrutura()
        
    def _inicializar_estrutura(self):
        """Inicializa a estrutura de diretórios necessária."""
        log('IA_INFO', self.source_name, f"Inicializando estrutura de diretórios em: {self.base_path}")
        
        for dir_name in self.estrutura_diretorios.values():
            dir_path = os.path.join(self.base_path, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                log('IA_INFO', self.source_name, f"Diretório criado: {dir_path}")
            else:
                log('IA_INFO', self.source_name, f"Diretório existente: {dir_path}")
                
    def get_modelo_path(self, node_id: str) -> str:
        """Retorna o caminho para o arquivo do modelo."""
        return os.path.join(self.base_path, 'modelos', f'{node_id}.model')
        
    def get_config_path(self, node_id: str) -> str:
        """Retorna o caminho para o arquivo de configuração."""
        return os.path.join(self.base_path, 'configs', f'{node_id}_config.json')
        
    def get_training_data_path(self, node_id: str) -> str:
        """Retorna o caminho para os dados de treinamento."""
        return os.path.join(self.base_path, 'dados', node_id)
        
    def salvar_config_modelo(self, node_id: str, config: Dict[str, Any]):
        """Salva a configuração de um modelo."""
        try:
            config_path = self.get_config_path(node_id)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            log('IA_INFO', self.source_name, 
                f"Configuração salva para nó {node_id}",
                details={'config_path': config_path})
        except Exception as e:
            log('IA_ERROR', self.source_name, 
                f"Erro ao salvar configuração do nó {node_id}: {e}")
            
    def carregar_config_modelo(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Carrega a configuração de um modelo."""
        try:
            config_path = self.get_config_path(node_id)
            if not os.path.exists(config_path):
                log('IA_WARN', self.source_name, 
                    f"Configuração não encontrada para nó {node_id}")
                return None
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            log('IA_INFO', self.source_name, 
                f"Configuração carregada para nó {node_id}",
                details={'config_path': config_path})
            return config
            
        except Exception as e:
            log('IA_ERROR', self.source_name, 
                f"Erro ao carregar configuração do nó {node_id}: {e}")
            return None
            
    def verificar_dados_treinamento(self, node_id: str) -> Dict[str, Any]:
        """Verifica os dados de treinamento disponíveis."""
        data_path = self.get_training_data_path(node_id)
        resultado = {
            'disponivel': False,
            'arquivos': [],
            'total_dados': 0,
            'ultima_atualizacao': None
        }
        
        try:
            if os.path.exists(data_path):
                arquivos = [f for f in os.listdir(data_path) if f.endswith('.data')]
                if arquivos:
                    resultado.update({
                        'disponivel': True,
                        'arquivos': arquivos,
                        'total_dados': len(arquivos),
                        'ultima_atualizacao': datetime.fromtimestamp(
                            os.path.getmtime(os.path.join(data_path, arquivos[-1]))
                        ).isoformat()
                    })
                    
            log('IA_INFO', self.source_name,
                f"Verificação de dados de treinamento para nó {node_id}",
                details=resultado)
                
        except Exception as e:
            log('IA_ERROR', self.source_name,
                f"Erro ao verificar dados de treinamento do nó {node_id}: {e}")
            
        return resultado
        
    def listar_modelos_disponiveis(self) -> List[str]:
        """Lista todos os modelos disponíveis."""
        modelos_dir = os.path.join(self.base_path, 'modelos')
        modelos = [f.split('.')[0] for f in os.listdir(modelos_dir) 
                  if f.endswith('.model')]
        
        log('IA_INFO', self.source_name,
            f"Modelos disponíveis: {len(modelos)}",
            details={'modelos': modelos})
            
        return modelos
        
    def verificar_estado_modelo(self, node_id: str) -> Dict[str, Any]:
        """Verifica o estado completo de um modelo."""
        estado = {
            'modelo_existe': False,
            'config_existe': False,
            'dados_treinamento': None,
            'ultima_modificacao': None,
            'tamanho_modelo': None
        }
        
        try:
            # Verifica modelo
            modelo_path = self.get_modelo_path(node_id)
            if os.path.exists(modelo_path):
                estado.update({
                    'modelo_existe': True,
                    'ultima_modificacao': datetime.fromtimestamp(
                        os.path.getmtime(modelo_path)
                    ).isoformat(),
                    'tamanho_modelo': os.path.getsize(modelo_path)
                })
                
            # Verifica configuração
            config_path = self.get_config_path(node_id)
            estado['config_existe'] = os.path.exists(config_path)
            
            # Verifica dados de treinamento
            estado['dados_treinamento'] = self.verificar_dados_treinamento(node_id)
            
            log('IA_INFO', self.source_name,
                f"Estado do modelo verificado para nó {node_id}",
                details=estado)
                
        except Exception as e:
            log('IA_ERROR', self.source_name,
                f"Erro ao verificar estado do modelo {node_id}: {e}")
            
        return estado
