# driver_process.py

"""
Compatibilidade do driver ControlLogix/CompactLogix com pycomm3.LogixDriver

Este driver foi desenvolvido para comunicação robusta, leitura e escrita de tags em CLPs Allen-Bradley das famílias ControlLogix e CompactLogix, utilizando protocolo Ethernet/IP e a biblioteca pycomm3.

Compatibilidade Confirmada:
- Allen-Bradley CompactLogix (L1, L2, L3, L32E, L33E, L36, L38, L43, L45, L73, L84, etc.)
- Allen-Bradley ControlLogix (todas as séries: 1756-Lxx, 5580, etc.)
- Allen-Bradley SoftLogix 5800 (emulador)
- Micro800 family (Micro820, Micro850, Micro870) — desde que as tags estejam configuradas e expostas via Ethernet/IP
- Outros dispositivos Rockwell Automation que suportam CIP/Logix e expõem tags via Ethernet/IP

Compatibilidade Parcial ou Dependente de Configuração:
- Gateways EtherNet/IP que expõem tags Logix
- Emuladores RSLogix Emulate 5000

Principais Características:
- Leitura e escrita de tags por nome (não depende de endereçamento fixo)
- Suporte a tipos: BOOL, INT, DINT, REAL (float), DOUBLE, STRING
- Reconexão automática e tolerância a falhas de rede
- Log detalhado, controle de scan, fila de escrita assíncrona
- Atualização de status e valores em dicionário compartilhado

Limitações:
- Não compatível nativamente com CLPs de outros fabricantes (Siemens, Schneider, Delta, WEG, LS, etc.)
- Apenas CLPs que suportam protocolo Logix/CIP via Ethernet/IP
- Tags precisam estar configuradas e expostas para acesso remoto

Referência Técnica:
- Protocolo: EtherNet/IP (CIP)
- Biblioteca utilizada: pycomm3 (https://github.com/ottowayi/pycomm3)
- Testado e validado com CompactLogix L33E

"""



from multiprocessing import Process
from queue import Queue
import time
from typing import Dict, List, Any
from modulos.logger import log
from datetime import datetime

# Importa a biblioteca do driver diretamente aqui
from pycomm3 import LogixDriver

class controllogixDriverProcess(Process):
    """
    Processo autônomo que gerencia a comunicação com um único CLP.
    """
    def __init__(self, driver_config: Dict[str, Any], tags_config: List[Dict[str, Any]], shared_data, write_queue: Queue):
        super().__init__()
        self.daemon = True
        self.driver_id = driver_config['id']
        self.driver_config = driver_config
        self.tags_config = tags_config
        self.shared_data = shared_data
        self.write_queue = write_queue
        self.source_name = f"Driver-{self.driver_config['nome']}"
        self.running = False

        # --- TRECHO CORRIGIDO E COMPLETO ---
        config = driver_config.get('config', {})
        self.ip = config.get('ip')
        self.scan_interval_s = config.get('scan_interval', 1000) / 1000.0
        self.timeout_s = config.get('timeout', 5000) / 1000.0
        self.retry_count = config.get('retry_count', 3)
        self.log_enabled = config.get('log_enabled', True)


    def run(self):
        self.running = True
        if self.log_enabled:
            log('INFO', self.source_name, f'[{self.driver_config["tipo"]}] Processo iniciado.')
        
        if not self.ip:
            detalhe_erro = "Configuração inválida: Endereço IP não fornecido."
            if self.log_enabled: log('ERROR', self.source_name, detalhe_erro)
            self._update_shared_status("desconectado", detalhe_erro)
            self._mark_all_tags_bad("Desconectado")
            return

        tags_para_ler = [
            tag.get('endereco') for tag in self.tags_config if tag.get('scan_enabled', True)
        ]

        last_logged_status = None
        last_error_log_time = 0
        log_interval_seconds = 30

        while self.running:
            tentativas_de_conexao = 0
            conectado = False

            # --- Loop de Tentativas de Conexão ---
            while not conectado and tentativas_de_conexao < self.retry_count and self.running:
                try:
                    # O 'with' já gerencia a conexão, se falhar, levanta exceção
                    with LogixDriver(self.ip, timeout=self.timeout_s) as plc:
                        conectado = True # Se o 'with' foi bem-sucedido, estamos conectados

                        if last_logged_status != 'conectado':
                            if self.log_enabled:
                                log('INFO', self.source_name, "Conexão estabelecida com sucesso.")
                            self._update_shared_status("conectado", "Monitorando...")
                            last_logged_status = 'conectado'
                        
                        self._communication_loop(plc, tags_para_ler) # Entra no loop de comunicação

                except Exception as e:
                    tentativas_de_conexao += 1
                    detalhe_erro = f"Falha ao conectar (tentativa {tentativas_de_conexao}/{self.retry_count}): {e}"
                    
                    now = time.time()
                    if last_logged_status != 'desconectado' or (now - last_error_log_time > log_interval_seconds):
                        if self.log_enabled: log('ERROR', self.source_name, detalhe_erro)
                        last_error_log_time = now

                    self._update_shared_status("desconectado", detalhe_erro)
                    if last_logged_status != 'desconectado':
                        self._mark_all_tags_bad("Desconectado")
                        last_logged_status = 'desconectado'
                    
                    if tentativas_de_conexao < self.retry_count:
                        time.sleep(2) # Pausa curta entre as tentativas

            # Se saiu do loop de tentativas sem sucesso, faz uma pausa longa
            if self.running and not conectado:
                if self.log_enabled:
                    log('WARN', self.source_name, f"Máximo de {self.retry_count} tentativas de conexão atingido. Aguardando 10s.")
                time.sleep(10)

    def _convert_value_for_tag(self, valor, tipo_dado):
        """
        Converte o valor para o tipo correto conforme especificado em tipo_dado.
        Suporta: int, float, real, double, bool, string. Outros tipos podem ser expandidos.
        """
        try:
            if tipo_dado == "int":
                return int(valor)
            elif tipo_dado in ("float", "real", "double"):
                return float(valor)
            elif tipo_dado == "bool":
                # Aceita 1/0, 'true'/'false', True/False
                if isinstance(valor, str):
                    return valor.strip().lower() in ("1", "true", "sim", "yes")
                return bool(valor)
            elif tipo_dado == "string":
                return str(valor)
            # Adicione outros tipos conforme necessário
            return valor
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha na conversão do valor '{valor}' para tipo '{tipo_dado}': {e}")
            return valor

    def _process_write_queue(self, plc_client: LogixDriver):
        """Verifica e processa comandos na fila de escrita."""
        while not self.write_queue.empty():
            tag_id, valor = self.write_queue.get_nowait()
            tag_config = next((t for t in self.tags_config if t['id'] == tag_id), None)
            if not tag_config or not tag_config.get('escrita_permitida'):
                if self.log_enabled:
                    log('WARN', self.source_name, f"Escrita ignorada para tag '{tag_id}' (não encontrada ou sem permissão).")
                continue
            tag_endereco = tag_config.get('endereco')
            tipo_dado = tag_config.get('tipo_dado', None)
            valor_convertido = self._convert_value_for_tag(valor, tipo_dado)
            if tag_endereco:
                try:
                    response = plc_client.write((tag_endereco, valor_convertido))
                    erro_escrita = getattr(response, 'error', None)
                    # Delay para garantir atualização do CLP
                    time.sleep(0.1)
                    valor_lido = None
                    tipo_valor_lido = None
                    try:
                        resp_leitura = plc_client.read(tag_endereco)
                        if resp_leitura.error is None:
                            valor_lido = resp_leitura.value
                            tipo_valor_lido = type(valor_lido).__name__
                    except Exception as e:
                        valor_lido = f"Erro leitura pós-escrita: {e}"
                        tipo_valor_lido = None
                    escrita_efetivada = (valor_lido == valor_convertido)
                    if self.log_enabled:
                        log('INFO', self.source_name,
                            f"Escrita na tag '{tag_id}' (endereço: '{tag_endereco}'): valor_enviado='{valor_convertido}' (tipo: '{tipo_dado}'), erro='{erro_escrita}', valor_lido='{valor_lido}' (tipo_lido: '{tipo_valor_lido}'), sucesso={'SIM' if escrita_efetivada else 'NÃO'}")
                    if erro_escrita:
                        if self.log_enabled:
                            log('ERROR', self.source_name, f"Erro na escrita de '{tag_endereco}': {erro_escrita}")
                except Exception as e:
                    if self.log_enabled:
                        log('ERROR', self.source_name, f"Exceção na escrita de '{tag_endereco}': {e}")
            else:
                if self.log_enabled:
                    log('WARN', self.source_name, f"Comando de escrita para tag desconhecida '{tag_id}' ignorado.")

    def _read_tags(self, plc: LogixDriver, tags_para_ler: list):
        """Lê as tags do PLC e atualiza o dicionário compartilhado."""
        if not tags_para_ler:
            return
            
        resultados = plc.read(*tags_para_ler)
        if len(tags_para_ler) == 1 and not isinstance(resultados, list):
            resultados = [resultados]
        
        dados_lidos = {}
        tags_ativas = [t for t in self.tags_config if t.get('scan_enabled', True)]

        for i, resp in enumerate(resultados):
            tag_config = tags_ativas[i]
            tag_id = tag_config['id']
            
            if resp.error is None:
                dados_lidos[tag_id] = {'valor': resp.value, 'qualidade': 'boa', 'log': 'OK'}
            else:
                dados_lidos[tag_id] = {'valor': None, 'qualidade': 'ruim', 'log': f"Erro leitura: {resp.error}"}
                
        self._update_shared_tags(dados_lidos)

    def _update_shared_status(self, status: str, detalhe: str):
        """Atualiza o status do driver no dicionário compartilhado."""
        # Cria uma cópia temporária para evitar problemas de concorrência
        current_data = self.shared_data.get(self.driver_id, {})
        new_data = {
            "status_conexao": status,
            "detalhe": detalhe,
            "timestamp": datetime.now().isoformat(),
            "config": self.driver_config,
            "tags": current_data.get("tags", {}),
            "log": detalhe if status != "conectado" and detalhe else (current_data.get("log", "") if status != "conectado" else "")
        }
        self.shared_data[self.driver_id] = new_data

    def _update_shared_tags(self, dados_lidos: Dict[str, Any]):
        """Atualiza os dados das tags no dicionário compartilhado."""

        try:
            current_data = self.shared_data.get(self.driver_id, {})
            current_tags = current_data.get("tags", {})
            
            for tag_id, data in dados_lidos.items():
                tag_config = next((t for t in self.tags_config if t['id'] == tag_id), {})
                tag_status = {
                    "id": tag_id,
                    "id_driver": self.driver_id,  # <<< ADICIONADO: O "CEP" ESSENCIAL
                    "nome": tag_config.get('nome', '--'),
                    "endereco": tag_config.get('endereco', '--'),
                    "tipo_dado": tag_config.get('tipo_dado', '--'),
                    "valor": data.get('valor'),
                    "qualidade": data.get('qualidade'),
                    "formato_lido": data.get('formato_lido', '--'),
                    "formato_requerido": tag_config.get('tipo_dado', '--'),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "log": data.get('log', '')
                }

                # Propaga campo_exibir se existir
                if 'campo_exibir' in tag_config:
                    tag_status['campo_exibir'] = tag_config['campo_exibir']
                current_tags[tag_id] = tag_status
            
            current_data["tags"] = current_tags
            self.shared_data[self.driver_id] = current_data

        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar tags compartilhadas: {e}")
        

    def _mark_all_tags_bad(self, log_msg: str):
        """Marca todas as tags como de qualidade ruim em caso de desconexão."""
        dados_ruins = {
            tag_config['id']: {"valor": None, "qualidade": "ruim", "log": log_msg}
            for tag_config in self.tags_config
        }
        self._update_shared_tags(dados_ruins)

    def _communication_loop(self, plc: LogixDriver, tags_para_ler: list):
        """Loop principal de leitura e escrita enquanto conectado."""
        while self.running and plc.connected:
            start_time = time.time()
            try:
                self._read_tags(plc, tags_para_ler)
                self._process_write_queue(plc)
            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Erro durante comunicação: {e}. Forçando reconexão...")
                break # Quebra o loop para o 'run' principal tentar reconectar

            elapsed = time.time() - start_time
            sleep_time = self.scan_interval_s - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)