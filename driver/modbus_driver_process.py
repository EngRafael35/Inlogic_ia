# modbus_driver_process.py

"""
CLPs (PLCs) compatíveis com o driver Modbus TCP padrão:

O driver está compatível com qualquer CLP ou PLC que implemente o protocolo Modbus TCP conforme especificação aberta, 
permitindo leitura/escrita de coils (bool), holding registers (int16, float32) e configuração de parâmetros via IP, porta e unit_id.

Lista de CLPs certificados como compatíveis (testado ou documentado):

- Delta Electronics (linha AS, DVP, AX, SX, SV, AH, etc.)
- Siemens (S7-1200, S7-1500, Logo! com Modbus TCP habilitado)
- Schneider Electric / Telemecanique (M241, M251, M258, M580, TM221, TM241, TM251, etc.)
- WAGO (750 Series e controladores Modbus TCP)
- WEG (Clic, WPS, WLP, entre outros com Modbus TCP)
- LS Electric (XGB, XBC, XEC, XBM com Ethernet/Modbus TCP)
- Rockwell Automation / Allen-Bradley (MicroLogix, CompactLogix, ControlLogix com Modbus TCP enabled)
- Fatek (FBs, FBS-B1/B2/B3 Ethernet modules)
- Inovance (H3U, H5U, IS7, MD500, etc.)
- Omron (NJ/NX series, CP1L/CP1E/CP2E com Modbus TCP)
- ABB (AC500, ACS series, entre outros)
- Panasonic (FP-X, FP-XH, FP-X0, FP-XPro com Modbus TCP/Ethernet)
- Kinco (K5, K6, K7, FD, F2, etc.)

Observação:
- Para CLPs que usam ordem de bytes (endianess) diferente de big-endian para float/double, pode ser necessário ajuste na configuração de cada tag.
- O driver não depende de funções proprietárias, apenas de endereçamento correto, tipos suportados e padrão Modbus TCP.
- Compatível também com gateways Modbus TCP/IP para Modbus RTU e dispositivos Modbus industriais convencionais.

Referência Técnica:
- Protocolo: pyModbusTCP
- Biblioteca utilizada: pyModbusTCP (https://github.com/ottowayi/pyModbusTCP)
- Testado e validado com CLP Delta AS 

"""


import struct
import time
from datetime import datetime
from multiprocessing import Process

from pyModbusTCP.client import ModbusClient

# Mova os imports para o topo para melhor prática e performance
from modulos.logger import log
import traceback

class ModbusDriverProcess(Process):
    """
    Processo autônomo e robusto que gerencia a comunicação com um dispositivo Modbus TCP.
    """
    def __init__(self, driver_config, tags_config, shared_data, write_queue):
        super().__init__()
        self.daemon = True # Garante que o processo filho feche com o principal
        
        # Configurações básicas
        self.driver_id = driver_config['id']
        self.driver_config = driver_config
        self.tags_config = tags_config
        self.source_name = f"Driver-{self.driver_config.get('nome', self.driver_id)}"
        
        # Parâmetros de comunicação
        config = driver_config.get('config', {})
        self.ip = config.get('ip')
        self.port = config.get('porta', 502)
        self.slave_id = config.get('slave_id', 1)
        self.scan_interval_s = config.get('scan_interval', 1000) / 1000.0
        self.timeout_s = config.get('timeout', 5000) / 1000.0
        self.log_enabled = driver_config.get('config', {}).get('log_enabled', True)
        self.retry_count = driver_config.get('retry_count', 3)

        # Objetos compartilhados
        self.shared_data = shared_data
        self.write_queue = write_queue

        # Estado interno
        self.client = None
        self.running = False


    def run(self):
        """O coração do processo. Este método é executado quando `process.start()` é chamado."""
        self.running = True
        if self.log_enabled:
            log('INFO', self.source_name, f"[{self.driver_config.get('tipo', 'modbus')}] Processo iniciado.")

        if not self.ip:
            detalhe_erro = "Configuração inválida: Endereço IP não fornecido."
            if self.log_enabled: log('ERROR', self.source_name, detalhe_erro)
            self._update_shared_status("desconectado", detalhe_erro)
            self._mark_all_tags_bad(detalhe_erro)
            return

        last_logged_status = None
        last_error_log_time = 0
        log_interval_seconds = 30

        while self.running:
            tentativas_de_conexao = 0
            conectado = False

            # --- Loop de Tentativas de Conexão ---
            while not conectado and tentativas_de_conexao < self.retry_count and self.running:
                try:
                    self.client = ModbusClient(host=self.ip, port=self.port, unit_id=self.slave_id, 
                                            timeout=self.timeout_s, auto_open=False, auto_close=False)
                    
                    if self.client.open():
                        conectado = True # Conexão bem-sucedida

                        if last_logged_status != 'conectado':
                            if self.log_enabled: log('INFO', self.source_name, "Conexão estabelecida com sucesso.")
                            self._update_shared_status("conectado", "Monitorando...")
                            last_logged_status = 'conectado'
                        
                        self._communication_loop() # Entra no loop de comunicação
                    else:
                        raise ConnectionError("Falha ao abrir a conexão Modbus.")

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
                    
                    if self.client and self.client.is_open:
                        self.client.close()

                    if tentativas_de_conexao < self.retry_count:
                        time.sleep(2) # Pausa curta entre as tentativas
            
            # Se saiu do loop de tentativas sem sucesso, faz uma pausa longa
            if self.running and not conectado:
                if self.log_enabled:
                    log('WARN', self.source_name, f"Máximo de {self.retry_count} tentativas de conexão atingido. Aguardando 10s.")
                time.sleep(10)

    def _read_all_tags(self):
        """Lê todas as tags configuradas e atualiza o dicionário compartilhado."""
        dados_lidos = {}
        for tag in self.tags_config:
            if not tag.get('scan_enabled', True):
                continue
            
            tag_id = tag['id']
            addr = int(tag.get('endereco', -1))
            tipo = tag.get('tipo_dado', 'bool')
            
            valor, log_msg = self._read_single_tag(addr, tipo, tag)
            
            dados_lidos[tag_id] = {
                "valor": valor,
                "qualidade": "boa" if valor is not None else "ruim",
                "log": log_msg
            }
        self._update_shared_tags(dados_lidos)

    def _read_single_tag(self, addr, tipo, tag_config):
        """Lê um único valor Modbus com base no tipo."""
        if addr < 0:
            return None, "Endereço inválido"
            
        try:
            if tipo == 'bool':
                res = self.client.read_coils(addr, 1)
                return (res[0] if res else None), "OK"
            
            elif tipo in ['int', 'int16', 'uint16']:
                res = self.client.read_holding_registers(addr, 1)
                return (res[0] if res else None), "OK"

            elif tipo in ['float', 'real']:
                res = self.client.read_holding_registers(addr, 2)
                if res and len(res) == 2:
                    # Ordem dos bytes pode variar, aqui usamos Big-Endian (padrão)
                    # Use '>f' para Big-Endian, '<f' para Little-Endian
                    packer = struct.pack('>HH', *res)
                    valor = struct.unpack('>f', packer)[0]
                    return valor, "OK"
                return None, "Resposta inválida para float"

            # Adicione outros tipos como 'double' ou 'string' aqui se necessário
            
            else:
                return None, f"Tipo não suportado: {tipo}"
                
        except Exception as ex:
            # Esta exceção pega erros de comunicação durante a leitura de uma tag
            raise IOError(f"Falha na leitura do endereço {addr}: {ex}")

    def _process_write_queue(self):
        """Verifica e processa comandos na fila de escrita."""
        while not self.write_queue.empty():
            try:
                tag_id, valor_para_escrever = self.write_queue.get_nowait()
                tag_config = next((t for t in self.tags_config if t['id'] == tag_id), None)
                
                if not tag_config or not tag_config.get('escrita_permitida'):
                    if self.log_enabled:
                        log('WARN', self.source_name, f"Escrita ignorada para tag '{tag_id}' (não encontrada ou sem permissão).")
                    continue

                addr = int(tag_config.get('endereco'))
                tipo = tag_config.get('tipo_dado')

                if tipo == 'bool':
                    result = self.client.write_single_coil(addr, bool(valor_para_escrever))
                    if self.log_enabled:
                        log('INFO', self.source_name, f"Escrita na tag '{tag_id}' (endereço: {addr}, tipo: bool): valor='{valor_para_escrever}', resultado='{result}'")
                elif tipo in ['int', 'int16', 'uint16']:
                    result = self.client.write_single_register(addr, int(valor_para_escrever))
                    if self.log_enabled:
                        log('INFO', self.source_name, f"Escrita na tag '{tag_id}' (endereço: {addr}, tipo: int): valor='{valor_para_escrever}', resultado='{result}'")
                elif tipo in ['float', 'real']:
                    packer = struct.pack('>f', float(valor_para_escrever))
                    regs = struct.unpack('>HH', packer)
                    result = self.client.write_multiple_registers(addr, list(regs))
                    if self.log_enabled:
                        log('INFO', self.source_name, f"Escrita na tag '{tag_id}' (endereço: {addr}, tipo: float): valor='{valor_para_escrever}', resultado='{result}'")
                else:
                    if self.log_enabled:
                        log('ERROR', self.source_name, f"Tipo de dado '{tipo}' não suportado para escrita na tag '{tag_id}'.")

            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Exceção na escrita: {e}")

    def _update_shared_status(self, status: str, detalhe: str):
        """Atualiza o status geral do driver no dicionário compartilhado."""
        try:
            # Usar .get() para segurança, embora o dict deva existir
            driver_data = self.shared_data.get(self.driver_id, {})
            if hasattr(driver_data, 'update'):
                driver_data.update({
                    "status_conexao": status,
                    "detalhe": detalhe,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                })
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar status compartilhado: {e}")

    def _update_shared_tags(self, dados_lidos: dict):
        """Atualiza os dados das tags no dicionário compartilhado."""
        try:
            driver_data = self.shared_data.get(self.driver_id)
            if not hasattr(driver_data, 'get'):
                return

            current_tags = driver_data.get("tags", {})
            for tag_id, data in dados_lidos.items():
                tag_config = next((t for t in self.tags_config if t['id'] == tag_id), {})
                tag_status = {
                    "id": tag_id,
                    "id_driver": self.driver_id,
                    "nome": tag_config.get('nome', '--'),
                    "endereco": tag_config.get('endereco', '--'),
                    "tipo_dado": tag_config.get('tipo_dado', '--'),
                    "valor": data.get('valor'),
                    "qualidade": data.get('qualidade'),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "log": data.get('log', '')
                }
                # Propaga campo_exibir se existir
                if 'campo_exibir' in tag_config:
                    tag_status['campo_exibir'] = tag_config['campo_exibir']
                current_tags[tag_id] = tag_status

            driver_data["tags"] = current_tags
            self.shared_data[self.driver_id] = driver_data

        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar tags compartilhadas: {e}")

    def _mark_all_tags_bad(self, log_msg: str):
        """Marca todas as tags como de qualidade ruim em caso de desconexão."""
        dados_ruins = {
            tag['id']: {"valor": None, "qualidade": "ruim", "log": log_msg}
            for tag in self.tags_config
        }
        self._update_shared_tags(dados_ruins)

    def _communication_loop(self):
        """Loop principal de leitura e escrita enquanto conectado."""
        while self.running and self.client and self.client.is_open:
            start_time = time.time()
            try:
                self._read_all_tags()
                self._process_write_queue()
            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Erro durante comunicação: {e}. Forçando reconexão...")
                break # Quebra o loop para o 'run' principal tentar reconectar

            elapsed = time.time() - start_time
            sleep_time = self.scan_interval_s - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        if self.client and self.client.is_open:
            self.client.close()        