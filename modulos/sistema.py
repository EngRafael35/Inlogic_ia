# sistema.py

"""
InLogic Studio - Sistema Principal
--------------------------------
Este módulo contém a implementação principal do sistema de supervisão InLogic.
Responsável por gerenciar drivers, comunicação entre processos e interface do usuário.

Funcionalidades principais:
- Gerenciamento de drivers de comunicação
- Sistema de logging
- Criptografia de configurações
- Monitoramento em tempo real
- API de comunicação
- Sistema de escrita em tags
"""


import json
import time
import sys
import psutil
import multiprocessing
from multiprocessing import freeze_support
import os
import threading


# Adiciona o diretório raiz do projeto ao PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from servidor.servidor import ServidorAPI

# Configuração do sistema de cores para console
# Usa colorama para dar suporte a cores em diferentes terminais
try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)  # Autoreset evita que as cores "vazem" entre prints
    CORES_ATIVAS = True
except ImportError:
    # Fallback para quando colorama não está disponível
    # Cria classes vazias para evitar erros quando colorama não está instalado
    class Fore: pass
    class Style: pass
    class Back: pass
    Fore.GREEN = Fore.YELLOW = Fore.RED = Fore.CYAN = Fore.MAGENTA = Fore.WHITE = ''
    Style.BRIGHT = Style.RESET_ALL = ''
    Back.RED = ''
    CORES_ATIVAS = False

# Importação do sistema de logging personalizado
from modulos.logger import log

class MockDriverProcess(multiprocessing.Process):
    """
    Driver mock para testes ou quando o driver real não está disponível.
    Usado como fallback quando um driver específico não pode ser carregado.
    
    Este processo simula um driver real mas não faz nenhuma comunicação real.
    Útil para desenvolvimento, testes e diagnóstico do sistema.
    """
    def __init__(self, **kwargs):
        """
        Inicializa o driver mock.
        
        Args:
            **kwargs: Argumentos que seriam passados para um driver real
                     (driver_config, tags_config, etc.)
        """
        super().__init__()
        self.kwargs = kwargs
        
    def run(self):
        """
        Simula a execução de um driver real.
        Apenas imprime uma mensagem e mantém o processo vivo.
        """
        print(f"Mock Driver {self.kwargs.get('driver_config',{}).get('nome')} iniciado.")
        time.sleep(999)  # Mantém o processo vivo

# Sistema de Criptografia
# ----------------------
# Implementa a criptografia AES para proteção das configurações do sistema
from base64 import b64decode
try:
    # PyCryptodome para criptografia AES
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    CRIPTOGRAFIA_DISPONIVEL = True
except ImportError:
    # Se PyCryptodome não estiver instalado, desativa a criptografia
    CRIPTOGRAFIA_DISPONIVEL = False
# ... (resto do seu código de criptografia mantido)
CHAVE_SECRETA = b"inlogic18366058".ljust(32, b'0')

def descriptografar_json(conteudo_criptografado):
    # ... (seu código mantido)
    if not CRIPTOGRAFIA_DISPONIVEL:
        log('ERROR', 'MAIN', "Biblioteca 'pycryptodome' não instalada. Não é possível descriptografar.")
        sys.exit(1)
    dados = b64decode(conteudo_criptografado)
    iv = dados[:16]
    dados_encriptados = dados[16:]
    cipher = AES.new(CHAVE_SECRETA, AES.MODE_CBC, iv)
    dados_descriptografados = unpad(cipher.decrypt(dados_encriptados), AES.block_size)
    return json.loads(dados_descriptografados.decode('utf-8'))

CONFIG_FILE = r'C:\In Logic\Setup ativos\Setup.cfg'

class SistemaPrincipal:

    """
    Classe principal que orquestra todo o sistema InLogic.
    
    Esta classe é o coração do sistema, responsável por:
    - Gerenciamento do ciclo de vida dos drivers
    - Gerenciamento da comunicação entre processos
    - Monitoramento de tags em tempo real
    - Interface com o usuário via console
    - Gerenciamento das configurações do sistema
    - Controle do servidor API
    
    A classe usa multiprocessing.Manager para compartilhar dados entre processos,
    garantindo comunicação segura e eficiente entre os componentes do sistema.
    """

    def __init__(self, manager):
        """
        Inicializa o sistema principal.
        
        Args:
            manager (multiprocessing.Manager): Gerenciador de recursos compartilhados
                                             entre processos
        
        O construtor configura:
        - Estruturas de dados compartilhadas
        - Carregamento de configurações
        - Mapeamento de tags
        - Preparação para drivers
        """
        self.source_name = "MAIN"  # Identificador para logs
        self.manager = manager     # Gerenciador de recursos compartilhados
        self.config = self._carregar_configuracao()
        
        # Estruturas compartilhadas entre processos
        self.shared_driver_data = self.manager.dict()  # Dados dos drivers
        self.write_queues = self.manager.dict()        # Filas de escrita
        self.driver_processes = []                      # Lista de processos
        
        # Mapa de tags -> drivers (compartilhado)
        # Mantém o relacionamento entre tags e seus drivers
        self.tag_map = self.manager.dict()
        self._popular_mapa_de_tags()
        
        # Sistema de IA e Fases
        log('INFO', self.source_name, "Iniciando sistema de IA...")
        try:
            # CORREÇÃO DO IMPORT
            from ia.gerenciador import GerenciadorIA
            # Neste ponto, o GerenciadorIA deve carregar os checkpoints existentes.
            log('INFO', self.source_name, "Carregando estado e modelos do sistema de IA (checkpoints)...")
            self.ia_manager = GerenciadorIA(manager, self.config, self)
            log('INFO', self.source_name, "Sistema de IA inicializado com sucesso")
        except Exception as e:
            log('ERROR', self.source_name, f"Erro ao inicializar sistema de IA: {e}")
            raise
        
        # Servidor API (iniciado sob demanda)
        self.servidor_api = None

        self.running = False  # Flag para controlar o ciclo de vida das threads
        self.distributor_thread = None
        self.last_processed_data = self.manager.dict()

    def _carregar_configuracao(self):
        """
        Carrega, descriptografa e valida a configuração do sistema.
        Adiciona campos faltantes com valores default.
        """
        from modulos.configuracao_utils import validar_e_completar_config, log_campos_faltantes
        
        log('INFO', self.source_name, f"Carregando configuração de '{CONFIG_FILE}'...")
        try:
            # 1. Lê e descriptografa o arquivo
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                conteudo_criptografado = f.read()
            config = descriptografar_json(conteudo_criptografado)
            
            # 2. Valida e completa a configuração
            config = validar_e_completar_config(config)
            
            # 3. Loga campos opcionais faltantes
            log('INFO', self.source_name, "Verificando campos opcionais da configuração...")
            log_campos_faltantes(config)
            
            return config
            
        except FileNotFoundError:
            log('ERROR', self.source_name, f"Arquivo de configuração '{CONFIG_FILE}' não encontrado.")
            sys.exit(1)
        except Exception as e:
            log('ERROR', self.source_name, f"Erro ao processar arquivo de configuração: {e}")
            sys.exit(1)

    def iniciar_subsistemas(self):
        """NOVO MÉTODO: Centraliza a inicialização de todos os componentes."""
        self.running = True
        self.iniciar_drivers()
        self.iniciar_servidor_api()
        self.iniciar_distribuidor_ia() # Inicia o Sistema Nervoso
        log('SUCCESS', self.source_name, "Todos os subsistemas foram iniciados.")      

        # Loop de ciclo de vida do serviço: fica aguardando até que self.running seja False (parada via SvcStop)
        while self.running:
            time.sleep(5)  # Mantém o serviço vivo; pode adicionar healthchecks/monitoramento aqui

    def iniciar_drivers(self):
        # ... (seu código mantido, mas com uma correção crucial)
        log('INFO', self.source_name, "Iniciando processos dos drivers...")
        if 'projetos' not in self.config:
            log('WARN', self.source_name, "Nenhum projeto encontrado na configuração.")
            return

        for projeto in self.config['projetos']:
            for driver_config in projeto.get('drivers', []):
                driver_id = driver_config['id']
                tags_para_este_driver = [
                    tag for tag in projeto.get('tags', []) if tag.get('id_driver') == driver_id
                ]

                # **CORREÇÃO CRUCIAL**
                # Crie a fila e o sub-dicionário ANTES de iniciar o processo
                write_queue = self.manager.Queue()
                self.write_queues[driver_id] = write_queue
                
                # Prepara o estado inicial do driver com informações de fase
                self.shared_driver_data[driver_id] = self.manager.dict({
                    "status_conexao": "iniciando",
                    "detalhe": "Processo sendo criado.",
                    "config": driver_config,
                    "tags": self.manager.dict(),
                    "fase_atual": driver_config.get('fase_operacao', 'MONITORAMENTO'),
                    "modo_operacao": driver_config.get('modo_operacao', 'normal'),
                    "restricoes": driver_config.get('restricoes', {}),
                    "ultima_atualizacao": time.strftime("%Y-%m-%d %H:%M:%S")
                })

                tipo_driver = driver_config.get('tipo', '').lower()
                ProcessoClasse = None

                try:

                    # Verifica tipo de driver Controllogix
                    if tipo_driver == 'controllogix':
                        from driver.controllogix_driver_process import controllogixDriverProcess as ProcessoClasse
                    # Verifica tipo de driver Modbus
                    elif tipo_driver in ['modbus_tcp', 'modbus']:
                        from driver.mqtt_driver_process import ModbusDriverProcess as ProcessoClasse
                    # Verifica tipo de driver MQTT
                    elif tipo_driver == 'mqtt':
                        from driver.mqtt_driver_process import MQTTDriverProcess as ProcessoClasse
                    # Verifica tipo de driver SQL
                    elif tipo_driver == 'sql':
                        from driver.sql_driver_process import SQLDriverProcess as ProcessoClasse                                                
               
                except ImportError:
                     log('WARN', self.source_name, f"Não foi possível importar a classe para o driver '{tipo_driver}'.")

                if ProcessoClasse is None:
                    ProcessoClasse = MockDriverProcess
                    log('WARN', self.source_name, f"Classe de driver para '{tipo_driver}' não encontrada. Usando Mock.")

                # Passe os objetos compartilhados DIRETAMENTE
                processo = ProcessoClasse(
                    driver_config=driver_config,
                    tags_config=tags_para_este_driver,
                    shared_data=self.shared_driver_data,
                    write_queue=write_queue # Passa a fila específica
                )
                self.driver_processes.append(processo)
                processo.start()


    def _exibir_status_periodicamente(self):
        # ... (seu código mantido, mas com cópias para segurança)
        HEADER = f"{Style.BRIGHT}{Fore.YELLOW}"
        DRIVER_OK = f"{Style.BRIGHT}{Fore.GREEN}"
        DRIVER_FAIL = f"{Style.BRIGHT}{Fore.RED}"
        TAG_NAME = Fore.CYAN
        TAG_VALUE = Fore.WHITE
        RESET = Style.RESET_ALL

        print("\n" * 2)
        print(HEADER + "╔" + "═" * 78 + "╗")
        print(HEADER + f"║ {'PAINEL DE STATUS DO SISTEMA':^76} ║")
        print(HEADER + f"║ {time.strftime('%Y-%m-%d %H:%M:%S'):^76} ║")
        
        # Status do Sistema de IA
        if self.ia_manager:
            IA_STATUS = "ATIVO"
            IA_COLOR = DRIVER_OK
        else:
            IA_STATUS = "INATIVO"
            IA_COLOR = DRIVER_FAIL
        print(HEADER + f"║ {'STATUS DO SISTEMA DE IA: ' + IA_COLOR + IA_STATUS + HEADER:^76} ║")
        
        print(HEADER + "╚" + "═" * 78 + "╝")

        try:
            # Iterar sobre uma cópia das chaves para segurança
            for driver_id in list(self.shared_driver_data.keys()):
                data = self.shared_driver_data.get(driver_id, {})
                # Usar cópias locais para evitar problemas de concorrência durante o print
                data_copy = dict(data)
                nome_driver = data_copy.get('config', {}).get('nome', 'N/A')
                status = data_copy.get('status_conexao', 'desconhecido')
                detalhe = data_copy.get('detalhe', '')

                if status == 'conectado': status_color, status_icon = DRIVER_OK, "✔"
                else: status_color, status_icon = DRIVER_FAIL, "✖"

                print(f"\n{status_color}▶ DRIVER: {nome_driver} (ID: {driver_id})")
                print(f"  Status: {status_icon} {status.upper()} - {detalhe}")
                
                tags_data = dict(data_copy.get('tags', {}))
                if not tags_data:
                    print(f"    {Fore.YELLOW}Nenhuma tag reportada ainda.")
                else:
                    print(f"  {Style.BRIGHT}{'TAG':<30} {'VALOR':<20} {'QUALIDADE'}")
                    print(f"  {'-'*29} {'-'*19} {'-'*15}")
                    for tag_id, tag_info in tags_data.items():
                        nome_tag = tag_info.get('nome', 'N/A')
                        valor = tag_info.get('valor', 'N/D')
                        qualidade = tag_info.get('qualidade', 'N/D')
                        qualidade_color = Fore.GREEN if qualidade == 'boa' else Fore.RED
                        print(f"    {TAG_NAME}{nome_tag:<28}{RESET} {TAG_VALUE}{str(valor):<18}{RESET} {qualidade_color}{qualidade}{RESET}")
        except Exception as e:
            print(f"\n{Back.RED}{Fore.WHITE} ERRO AO EXIBIR STATUS: {e} {RESET}\n")

    def monitorar(self):
        # ... (seu código mantido)
        log('INFO', self.source_name, "Sistema em modo de monitoramento.")
        try:
            while True:
                self._exibir_status_periodicamente()
                time.sleep(100)
                #teste de escrita
                #self.escrever_valor_tag(f"tag_3ab559fa", "555")
        except Exception as e:
            log('INFO', self.source_name, f"erro ao monitorar drivers: {e}")
            return

    def iniciar_distribuidor_ia(self):
            """Inicia a thread que atua como o Sistema Nervoso, distribuindo dados para a IA."""
            self.distributor_thread = threading.Thread(target=self._thread_distribuicao_ia, daemon=True)
            self.distributor_thread.start()


    def _thread_distribuicao_ia(self):
        """
        O Sistema Nervoso do Ecossistema InLogic ECID.

        Esta thread opera em background como o principal distribuidor de informações.
        Sua função é continuamente observar o estado do mundo físico (dados dos drivers)
        e a saúde do próprio sistema (métricas de processo), e entregar essas
        "sensações" para os Nós Cognitivos apropriados para que eles possam
        perceber, pensar e agir.

        Este processo é projetado para ser robusto e contínuo, garantindo que
        o fluxo de consciência da IA nunca seja interrompido por falhas pontuais.
        """
        log('INFO', 'SISTEMA_NERVOSO_IA', "Ativado. Monitorando o fluxo de dados para os cérebros da IA.")
        
        while self.running:
            try:
                # Intervalo entre os "pulsos" do sistema nervoso. É configurável.
                # Um valor mais baixo dá mais responsividade, um valor mais alto economiza CPU.
                intervalo = self.config.get('ia_distribution_interval_s', 2.0)
                time.sleep(intervalo)
                
                if not hasattr(self, 'ia_manager'):
                    # Aguarda a IA estar pronta, evitando erros durante a inicialização.
                    continue

                # --- FLUXO 1 e 2: SENSAÇÕES DO MUNDO EXTERNO (Tags e Drivers) ---
                # Esta seção lê os dados que os processos de driver coletaram.
                self._distribuir_dados_dos_drivers()
                
                # --- FLUXO 3: CONSCIÊNCIA DO PRÓPRIO CORPO (Saúde do Sistema) ---
                # Esta seção coleta e distribui dados sobre a saúde do software InLogic em si.
                self._distribuir_dados_de_saude_do_sistema()

            except Exception as e:
                # Captura qualquer erro inesperado no loop principal para que a thread nunca morra.
                log('ERROR', 'SISTEMA_NERVOSO_IA', "Erro crítico no loop de distribuição", details={'erro': str(e)})

        log('INFO', 'SISTEMA_NERVOSO_IA', "Thread de distribuição de dados encerrada de forma limpa.")

    def _distribuir_dados_dos_drivers(self):
        """
        Coleta dados dos drivers de comunicação e os roteia para os Nós
        Cognitivos de Tag e Driver correspondentes.
        """
        dados_drivers_atuais = dict(self.shared_driver_data)
        
        for driver_id, driver_data in dados_drivers_atuais.items():
            # 1. Roteia DADOS DE PERFORMANCE para o Nó de Driver.
            # Este pacote de dados é sobre a SAÚDE da comunicação (status, latência, etc.).
            dados_performance_driver = {k: v for k, v in driver_data.items() if k != 'tags'}
            if self.last_processed_data.get(driver_id) != dados_performance_driver:
                self.ia_manager.processar_atualizacao_dados('driver', driver_id, dict(dados_performance_driver))
                self.last_processed_data[driver_id] = dados_performance_driver
            
            # 2. Roteia DADOS DE VALOR para os Nós de Tag.
            # Estes são os dados brutos coletados dos sensores.
            tags_atuais = dict(driver_data.get('tags', {}))
            for tag_id, tag_data in tags_atuais.items():
                if self.last_processed_data.get(tag_id) != tag_data:
                    # Incluímos o 'id_driver' para que o GerenciadorIA possa rotear para o ecossistema correto.
                    if 'id_driver' not in tag_data:
                         tag_data['id_driver'] = driver_id # Garante que o "CEP" esteja presente.
                    self.ia_manager.processar_atualizacao_dados('tag', tag_id, dict(tag_data))
                    self.last_processed_data[tag_id] = tag_data

    def _distribuir_dados_de_saude_do_sistema(self):
        """
        Coleta métricas de saúde do processo principal (CPU, RAM) e logs,
        e os envia aos Nós de Processo para uma análise de alto nível.
        """
        try:
            # Obtém dados de performance do processo principal.
            processo_main = psutil.Process(os.getpid())
            dados_saude = {
                'cpu_uso_percent': psutil.cpu_percent(interval=None),
                'memoria_uso_mb': processo_main.memory_info().rss / (1024 * 1024),
                'threads_ativas': threading.active_count()
            }
            
            # Acessa os logs mais recentes do buffer de log global.
            from modulos.logger import get_recent_logs
            logs_recentes = get_recent_logs(20) # Pega os últimos 20 logs.

            # Monta o pacote de dados final para os Nós de Processo.
            pacote_de_consciencia_situacional = {
                'metricas_saude': dados_saude,
                'logs_recentes': logs_recentes
            }
            
            # A responsabilidade de saber quais Nós de Processo existem é do GerenciadorIA.
            # O Sistema Nervoso apenas entrega a "sensação" de saúde para a camada de IA.
            # Um ID genérico é usado, e o IAManager o roteará para todos os Nós de Processo interessados.
            id_no_processo_generico = "sistema_geral"
            self.ia_manager.processar_atualizacao_dados('processo', id_no_processo_generico, pacote_de_consciencia_situacional)

        except Exception as e:
            # Não permite que uma falha na coleta de métricas de saúde pare a distribuição
            # de dados de tag/driver.
            log('WARN', 'SISTEMA_NERVOSO_IA', "Não foi possível coletar e distribuir dados de saúde do sistema.", details={'erro': str(e)})

    def parar_drivers(self):
        """
        Para todos os processos de driver de forma forçada, garantindo que
        nenhum processo filho fique órfão.
        """
        log('INFO', self.source_name, "Parando todos os processos de driver...")
        for processo in self.driver_processes:
            if processo.is_alive():
                processo.terminate()
                processo.join(timeout=3)
                if processo.is_alive():
                    # Como último recurso, se o terminate não funcionar
                    processo.kill()
                    log('WARN', self.source_name, f"Processo {processo.pid} forçado a encerrar (kill).")
        self.driver_processes = [] # Limpa a lista de processos
        log('INFO', self.source_name, "Todos os processos de driver foram encerrados.")

    # --- 2. O MÉTODO 'parar_servidor_api' também continua o mesmo ---
    def parar_servidor_api(self):
        """Para o servidor da API de forma limpa."""
        if self.servidor_api and self.servidor_api.is_alive():
            try:
                log('INFO', self.source_name, "Desligando servidor API...")
                self.servidor_api.shutdown()
            except Exception as e:
                log('WARN', self.source_name, f"Erro ao tentar desligar o servidor API de forma limpa: {e}")
                
    # --- 3. O MÉTODO 'parar' centraliza a lógica de desligamento ---
    def parar(self):
        """
        Para todos os subsistemas de forma organizada e limpa, garantindo a
        ordem correta de desligamento.
        """
        log('INFO', self.source_name, "Iniciando processo de parada do sistema...")
        self.running = False  # Sinaliza para todas as threads em loop pararem

        # 1. Para a API primeiro para não aceitar novas requisições
        self.parar_servidor_api()
        
        # 2. Para os drivers que estão coletando dados
        self.parar_drivers()

        # 3. Para o sistema de IA e salva seu estado final
        if self.ia_manager and hasattr(self.ia_manager, 'parar'):
            log('INFO', self.source_name, "Salvando estado final da IA...")
            self.ia_manager.parar()
            
        log('SUCCESS', self.source_name, "Sistema completo parado com sucesso.")

    # --- 4. O MÉTODO 'reinicializar_sistema' é mantido para ser chamado via API ---
    def reinicializar_sistema(self):
        """
        Reinicializa o sistema de forma segura, recarregando a configuração
        e reiniciando os drivers e a IA.
        """
        log('INFO', self.source_name, "--- INICIANDO REINICIALIZAÇÃO COMPLETA DO SISTEMA ---")
        
        # 1. Para os componentes atuais
        self.running = False # Para a thread do distribuidor
        # É uma boa prática esperar a thread do distribuidor terminar
        if hasattr(self, 'distributor_thread') and self.distributor_thread.is_alive():
            self.distributor_thread.join(timeout=2)
            
        self.parar_drivers()
        # Não paramos a API, pois ela que recebeu o comando
        
        # Não paramos o IAManager, apenas o reconfiguramos se necessário ou o recriamos.
        # Vamos optar por recriá-lo para garantir um estado limpo.
        
        # 2. Recarrega a configuração
        self.config = self._carregar_configuracao()

        # 3. Limpa e reinicia as estruturas de dados
        # O Manager do multiprocessing não permite limpar os dicts facilmente,
        # por isso a melhor prática é recriar o IAManager
        self.shared_driver_data.clear()
        self.write_queues.clear()
        self.tag_map.clear()
        self.last_processed_data.clear()

        # 4. Repopula o mapa de tags com a nova configuração
        self._popular_mapa_de_tags()
        
        # 5. Reinicia a IA com a nova configuração
        log('INFO', self.source_name, "Reinicializando sistema de IA...")
        try:
            from ia.gerenciador import GerenciadorIA
            self.ia_manager = GerenciadorIA(self.manager, self.config, self)
            log('INFO', self.source_name, "Sistema de IA reinicializado com sucesso")
        except Exception as e:
            log('ERROR', self.source_name, f"Erro ao reinicializar sistema de IA: {e}")
            # Considerar um estado de falha aqui se a IA não conseguir reiniciar
            
        # 6. Inicia os novos processos de driver
        self.iniciar_drivers()
        
        # 7. Reinicia a thread do distribuidor de dados
        self.running = True
        self.iniciar_distribuidor_ia()

        log('SUCCESS', self.source_name, "--- REINICIALIZAÇÃO DO SISTEMA CONCLUÍDA ---")


    def _popular_mapa_de_tags(self):
        """Popula o dicionário compartilhado tag_map."""
        mapa_local = {}
        if 'projetos' in self.config:
            for projeto in self.config['projetos']:
                for tag in projeto.get('tags', []):
                    if 'id' in tag and 'id_driver' in tag:
                        mapa_local[tag['id']] = tag['id_driver']
        
        # Atualiza o dicionário compartilhado de uma vez
        self.tag_map.update(mapa_local)

    def escrever_valor_tag(self, tag_id: str, valor: any):
        """
        Encontra o driver correto pelo ID da tag e envia um comando de escrita.
        Valida a operação conforme a fase atual do driver.
        """
        # 1. Encontra o driver_id usando o mapa
        driver_id = self.tag_map.get(tag_id)

        if not driver_id:
            log('ERROR', self.source_name, f"Tag com ID '{tag_id}' não encontrada em nenhum driver.")
            return

        # 2. Valida a operação com o gerenciador de IA
        validacao = self.ia_manager.validar_escrita(tag_id, valor)
        if not validacao['permitido']:
            log('ERROR', self.source_name, f"Escrita não permitida para tag '{tag_id}': {validacao['erro']}")
            return

        # 3. Verifica se a fila de escrita para esse driver existe
        if driver_id in self.write_queues:
            fila_do_driver = self.write_queues[driver_id]
            comando = (tag_id, valor)
            
            # 4. Envia o comando para a fila correta
            fila_do_driver.put(comando)
            log('INFO', self.source_name, 
                f"Comando de escrita enviado para Tag '{tag_id}' (Driver: {driver_id}), " +
                f"Valor: '{valor}', Fase: {validacao['fase_atual']}")
        else:
            log('ERROR', self.source_name, f"Fila de escrita não encontrada para o driver '{driver_id}'")



    def escrever_lote_driver(self, driver_id: str, valores: any):
        """
        Envia um comando de escrita em lote para o driver especificado.
        """
        if driver_id not in self.write_queues:
            log('ERROR', self.source_name, f"Fila de escrita não encontrada para o driver '{driver_id}'")
            return False

        fila_do_driver = self.write_queues[driver_id]
        item = {"valores": valores}  # Envia dict para escrita em lote

        fila_do_driver.put(item)
        log('INFO', self.source_name, f"Comando de escrita em lote enviado para o driver '{driver_id}'")
        return True


    def iniciar_servidor_api(self):
        """Cria e inicia o servidor da API em uma thread separada."""
        try:
            if not self.servidor_api:
                # Verifica se a porta está disponível
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                port_available = sock.connect_ex(('localhost', 5000))
                sock.close()
                
                if port_available == 0:
                    log('ERROR', self.source_name, "Porta 5000 já está em uso. Servidor API não pode ser iniciado.")
                    return False
                
                # Passa a própria instância 'self' para o servidor
                self.servidor_api = ServidorAPI(sistema_principal=self)
                try:
                    self.servidor_api.start()
                    # Espera um pouco para verificar se o servidor iniciou corretamente
                    time.sleep(1)
                    if not self.servidor_api.is_alive():
                        raise Exception("Servidor não iniciou corretamente")
                    log('INFO', self.source_name, "Servidor API iniciado com sucesso")
                    return True
                except Exception as e:
                    log('ERROR', self.source_name, f"Erro ao iniciar servidor API: {e}")
                    self.servidor_api = None
                    return False
            return True
        except Exception as e:
            log('ERROR', self.source_name, f"Erro ao configurar servidor API: {e}")
            return False

    def parar_servidor_api(self):
        """Para o servidor da API de forma limpa."""
        try:
            if self.servidor_api and self.servidor_api.is_alive():
                self.servidor_api.shutdown()
                self.servidor_api.join(timeout=5)  # Espera até 5 segundos pelo término
                if self.servidor_api.is_alive():
                    log('WARN', self.source_name, "Servidor API não encerrou normalmente, forçando parada")
                    # Força o encerramento se necessário
                    import ctypes
                    if hasattr(self.servidor_api, "_thread_id"):
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(
                            ctypes.c_long(self.servidor_api._thread_id),
                            ctypes.py_object(SystemExit)
                        )
                log('INFO', self.source_name, "Servidor API encerrado")
        except Exception as e:
            log('ERROR', self.source_name, f"Erro ao parar servidor API: {e}")




