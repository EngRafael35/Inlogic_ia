"""
Módulo de Persistência do InLogic ECID.
Responsável pelo gerenciamento de salvamento e recuperação de estados de treinamento.
"""

import os
import json
import pickle
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np
from pathlib import Path

class GerenciadorPersistencia:
    """
    Gerenciador de persistência de dados de treinamento e estados dos IAs.
    Implementa:
    - Salvamento automático de checkpoints
    - Recuperação de estados
    - Versionamento de modelos
    - Backup automático
    """
    
    # Estrutura base de diretórios
    BASE_DIR = "C:\\In Logic\\Treinamentos"
    ESTRUTURA_DIRETORIOS = {
        'nos': {
            'tag': 'nos/tag',
            'driver': 'nos/driver',
            'processo': 'nos/processo'
        },
        'motores': {
            'aprendizado': 'motores/aprendizado',
            'controle': 'motores/controle',
            'seguranca': 'motores/seguranca',
            'otimizacao': 'motores/otimizacao'
        },
        'coordenador': 'coordenador',
        'backup': 'backup'
    }

    def __init__(self):
        """Inicializa o gerenciador de persistência."""
        self._criar_estrutura_diretorios()
        self.meta_info = self._carregar_ou_criar_meta()
        
    def _criar_estrutura_diretorios(self):
        """Cria a estrutura de diretórios se não existir."""
        try:
            # Cria diretório base
            Path(self.BASE_DIR).mkdir(parents=True, exist_ok=True)
            
            # Cria estrutura de subdiretórios
            for categoria, subcats in self.ESTRUTURA_DIRETORIOS.items():
                if isinstance(subcats, dict):
                    for subcategoria, path in subcats.items():
                        Path(os.path.join(self.BASE_DIR, path)).mkdir(parents=True, exist_ok=True)
                else:
                    Path(os.path.join(self.BASE_DIR, subcats)).mkdir(parents=True, exist_ok=True)
                    
        except Exception as e:
            raise Exception(f"Erro ao criar estrutura de diretórios: {str(e)}")

    def _carregar_ou_criar_meta(self) -> Dict:
        """Carrega ou cria arquivo de metadados."""
        meta_path = os.path.join(self.BASE_DIR, 'meta.json')
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._criar_meta_padrao()
        else:
            return self._criar_meta_padrao()

    def _criar_meta_padrao(self) -> Dict:
        """Cria estrutura padrão de metadados."""
        meta = {
            'ultima_atualizacao': datetime.now().isoformat(),
            'versao_sistema': '1.0.0',
            'nos': {
                'tag': {'modelos': {}, 'ultima_sincronizacao': None},
                'driver': {'modelos': {}, 'ultima_sincronizacao': None},
                'processo': {'modelos': {}, 'ultima_sincronizacao': None}
            },
            'motores': {
                'aprendizado': {'estado': {}, 'checkpoints': []},
                'controle': {'estado': {}, 'checkpoints': []},
                'seguranca': {'estado': {}, 'checkpoints': []},
                'otimizacao': {'estado': {}, 'checkpoints': []}
            },
            'coordenador': {'estado': {}, 'configuracoes': {}},
            'estatisticas': {
                'total_atualizacoes': 0,
                'total_recuperacoes': 0,
                'ultimo_backup': None
            }
        }
        self._salvar_meta(meta)
        return meta

    def _salvar_meta(self, meta: Dict):
        """Salva metadados em arquivo."""
        meta_path = os.path.join(self.BASE_DIR, 'meta.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)

    def salvar_estado_no(self, tipo_no: str, id_no: str, estado: Dict[str, Any]) -> bool:
        """
        Salva o estado de um nó específico.
        
        Args:
            tipo_no: Tipo do nó ('tag', 'driver', 'processo')
            id_no: Identificador único do nó
            estado: Estado do nó a ser salvo
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            diretorio = os.path.join(self.BASE_DIR, self.ESTRUTURA_DIRETORIOS['nos'][tipo_no])
            arquivo = os.path.join(diretorio, f'{id_no}.pkl')
            
            # Salva estado
            with open(arquivo, 'wb') as f:
                pickle.dump(estado, f)
            
            # Atualiza metadados
            self.meta_info['nos'][tipo_no]['modelos'][id_no] = {
                'ultima_atualizacao': datetime.now().isoformat(),
                'tamanho': os.path.getsize(arquivo),
                'hash': self._calcular_hash(arquivo)
            }
            self.meta_info['nos'][tipo_no]['ultima_sincronizacao'] = datetime.now().isoformat()
            self.meta_info['estatisticas']['total_atualizacoes'] += 1
            
            self._salvar_meta(self.meta_info)
            return True
            
        except Exception as e:
            print(f"Erro ao salvar estado do nó {tipo_no}/{id_no}: {str(e)}")
            return False

    def recuperar_estado_no(self, tipo_no: str, id_no: str) -> Optional[Dict[str, Any]]:
        """
        Recupera o estado de um nó específico.
        
        Args:
            tipo_no: Tipo do nó ('tag', 'driver', 'processo')
            id_no: Identificador único do nó
            
        Returns:
            Optional[Dict]: Estado do nó ou None se não encontrado
        """
        try:
            arquivo = os.path.join(
                self.BASE_DIR, 
                self.ESTRUTURA_DIRETORIOS['nos'][tipo_no],
                f'{id_no}.pkl'
            )
            
            if not os.path.exists(arquivo):
                return None
                
            with open(arquivo, 'rb') as f:
                estado = pickle.load(f)
                
            self.meta_info['estatisticas']['total_recuperacoes'] += 1
            self._salvar_meta(self.meta_info)
            
            return estado
            
        except Exception as e:
            print(f"Erro ao recuperar estado do nó {tipo_no}/{id_no}: {str(e)}")
            return None

    def salvar_estado_motor(self, tipo_motor: str, estado: Dict[str, Any]) -> bool:
        """
        Salva o estado de um motor cognitivo.
        
        Args:
            tipo_motor: Tipo do motor ('aprendizado', 'controle', etc)
            estado: Estado do motor a ser salvo
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            diretorio = os.path.join(self.BASE_DIR, self.ESTRUTURA_DIRETORIOS['motores'][tipo_motor])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = os.path.join(diretorio, f'estado_{timestamp}.pkl')
            
            # Salva estado
            with open(arquivo, 'wb') as f:
                pickle.dump(estado, f)
            
            # Atualiza metadados
            self.meta_info['motores'][tipo_motor]['estado'] = {
                'arquivo': arquivo,
                'timestamp': datetime.now().isoformat(),
                'tamanho': os.path.getsize(arquivo)
            }
            self.meta_info['motores'][tipo_motor]['checkpoints'].append({
                'arquivo': arquivo,
                'timestamp': datetime.now().isoformat()
            })
            
            # Mantém apenas os últimos 5 checkpoints
            if len(self.meta_info['motores'][tipo_motor]['checkpoints']) > 5:
                checkpoint_antigo = self.meta_info['motores'][tipo_motor]['checkpoints'].pop(0)
                if os.path.exists(checkpoint_antigo['arquivo']):
                    os.remove(checkpoint_antigo['arquivo'])
            
            self._salvar_meta(self.meta_info)
            return True
            
        except Exception as e:
            print(f"Erro ao salvar estado do motor {tipo_motor}: {str(e)}")
            return False

    def recuperar_estado_motor(self, tipo_motor: str) -> Optional[Dict[str, Any]]:
        """
        Recupera o estado mais recente de um motor cognitivo.
        
        Args:
            tipo_motor: Tipo do motor ('aprendizado', 'controle', etc)
            
        Returns:
            Optional[Dict]: Estado do motor ou None se não encontrado
        """
        try:
            estado_info = self.meta_info['motores'][tipo_motor]['estado']
            if not estado_info or not os.path.exists(estado_info['arquivo']):
                return None
                
            with open(estado_info['arquivo'], 'rb') as f:
                estado = pickle.load(f)
                
            self.meta_info['estatisticas']['total_recuperacoes'] += 1
            self._salvar_meta(self.meta_info)
            
            return estado
            
        except Exception as e:
            print(f"Erro ao recuperar estado do motor {tipo_motor}: {str(e)}")
            return None

    def criar_backup(self) -> bool:
        """
        Cria um backup completo do sistema.
        
        Returns:
            bool: Sucesso da operação
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(self.BASE_DIR, 'backup', f'backup_{timestamp}')
            
            # Cria diretório de backup
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copia todos os arquivos exceto a pasta de backup
            for item in os.listdir(self.BASE_DIR):
                if item != 'backup':
                    s = os.path.join(self.BASE_DIR, item)
                    d = os.path.join(backup_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
            
            # Atualiza metadados
            self.meta_info['estatisticas']['ultimo_backup'] = datetime.now().isoformat()
            self._salvar_meta(self.meta_info)
            
            return True
            
        except Exception as e:
            print(f"Erro ao criar backup: {str(e)}")
            return False

    def restaurar_backup(self, timestamp: str) -> bool:
        """
        Restaura um backup específico.
        
        Args:
            timestamp: Timestamp do backup a ser restaurado
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            backup_dir = os.path.join(self.BASE_DIR, 'backup', f'backup_{timestamp}')
            if not os.path.exists(backup_dir):
                return False
                
            # Remove diretórios atuais (exceto backup)
            for item in os.listdir(self.BASE_DIR):
                if item != 'backup':
                    path = os.path.join(self.BASE_DIR, item)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
            
            # Restaura do backup
            for item in os.listdir(backup_dir):
                s = os.path.join(backup_dir, item)
                d = os.path.join(self.BASE_DIR, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            
            # Recarrega metadados
            self.meta_info = self._carregar_ou_criar_meta()
            
            return True
            
        except Exception as e:
            print(f"Erro ao restaurar backup: {str(e)}")
            return False

    def _calcular_hash(self, arquivo: str) -> str:
        """Calcula hash de um arquivo."""
        import hashlib
        hasher = hashlib.sha256()
        with open(arquivo, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    def limpar_dados_antigos(self, dias: int = 30) -> bool:
        """
        Remove dados mais antigos que o número de dias especificado.
        
        Args:
            dias: Número de dias para manter dados
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            limite = datetime.now().timestamp() - (dias * 24 * 60 * 60)
            
            # Limpa backups antigos
            backup_dir = os.path.join(self.BASE_DIR, 'backup')
            if os.path.exists(backup_dir):
                for item in os.listdir(backup_dir):
                    path = os.path.join(backup_dir, item)
                    if os.path.getctime(path) < limite:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
            
            # Atualiza metadados
            self._salvar_meta(self.meta_info)
            
            return True
            
        except Exception as e:
            print(f"Erro ao limpar dados antigos: {str(e)}")
            return False
