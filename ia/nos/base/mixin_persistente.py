# ia/nos/base/mixin_persistente.py
import os
import pickle
import shutil
from typing import Dict
from datetime import datetime
from collections import deque
from modulos.registrador import log

class MixinNoPersistente:
    """
    Mixin que adiciona a habilidade de persistência (salvar/carregar estado)
    a um Nó Cognitivo de forma robusta e atômica.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formato_persistencia = self.config.get('persistencia', {}).get('formato', 'pkl')
        self.caminho_estado = os.path.join(self.diretorios['dados'], f'estado.{self.formato_persistencia}')
        log('IA_INFO', self.fonte_log, "Habilidade de persistência ativada.")
        self.carregar_estado()

    def _get_estado_para_salvar(self) -> Dict:
        """Coleta o estado do nó que precisa ser salvo."""
        estado = {
            'fase_operacional': self.fase_operacional,
            'saude': self.saude,
            'metricas': self.metricas,
            'historico': list(self.historico),
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
            estado_completo = self._get_estado_para_salvar()
            
            with open(caminho_temporario, 'wb') as f:
                pickle.dump(estado_completo, f)
                
            os.replace(caminho_temporario, self.caminho_estado)
            log('IA_DEBUG', self.fonte_log, "Estado do nó salvo com sucesso.")
            self._criar_checkpoint()
        except Exception as e:
            log('IA_ERROR', self.fonte_log, "Falha ao salvar estado", details={'erro': str(e)})

    def carregar_estado(self):
        """Carrega o último estado salvo de forma segura."""
        if not os.path.exists(self.caminho_estado):
            log('IA_INFO', self.fonte_log, "Nenhum estado anterior encontrado, iniciando do zero.")
            return

        try:
            with open(self.caminho_estado, 'rb') as f:
                estado = pickle.load(f)
            self._carregar_do_estado(estado)
            log('IA_INFO', self.fonte_log, "Estado anterior carregado.", details={'timestamp': estado.get('timestamp')})
        except (EOFError, pickle.UnpicklingError):
            log('IA_WARN', self.fonte_log, f"Arquivo de estado corrompido, removendo e iniciando do zero.")
            os.remove(self.caminho_estado)
        except Exception as e:
            log('IA_ERROR', self.fonte_log, "Falha crítica ao carregar estado", details={'erro': str(e)})

    def _criar_checkpoint(self):
        """Cria uma cópia de segurança do arquivo de estado."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho_checkpoint = os.path.join(self.diretorios['checkpoints'], f'estado_{timestamp}.{self.formato_persistencia}')
            shutil.copy2(self.caminho_estado, caminho_checkpoint)
        except Exception as e:
            log('IA_WARN', self.fonte_log, "Falha ao criar checkpoint.", details={'erro': str(e)})