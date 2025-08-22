"""
InLogic Studio - Serviço Windows
-------------------------------
Este módulo implementa o serviço do Windows para o sistema InLogic Studio,
utilizando as melhores práticas para robustez, manutenção e shutdown seguro.

Principais pontos:
- Inicialização desacoplada e clara do sistema principal.
- Controle do ciclo de vida pelo atributo de instância, nunca por globals.
- Shutdown limpo e ordenado de todos os subsistemas.
- Utilização correta do multiprocessing.Manager para recursos compartilhados.
- Logging seguro e integrado com o Windows Event Log.
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import logging
import time
import traceback
import threading  # Para rodar iniciar_subsistemas em background

class InLogicService(win32serviceutil.ServiceFramework):
    # Metadados do serviço (nome, exibição e descrição)
    _svc_name_ = "InLogicService"
    _svc_display_name_ = "InLogic Service"
    _svc_description_ = "Serviço de comunicação da In Logic - Software"

    def __init__(self, args):
        """
        Inicializa o serviço Windows (ServiceFramework).
        Não instancia o sistema principal aqui para evitar uso prematuro de recursos.
        """
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)  # Evento para sinalizar parada
        self.running = True  # Flag de ciclo de vida do serviço

        from multiprocessing import Manager
        from sistema import SistemaPrincipal  # Certifique-se que SistemaPrincipal está em sistema.py
        self.manager = Manager()
        self.sistema = SistemaPrincipal(self.manager)

    def SvcStop(self):
        """
        Método chamado pelo Service Control Manager (SCM) ao receber comando de parada.
        Garante shutdown limpo e ordenado do sistema.
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=60000)  # Informa ao Windows que está parando
        self.running = False  # Sinaliza para o loop principal do serviço
        self.sistema.parar()  # Chama o shutdown seguro do sistema principal
        win32event.SetEvent(self.hWaitStop)  # Libera o evento para terminar o serviço
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)  # Informa ao Windows que terminou
        logging.shutdown()  # Finaliza os handlers de log para evitar perda de dados

    def SvcDoRun(self):
        """
        Método chamado pelo SCM ao iniciar o serviço.
        Faz a inicialização e invoca o ciclo principal.
        """
        try:
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING, waitHint=30000)
            servicemanager.LogInfoMsg("InLogicService | Iniciando...")
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            threading.Thread(target=self.sistema.iniciar_subsistemas, daemon=True).start()
            # Loop de ciclo de vida do serviço: fica aguardando até que self.running seja False (parada via SvcStop)
            while self.running:
                time.sleep(5)  # Mantém o serviço vivo; pode adicionar healthchecks/monitoramento aqui
        except Exception as e:
            # Captura e loga qualquer erro fatal, garantindo reporting correto
            erro = "".join(traceback.format_exception(*sys.exc_info()))
            servicemanager.LogErrorMsg(f"InLogicService | Erro fatal:\n{erro}")
            self.SvcStop()
            raise
