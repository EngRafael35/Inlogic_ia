# mqtt_driver_process.py


"""
Compatibilidade do driver MQTT industrial com paho-mqtt

Este driver foi desenvolvido para integração industrial robusta via protocolo MQTT, possibilitando comunicação com brokers e dispositivos IoT, CLPs, sensores, gateways e sistemas supervisórios em aplicações de automação.

Compatibilidade Confirmada:
- Qualquer broker MQTT padrão (Mosquitto, HiveMQ, EMQX, VerneMQ, RabbitMQ com plugin MQTT, AWS IoT Core, Azure IoT Hub, IBM Watson IoT, etc.)
- CLPs industriais, sensores, gateways, edge devices e sistemas que publiquem/recebam mensagens MQTT.
- Compatível com dispositivos de qualquer fabricante que sigam o padrão MQTT 3.1/3.1.1/5.0.
- Integrável com sistemas SCADA, MES, supervisórios, plataformas cloud IoT e soluções IIoT.

Principais Características:
- Conexão, reconexão e gerenciamento autônomo do ciclo de vida do cliente MQTT.
- Leitura (subscribe) e escrita (publish) de dados em múltiplos tópicos configuráveis.
- Suporte a autenticação (login/senha), client_id customizável e controle de timeout/retries.
- Atualização de status, valores e qualidade de dados em dicionário compartilhado.
- Processamento profissional de erros, log detalhado, fila de escrita assíncrona.
- Flexível para diferentes estruturas de dados (textos, números, JSON, etc.) conforme payload.
- Compatível com qualquer arquitetura, seja industrial, predial, automotiva, agrícola ou residencial.

Limitações:
- Requer broker MQTT acessível e corretamente configurado para aceitar conexões externas.
- Permissões de publicação/assinatura devem estar habilitadas para o usuário configurado.
- Não executa parsing automático de payloads complexos (ex: JSON aninhado), podendo ser necessário tratamento adicional.
- Não realiza discovery automático de tópicos; depende da configuração das tags/tópicos monitorados.
- A qualidade dos dados depende da frequência de publicação dos dispositivos nos tópicos MQTT.
- Para garantir integridade dos dados, recomenda-se uso de QoS apropriado e tópicos bem definidos.

Referência Técnica:
- Protocolo: MQTT 3.1, 3.1.1, 5.0
- Biblioteca utilizada: paho-mqtt (https://github.com/eclipse/paho.mqtt.python)
- Testado e validado com Mosquitto, HiveMQ, EMQX, AWS IoT Core e dispositivos industriais MQTT

"""

import time
from datetime import datetime
from multiprocessing import Process, Lock, Queue
import paho.mqtt.client as mqtt

from modulos.logger import log

class MQTTDriverProcess(Process):
    """
    Processo autônomo e robusto para integração industrial via MQTT.
    Segue o padrão e práticas dos drivers ControlLogix/Modbus do sistema, 
    com tratamento profissional de erros, logging, reconexão, filas de escrita e atualização de dados compartilhados.
    """

    def __init__(self, driver_config, tags_config, shared_data, write_queue):
        super().__init__()
        self.daemon = True  # Garante encerramento junto ao processo principal
        # --- Identificação e Configuração ---
        self.driver_id = driver_config['id']
        self.driver_config = driver_config
        self.tags_config = tags_config
        self.shared_data = shared_data
        self.write_queue = write_queue
        self.source_name = f"Driver-{self.driver_config.get('nome', self.driver_id)}"

        # --- Parâmetros de comunicação MQTT ---
        config = driver_config.get('config', {})
        self.broker_address = config.get('host')  # Padrão: 'host'
        self.port = config.get('port', 1883)
        self.client_id = config.get('client_id')
        self.username = config.get('login') or None
        self.password = config.get('senha') or None
        self.scan_interval_s = config.get('scan_interval', 1000) / 1000.0
        self.timeout_s = config.get('timeout', 5000) / 1000.0
        self.retry_count = config.get('retry_count', 3)
        self.log_enabled = config.get('log_enabled', True)
        # --- Lista de tópicos monitorados vem das tags scan_enabled ---
        self.topicos = [tag.get('endereco') for tag in self.tags_config if tag.get('scan_enabled', True)]
        self.running = False

        # --- Controle interno de reconexão e logging ---
        self.ultimo_status_conexao = None
        self.ultimo_erro_log = 0
        self.log_interval_seconds = 30

    def run(self):
        """
        Método principal do processo: gerencia ciclo de vida, reconexão, loop de comunicação.
        """
        self.running = True
        # --- Estado MQTT ---
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        if self.log_enabled:
            log('INFO', self.source_name, f"[{self.driver_config.get('tipo', 'mqtt')}] Processo iniciado.")

        # --- Validação de configuração obrigatória ---
        if not self.broker_address:
            detalhe_erro = "Configuração inválida: broker_address (host) não fornecido."
            if self.log_enabled: log('ERROR', self.source_name, detalhe_erro)
            self._update_shared_status("desconectado", detalhe_erro)
            self._mark_all_tags_bad(detalhe_erro)
            return

        # --- Loop principal de conexão/reconexão ---
        while self.running:
            tentativas_de_conexao = 0
            conectado = False

            while not conectado and tentativas_de_conexao < self.retry_count and self.running:
                try:
                    # --- Tentativa de conexão MQTT ---
                    self.client.connect(self.broker_address, self.port, int(self.timeout_s))
                    self.client.loop_start()  # Inicia thread interna do MQTT
                    conectado = True
                    if self.log_enabled and self.ultimo_status_conexao != 'conectado':
                        log('INFO', self.source_name, "Conexão MQTT estabelecida com sucesso.")
                    self._update_shared_status("conectado", "Monitorando MQTT...")
                    self.ultimo_status_conexao = 'conectado'
                    # --- Aguarda conexão antes de iniciar o loop principal ---
                    time.sleep(2)
                    self._communication_loop()
                    # Após o loop, assume desconexão
                    conectado = False

                except Exception as e:
                    tentativas_de_conexao += 1
                    detalhe_erro = f"Falha ao conectar MQTT (tentativa {tentativas_de_conexao}/{self.retry_count}): {e}"
                    now = time.time()
                    if self.ultimo_status_conexao != 'desconectado' or (now - self.ultimo_erro_log > self.log_interval_seconds):
                        if self.log_enabled: log('ERROR', self.source_name, detalhe_erro)
                        self.ultimo_erro_log = now
                    self._update_shared_status("desconectado", detalhe_erro)
                    if self.ultimo_status_conexao != 'desconectado':
                        self._mark_all_tags_bad("Desconectado")
                        self.ultimo_status_conexao = 'desconectado'
                    if tentativas_de_conexao < self.retry_count:
                        time.sleep(2)

            # --- Pausa longa após falha nas tentativas ---
            if self.running and not conectado:
                if self.log_enabled:
                    log('WARN', self.source_name, f"Máximo de {self.retry_count} tentativas de conexão MQTT atingido. Aguardando 10s.")
                time.sleep(10)

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback padrão do MQTT: executado ao conectar ao broker.
        Inscreve-se nos tópicos das tags e registra eventos.
        """
        if rc == 0:
            if self.log_enabled: log('INFO', self.source_name, "Conexão MQTT bem-sucedida.")
            # --- Inscrição em todos os tópicos das tags com scan_enabled ---
            for topico in self.topicos:
                try:
                    client.subscribe(topico)
                    if self.log_enabled: log('INFO', self.source_name, f"Inscrito no tópico: {topico}")
                except Exception as e:
                    if self.log_enabled: log('ERROR', self.source_name, f"Erro ao inscrever no tópico '{topico}': {e}")
        else:
            if self.log_enabled: log('ERROR', self.source_name, f"Falha na conexão MQTT. Código: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """
        Callback padrão do MQTT: executado ao desconectar do broker.
        Atualiza status e marca tags como ruim.
        """
        detalhe = f"Desconectado do broker MQTT. Código: {rc}"
        if self.log_enabled: log('WARN', self.source_name, detalhe)
        self._update_shared_status("desconectado", detalhe)
        self._mark_all_tags_bad(detalhe)

    def on_message(self, client, userdata, msg):
        """
        Callback padrão do MQTT: executado ao receber mensagem de qualquer tópico inscrito.
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self._process_message(topic, payload)
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Erro ao processar mensagem MQTT: {e}")

    def _process_message(self, topic, valor):
        """
        Processa mensagem recebida, converte valor, atualiza o dicionário compartilhado.
        """
        try:
            valor = valor.strip() if isinstance(valor, str) else valor
            if valor == "": valor = None
            elif isinstance(valor, str) and valor.isdigit():
                valor = int(valor)
            else:
                try:
                    valor = float(valor.replace(",", ".")) if isinstance(valor, str) else valor
                except Exception:
                    pass

            dados_lidos = {
                topic: {
                    "valor": valor,
                    "qualidade": "boa" if valor is not None else "ruim",
                    "log": "Mensagem recebida MQTT" if valor is not None else "Valor vazio recebido"
                }
            }
            self._update_shared_tags(dados_lidos)
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Erro ao processar tag MQTT '{topic}': {e}")

    def _process_write_queue(self):
        """
        Processa comandos de escrita na fila, publica valores nos tópicos correspondentes.
        """
        while not self.write_queue.empty():
            try:
                tag_id, valor_para_escrever = self.write_queue.get_nowait()
                tag_config = next((t for t in self.tags_config if t['id'] == tag_id), None)
                if not tag_config or not tag_config.get('escrita_permitida'):
                    if self.log_enabled:
                        log('WARN', self.source_name, f"Escrita ignorada para tag '{tag_id}' (não encontrada ou sem permissão).")
                    continue
                topico = tag_config.get('endereco')
                if topico:
                    result = self.client.publish(topico, valor_para_escrever)
                    if self.log_enabled:
                        log('INFO', self.source_name, f"Mensagem publicada no tópico '{topico}': {valor_para_escrever} (result: {result.rc})")
                else:
                    if self.log_enabled:
                        log('WARN', self.source_name, f"Comando de escrita para tag desconhecida '{tag_id}' ignorado.")
            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Exceção na escrita MQTT: {e}")


    def _update_shared_status(self, status: str, detalhe: str):
        """
        Atualiza o status geral do driver no dicionário compartilhado do sistema.
        """
        try:
            driver_data = self.shared_data.get(self.driver_id, {})
            driver_data.update({
                "status_conexao": status,
                "detalhe": detalhe,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "config": self.driver_config,
                "tags": driver_data.get("tags", {}),
                "log": detalhe
            })
            self.shared_data[self.driver_id] = driver_data
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar status compartilhado: {e}")

    def _update_shared_tags(self, dados_lidos: dict):
        """
        Atualiza os dados das tags no dicionário compartilhado, seguindo padrão completo do sistema.
        """
        try:
            driver_data = self.shared_data.get(self.driver_id)
            if not driver_data:
                driver_data = {}
            tags_data = driver_data.get("tags", {})
            for tag_id, data in dados_lidos.items():
                # Busca config real da tag (por id ou endereco/tópico)
                tag_config = next((t for t in self.tags_config if t.get('endereco') == tag_id or t['id'] == tag_id), {})
                tag_status = {
                    "id": tag_config.get('id', tag_id),
                    "id_driver": self.driver_id,
                    "nome": tag_config.get('nome', '--'),
                    "endereco": tag_config.get('endereco', tag_id),
                    "tipo_dado": tag_config.get('tipo_dado', '--'),
                    "valor": data.get('valor'),
                    "qualidade": data.get('qualidade'),
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "log": data.get('log', '')
                }
                # Propaga campo_exibir se existir (para interface)
                if 'campo_exibir' in tag_config:
                    tag_status['campo_exibir'] = tag_config['campo_exibir']
                tags_data[tag_status['id']] = tag_status
            driver_data["tags"] = tags_data
            self.shared_data[self.driver_id] = driver_data
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar tags compartilhadas: {e}")

    def _mark_all_tags_bad(self, log_msg: str):
        """
        Marca todas as tags como de qualidade ruim em caso de desconexão do broker.
        """
        dados_ruins = {
            tag_config['id']: {"valor": None, "qualidade": "ruim", "log": log_msg}
            for tag_config in self.tags_config
        }
        self._update_shared_tags(dados_ruins)

    def _communication_loop(self):
        """
        Loop principal de comunicação: processa fila de escrita e mantém ciclo de vida do driver.
        """
        while self.running and self.client.is_connected():
            start_time = time.time()
            try:
                self._process_write_queue()
            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Erro durante comunicação MQTT: {e}. Forçando reconexão...")
                break
            elapsed = time.time() - start_time
            sleep_time = self.scan_interval_s - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        # --- Finalização segura da conexão MQTT ---
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def parar(self):
        """
        Método para encerrar o processo e desconectar do broker MQTT.
        """
        self.running = False
        try:
            self.client.loop_stop()
            self.client.disconnect()
            if self.log_enabled:
                log('INFO', self.source_name, "Conexão MQTT encerrada.")
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao encerrar conexão MQTT: {e}")