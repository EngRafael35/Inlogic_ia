"""
InLogic Studio - Sistema Principal
----------------------------------
Este módulo implementa o ponto de entrada do sistema. Permite execução tanto em modo console (background app)
quanto como serviço Windows, alternando facilmente por meio da flag RODAR_COMO_SERVICO.

Principais práticas:
- Inicialização clara e desacoplada do ciclo principal.
- Shutdown seguro e limpo dos subsistemas.
- Logging centralizado e seguro.
- Multiprocessing.Manager utilizado corretamente para recursos compartilhados.
- Código pronto para produção e manutenção industrial.
"""

import sys
import time
from multiprocessing import freeze_support, Manager
from modulos.logger import log

# Imports do service
import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import sys
import traceback

# =========================
# Flag principal de modo de execução
# =========================
RODAR_COMO_SERVICO = True  # Altere para True para rodar como serviço Windows

# =========================
# Importação dos módulos principais
# =========================
from modulos.logger import log
from modulos.sistema import SistemaPrincipal  # Este import não executa o ciclo principal!


def executar_console():
    """
    Executa o sistema principal em modo console/background.
    Permite debug, testes e execução tradicional.
    """
    from multiprocessing import Manager
    with Manager() as manager:
        sistema = SistemaPrincipal(manager)
        try:
            sistema.iniciar_subsistemas()
        except KeyboardInterrupt:
            log('INFO', 'MAIN', "Interrupção recebida, encerrando sistema...")
        except Exception as e:
            log('FATAL', 'MAIN', "Erro fatal irrecuperável.", details={'erro': str(e)})
            import traceback
            traceback.print_exc()
        finally:
            sistema.parar()
            log('INFO', 'MAIN', "Aplicação encerrada.")

def executar_servico_windows():
    """
    Executa o sistema como serviço Windows, utilizando win32serviceutil.
    Permite rodar em background, controlado pelo Service Control Manager.
    """
    # Importa somente aqui para evitar dependência cruzada
    from modulos.win_service import InLogicService
   

    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(InLogicService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(InLogicService)


# =========================
# EntryPoint principal
# =========================
if __name__ == '__main__':

    freeze_support()
    # Comentário: basta alternar a flag acima para escolher o modo!
    if RODAR_COMO_SERVICO:
        executar_servico_windows()  # Manager criado no serviço
    else:
        executar_console()          # Manager criado no main



    def iniciar_subsistemas(self):
        """Centraliza a inicialização de todos os componentes."""

        self.running = True
        sistema = None
        self.iniciar_drivers()
        self.iniciar_servidor_api()
        self.iniciar_distribuidor_ia() # Inicia o Sistema Nervoso
        log('SUCCESS', self.source_name, "Todos os subsistemas foram iniciados.")
        
        self.automatico = sistema.running

        try:
            while self.automatico:
                time.sleep(1)
        except KeyboardInterrupt:
            sistema.running = False
