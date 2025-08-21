"""
Monitor de Treinamento da IA
---------------------------
Responsável por monitorar e logar o status de treinamento e checkpoints da IA.
"""

import time
from datetime import datetime
from typing import Dict, Any
from modulos.logger import log
import threading
import psutil
import os

class MonitorTreinamento:
    """
    Monitor de treinamento e checkpoints da IA.
    """
    
    def __init__(self, manager, info_treinamento: Dict, status_global: Dict):
        self.source_name = "IA_MONITOR"
        self.manager = manager
        
        # Inicialização segura das estruturas de dados
        self._initialized = False
        
        try:
            # Estrutura para informações de treinamento
            self.info_treinamento = info_treinamento if info_treinamento else manager.dict()
            if not self.info_treinamento:
                self.info_treinamento.update({
                    'modelos_ativos': {},
                    'fila_treinamento': [],
                    'historico_treinamentos': []
                })
            
            # Estrutura para status global
            self.status_global = status_global if status_global else manager.dict()
            if not self.status_global:
                self.status_global.update({
                    'nos_ativos': 0,
                    'acuracia_media': 0.0,
                    'alertas_gerados': 0,
                    'nos': {},
                    'modelos': {},
                    'metricas': {}
                })
                
            self._initialized = True
            
        except Exception as e:
            log('IA_ERROR', self.source_name, f"Erro na inicialização do monitor: {str(e)}")
            
        self.running = True
        
        # Inicia thread de monitoramento
        self.thread_monitor = threading.Thread(
            target=self._thread_monitoramento,
            daemon=True
        )
        self.thread_monitor.start()
        
    def _get_resource_usage(self) -> Dict[str, float]:
        """Obtém uso de recursos do sistema."""
        process = psutil.Process()
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'memory_mb': process.memory_info().rss / 1024 / 1024
        }
        
    def _format_status_treinamento(self) -> str:
        """Formata status atual de treinamento para log."""
        try:
            recursos = self._get_resource_usage()
            info_treinamento = dict(self.info_treinamento)
            status_global = dict(self.status_global)
            
            modelos_ativos = len(info_treinamento.get('modelos_ativos', {}))
            fila = len(info_treinamento.get('fila_treinamento', []))
            historico = len(info_treinamento.get('historico_treinamentos', []))
            
            # Pega detalhes dos modelos ativos
            modelos_info = ""
            if 'modelos_ativos' in info_treinamento:
                for modelo_id, info in info_treinamento['modelos_ativos'].items():
                    if isinstance(info, dict):
                        status = info.get('status', 'N/A')
                        progresso = info.get('progresso', 0)
                        epoca_atual = info.get('epoca_atual', 0)
                        total_epocas = info.get('total_epocas', 0)
                        acuracia = info.get('acuracia', 0.0)
                        modelos_info += f"║ • Modelo {modelo_id}: {status} | Progresso: {progresso}% | Época: {epoca_atual}/{total_epocas} | Acurácia: {acuracia:.2f}%\n"
            
            if not modelos_info:
                modelos_info = "║ Nenhum modelo em treinamento no momento\n"
                
            nos_ativos = status_global.get('nos_ativos', 0)
            alertas = status_global.get('alertas_gerados', 0)
            acuracia = status_global.get('acuracia_media', 0.0)
            
            return f"""
╔═══════════════════════════════════════════════════════════════
║ MONITOR DE TREINAMENTO IA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
╠═══════════════════════════════════════════════════════════════
║ SISTEMA:
║ • CPU: {recursos['cpu_percent']:5.1f}% | RAM: {recursos['memory_mb']:.1f}MB ({recursos['memory_percent']:.1f}%)
║ • Nós Ativos: {nos_ativos} | Alertas: {alertas}
║ • Acurácia Média Global: {acuracia:.2f}%
╟───────────────────────────────────────────────────────────────
║ TREINAMENTO:
║ • Modelos em Treinamento: {modelos_ativos} | Fila: {fila} | Total: {historico}
╟───────────────────────────────────────────────────────────────
║ MODELOS ATIVOS:
{modelos_info}╚═══════════════════════════════════════════════════════════════
"""
        except Exception as e:
            log('IA_ERROR', self.source_name, f"Erro ao formatar status: {str(e)}")
            return None

    def _check_checkpoints(self) -> Dict[str, Any]:
        """Verifica status dos checkpoints."""
        try:
            base_dir = os.path.join("data", "ia", "modelos")  # Usando o diretório padrão do sistema
            checkpoints_dir = os.path.join(base_dir, 'checkpoints')
            
            # Cria o diretório se não existir
            os.makedirs(checkpoints_dir, exist_ok=True)
            
            # Estrutura de retorno padrão
            resultado = {
                'total': 0,
                'ultimo': None,
                'tamanho_total': 0
            }
            
            # Verifica diretórios de checkpoints
            total_checkpoints = 0
            ultimo_checkpoint = None
            tamanho_total = 0
            
            for root, dirs, files in os.walk(checkpoints_dir):
                for file in files:
                    if file.endswith('.checkpoint'):
                        path = os.path.join(root, file)
                        timestamp = os.path.getmtime(path)
                        size = os.path.getsize(path) / 1024  # KB
                        
                        total_checkpoints += 1
                        tamanho_total += size
                        
                        if ultimo_checkpoint is None or timestamp > ultimo_checkpoint.get('timestamp', 0):
                            ultimo_checkpoint = {
                                'arquivo': file,
                                'timestamp': timestamp,
                                'tamanho': size
                            }
            
            resultado['total'] = total_checkpoints
            resultado['ultimo'] = ultimo_checkpoint if ultimo_checkpoint else {'arquivo': 'N/A', 'timestamp': 0, 'tamanho': 0}
            resultado['tamanho_total'] = tamanho_total
            
            return resultado
            
        except Exception as e:
            log('IA_ERROR', self.source_name, f"Erro ao verificar checkpoints: {str(e)}")
            return {
                'total': 0,
                'ultimo': {'arquivo': 'ERROR', 'timestamp': 0, 'tamanho': 0},
                'tamanho_total': 0
            }
        
        return {
            'total': total_checkpoints,
            'ultimo': ultimo_checkpoint,
            'tamanho_total': tamanho_total
        }
        
    def _format_checkpoint_status(self, status: Dict[str, Any]) -> str:
        """Formata status dos checkpoints para log."""
        try:
            if not status:
                return None
                
            ultimo = status.get('ultimo', {})
            if not ultimo:
                ultimo = {'arquivo': 'N/A', 'timestamp': 0, 'tamanho': 0}
                
            try:
                ultimo_data = datetime.fromtimestamp(ultimo.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                ultimo_data = "N/A"
                
            total = status.get('total', 0)
            tamanho_total = status.get('tamanho_total', 0)
            
            return f"""
╔═══════════════════════════════════════════════════════════════
║ MONITOR DE CHECKPOINTS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
╠═══════════════════════════════════════════════════════════════
║ • Total de Checkpoints: {total}
║ • Espaço Utilizado: {tamanho_total/1024:.2f} MB
║ • Último Checkpoint:
║   ◦ Nome: {ultimo.get('arquivo', 'N/A')}
║   ◦ Data: {ultimo_data}
║   ◦ Tamanho: {ultimo.get('tamanho', 0)/1024:.2f} MB
╚═══════════════════════════════════════════════════════════════
"""
        except Exception as e:
            log('IA_ERROR', self.source_name, f"Erro ao formatar status dos checkpoints: {str(e)}")
            return None
        
    def _thread_monitoramento(self):
        """Thread principal de monitoramento."""
        while self.running:
            try:
                # Verifica se as estruturas de dados estão disponíveis
                if not self.info_treinamento or not self.status_global:
                    time.sleep(5)
                    continue
                    
                # Log do status de treinamento
                status_treinamento = self._format_status_treinamento()
                log('INFO', self.source_name, status_treinamento)
                
                # Log do status dos checkpoints
                status_checkpoints = self._check_checkpoints()
                log('INFO', self.source_name, self._format_checkpoint_status(status_checkpoints))
                
                # Espera 1 minuto antes do próximo ciclo
                time.sleep(60)
                
            except Exception as e:
                log('IA_ERROR', self.source_name, f"Erro no monitoramento: {str(e)}")
                time.sleep(5)  # Espera um pouco em caso de erro
                
    def parar(self):
        """Para o monitor de forma segura."""
        self.running = False
        if self.thread_monitor.is_alive():
            self.thread_monitor.join(timeout=5)
