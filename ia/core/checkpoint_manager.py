"""
Gerenciador de Checkpoints para modelos de IA
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
from modulos.logger import log

class CheckpointManager:
    def __init__(self, base_dir: str):
        """
        Inicializa o gerenciador de checkpoints.
        
        Args:
            base_dir: Diretório base para salvar os checkpoints
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.source_name = "CHECKPOINT_MGR"
        
    def salvar_checkpoint(self, 
                         node_id: str, 
                         modelo: Any, 
                         metricas: Dict[str, Any],
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Salva um checkpoint do modelo com métricas e metadados.
        
        Args:
            node_id: ID do nó de IA
            modelo: O modelo a ser salvo
            metricas: Métricas do modelo
            metadata: Metadados adicionais (opcional)
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Cria diretório específico para este nó
            node_dir = os.path.join(self.base_dir, node_id)
            os.makedirs(node_dir, exist_ok=True)
            
            # Gera nome do checkpoint com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            checkpoint_dir = os.path.join(node_dir, f'checkpoint_{timestamp}')
            os.makedirs(checkpoint_dir)
            
            # Salva o modelo
            modelo_path = os.path.join(checkpoint_dir, 'modelo.pkl')
            modelo.save(modelo_path)
            
            # Salva métricas e metadados
            info = {
                'timestamp': timestamp,
                'metricas': metricas,
                'metadata': metadata or {}
            }
            info_path = os.path.join(checkpoint_dir, 'info.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            
            # Registra no log
            log('IA_MODEL', self.source_name, 
                f"Checkpoint salvo para nó {node_id}",
                details={
                    'checkpoint_dir': checkpoint_dir,
                    'metricas': metricas
                })
            
            return True
            
        except Exception as e:
            log('IA_ERROR', self.source_name, 
                f"Erro ao salvar checkpoint para nó {node_id}: {e}")
            return False
            
    def carregar_ultimo_checkpoint(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Carrega o checkpoint mais recente de um nó.
        
        Args:
            node_id: ID do nó de IA
            
        Returns:
            Dict com o modelo e informações ou None se não encontrar
        """
        try:
            node_dir = os.path.join(self.base_dir, node_id)
            if not os.path.exists(node_dir):
                log('IA_WARN', self.source_name, 
                    f"Nenhum checkpoint encontrado para nó {node_id}")
                return None
                
            # Lista todos os checkpoints
            checkpoints = [d for d in os.listdir(node_dir) 
                         if os.path.isdir(os.path.join(node_dir, d))]
            
            if not checkpoints:
                log('IA_WARN', self.source_name, 
                    f"Nenhum checkpoint encontrado para nó {node_id}")
                return None
                
            # Pega o mais recente
            ultimo_checkpoint = sorted(checkpoints)[-1]
            checkpoint_dir = os.path.join(node_dir, ultimo_checkpoint)
            
            # Carrega modelo e informações
            modelo_path = os.path.join(checkpoint_dir, 'modelo.pkl')
            info_path = os.path.join(checkpoint_dir, 'info.json')
            
            with open(info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
                
            log('IA_MODEL', self.source_name,
                f"Checkpoint carregado para nó {node_id}",
                details={
                    'checkpoint_dir': checkpoint_dir,
                    'info': info
                })
                
            return {
                'modelo_path': modelo_path,
                'info': info
            }
            
        except Exception as e:
            log('IA_ERROR', self.source_name,
                f"Erro ao carregar checkpoint para nó {node_id}: {e}")
            return None
            
    def limpar_checkpoints_antigos(self, 
                                 node_id: str, 
                                 manter_quantidade: int = 5):
        """
        Remove checkpoints antigos, mantendo apenas os N mais recentes.
        
        Args:
            node_id: ID do nó de IA
            manter_quantidade: Quantidade de checkpoints para manter
        """
        try:
            node_dir = os.path.join(self.base_dir, node_id)
            if not os.path.exists(node_dir):
                return
                
            checkpoints = [d for d in os.listdir(node_dir) 
                         if os.path.isdir(os.path.join(node_dir, d))]
            
            if len(checkpoints) <= manter_quantidade:
                return
                
            # Ordena por data e remove os mais antigos
            checkpoints_ordenados = sorted(checkpoints)
            for checkpoint in checkpoints_ordenados[:-manter_quantidade]:
                checkpoint_dir = os.path.join(node_dir, checkpoint)
                shutil.rmtree(checkpoint_dir)
                
            log('IA_INFO', self.source_name,
                f"Checkpoints antigos removidos para nó {node_id}",
                details={
                    'removidos': len(checkpoints) - manter_quantidade,
                    'mantidos': manter_quantidade
                })
                
        except Exception as e:
            log('IA_ERROR', self.source_name,
                f"Erro ao limpar checkpoints antigos do nó {node_id}: {e}")
