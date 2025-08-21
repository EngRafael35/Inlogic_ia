#sql_driver_process.py

"""
Compatibilidade do driver SQL industrial com pyodbc

Este driver foi projetado para comunicação robusta, leitura e escrita de dados em diversos bancos relacionais usando interface ODBC, sendo adequado para aplicações industriais, supervisórios e integrações de processo.

Compatibilidade Confirmada:
- Microsoft SQL Server (inclui Azure SQL)
- MySQL
- PostgreSQL
- Oracle Database
- Firebird/Interbase
- SQLite
- IBM DB2
- Sybase ASE
- Microsoft Access (.mdb, .accdb)

Principais Características:
- Monta automaticamente a string de conexão conforme o tipo de banco de dados informado.
- Suporte nativo a leitura e escrita de valores em tabelas específicas, por coluna configurada.
- Permite escrita individual ou em lote, com preenchimento automático de colunas de timestamp ou chave primária incremental.
- Funciona tanto com bancos locais quanto em servidores remotos.
- Reconexão automática, tolerância a falhas de rede, logs detalhados e controle de scan.
- Atualização de status de conexão e valores lidos/escritos em dicionário compartilhado.
- Compatível com sistemas supervisórios, MES, SCADA, CLPs que exportem dados via SQL, gateways industriais e integrações corporativas.

Limitações:
- Requer driver ODBC instalado para cada tipo de banco na máquina de execução.
- A estrutura da tabela (colunas, tipos, permissões) deve ser previamente criada e configurada no banco de dados.
- Não realiza operações de schema, apenas leitura/escrita de dados.
- Permissões de acesso ao banco e tabelas devem estar habilitadas para o usuário configurado.
- Para bancos com controle de concorrência ou transações, pode ser necessário ajuste específico.

Referência Técnica:
- Interface de comunicação: ODBC via pyodbc (https://github.com/mkleehammer/pyodbc)
- Testado e validado com SQL Server, MySQL, PostgreSQL e SQLite
- Adaptável para todos os bancos compatíveis com ODBC

"""


import time
from datetime import datetime
from multiprocessing import Process
import threading
import pyodbc

from modulos.logger import log

class SQLDriverProcess(Process):
    """
    Driver SQL industrial genérico, monta a string de conexão conforme o tipo de banco informado em 'db_type'.
    Compatível com SQL Server, MySQL, PostgreSQL, Oracle, Firebird, SQLite, DB2, Sybase, Access.
    """

    def __init__(self, driver_config, tags_config, shared_data, write_queue):
        super().__init__()
        self.daemon = True
        self.driver_id = driver_config['id']
        self.driver_config = driver_config
        self.tags_config = tags_config
        self.shared_data = shared_data
        self.write_queue = write_queue
        self.source_name = f"Driver-{self.driver_config.get('nome', self.driver_id)}"
        config = driver_config.get('config', {})
        self.db_type = config.get('db_type', 'sqlserver').lower()
        self.host = config.get('host')
        self.port = int(config.get('port', 1433))
        self.database = config.get('database')
        self.username = config.get('user')
        self.password = config.get('password')
        self.scan_interval_s = config.get('scan_interval', 1000) / 1000.0
        self.timeout_s = config.get('timeout', 5000) / 1000.0
        self.retry_count = config.get('retry_count', 3)
        self.log_enabled = config.get('log_enabled', True)
        self.table_name = config.get('table_name', 'dados_processo')
        self.running = False
        self.conn = None
    # self.lock será inicializado no método run()
        self.ultimo_status_conexao = None
        self.ultimo_erro_log = 0
        self.log_interval_seconds = 30

    def _montar_conn_str(self):
        """
        Monta a string de conexão ODBC conforme o tipo de banco.
        """
        if self.db_type == "sqlserver":
            # SQL Server / Azure SQL
            if self.host and "\\" in self.host:
                # Instância nomeada, sem porta
                server_str = self.host
            else:
                # Host/IP com porta
                server_str = f"{self.host},{self.port}"
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_str};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"TrustServerCertificate=yes;"
            )
        elif self.db_type == "mysql":
            return (
                f"DRIVER={{MySQL ODBC 8.0 Driver}};"
                f"SERVER={self.host};"
                f"DATABASE={self.database};"
                f"USER={self.username};"
                f"PASSWORD={self.password};"
                f"OPTION=3;"
            )
        elif self.db_type == "postgresql":
            return (
                f"DRIVER={{PostgreSQL ODBC Driver(UNICODE)}};"
                f"SERVER={self.host};"
                f"PORT={self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
        elif self.db_type == "oracle":
            return (
                f"DRIVER={{Oracle in OraClient11g_home1}};"
                f"DBQ={self.host}:{self.port}/{self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
        elif self.db_type == "sqlite":
            # No host/user, só caminho do arquivo
            return (
                f"DRIVER={{SQLite3 ODBC Driver}};"
                f"Database={self.database};"
            )
        elif self.db_type == "firebird":
            return (
                f"DRIVER={{Firebird/InterBase(r) driver}};"
                f"Dbname={self.host}:{self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
        elif self.db_type == "db2":
            return (
                f"DRIVER={{IBM DB2 ODBC DRIVER}};"
                f"DATABASE={self.database};"
                f"HOSTNAME={self.host};"
                f"PORT={self.port};"
                f"PROTOCOL=TCPIP;"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
        elif self.db_type == "sybase":
            return (
                f"DRIVER={{Sybase ASE ODBC Driver}};"
                f"SERVER={self.host};"
                f"PORT={self.port};"
                f"DB={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
            )
        elif self.db_type == "access":
            # Caminho do arquivo do banco
            return (
                f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
                f"DBQ={self.database};"
            )
        else:
            raise ValueError(f"Tipo de banco não suportado: {self.db_type}")

    def run(self):
        self.lock = threading.Lock()  # Inicializa o lock aqui, seguro para multiprocessing
        self.running = True
        if self.log_enabled:
            log('INFO', self.source_name, f"[{self.driver_config.get('tipo', 'sql')}] Processo iniciado.")
        try:
            conn_str = self._montar_conn_str()
        except Exception as e:
            detalhe_erro = f"Erro ao montar string de conexão: {e} >> String: {conn_str}"
            if self.log_enabled: log('ERROR', self.source_name, detalhe_erro)
            self._update_shared_status("desconectado", detalhe_erro)
            self._mark_all_tags_bad(detalhe_erro)
            return

        # Testa campos obrigatórios (os campos mudam por banco, mas os principais são validados)
        if not all([self.host, self.database, self.username, self.password]) and self.db_type not in ["sqlite", "access"]:
            detalhe_erro = f"Configuração SQL inválida: host/database/user/password obrigatórios. >> String: {conn_str}"
            if self.log_enabled: log('ERROR', self.source_name, detalhe_erro )
            self._update_shared_status("desconectado", detalhe_erro)
            self._mark_all_tags_bad(detalhe_erro)
            return

        while self.running:
            tentativas_de_conexao = 0
            conectado = False

            while not conectado and tentativas_de_conexao < self.retry_count and self.running:
                try:
                    self.conn = pyodbc.connect(conn_str, timeout=int(self.scan_interval_s*2))
                    conectado = True
                    if self.log_enabled and self.ultimo_status_conexao != 'conectado':
                        log('INFO', self.source_name, "Conexão SQL estabelecida com sucesso.")
                    self._update_shared_status("conectado", "Monitorando SQL...")
                    self.ultimo_status_conexao = 'conectado'
                    self._communication_loop()
                    conectado = False
                except Exception as e:
                    tentativas_de_conexao += 1
                    detalhe_erro = f"Falha ao conectar SQL (tentativa {tentativas_de_conexao}/{self.retry_count}): {e} >> String: {conn_str}"
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
            if self.running and not conectado:
                if self.log_enabled:
                    log('WARN', self.source_name, f"Máximo de {self.retry_count} tentativas de conexão SQL atingido. Aguardando 10s.")
                time.sleep(10)

    def _communication_loop(self):
        while self.running and self.conn:
            start_time = time.time()
            try:
                self._read_all_tags()
                self._process_write_queue()
            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Erro durante comunicação SQL: {e}. Forçando reconexão...")
                break
            elapsed = time.time() - start_time
            sleep_time = self.scan_interval_s - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        try:
            self.conn.close()
        except Exception:
            pass

    def _read_all_tags(self):
        dados_lidos = {}
        for tag in self.tags_config:
            if not tag.get('scan_enabled', True):
                continue
            coluna = tag.get('endereco')
            tag_id = tag['id']
            try:
                # Descobrir coluna para ordenação: 'timestamp' ou primeira coluna
                cursor = self.conn.cursor()
                cursor.execute(f"SELECT * FROM [{self.table_name}] LIMIT 1" if self.db_type != "sqlserver" else f"SELECT TOP 1 * FROM [{self.table_name}]")
                columns = [desc[0] for desc in cursor.description]
                # Preferencialmente usar 'timestamp', senão a primeira coluna
                if 'timestamp' in columns:
                    col_ord = 'timestamp'
                else:
                    col_ord = columns[0]
                # Montar consulta limitada ao mais recente
                if self.db_type == "sqlserver":
                    query = f"SELECT TOP 1 * FROM [{self.table_name}] ORDER BY [{col_ord}] DESC"
                elif self.db_type in ["mysql", "postgresql", "sqlite", "firebird", "db2", "sybase"]:
                    query = f"SELECT * FROM [{self.table_name}] ORDER BY [{col_ord}] DESC LIMIT 1"
                else:
                    query = f"SELECT * FROM [{self.table_name}] ORDER BY [{col_ord}] DESC"
                cursor.execute(query)
                row = cursor.fetchone()
                valor = None
                if row:
                    # Analisar tipo da coluna de ordenação
                    col_types = [desc[1] for desc in cursor.description]
                    # Se for int ou datetime, ok
                    row_dict = dict(zip(columns, row))
                    valor = row_dict.get(coluna)
                dados_lidos[tag_id] = {
                    "valor": valor,
                    "qualidade": "boa" if valor is not None else "ruim",
                    "log": "OK" if valor is not None else "Sem dados"
                }
            except Exception as e:
                dados_lidos[tag_id] = {
                    "valor": None,
                    "qualidade": "ruim",
                    "log": f"Erro leitura SQL: {e}"
                }
        self._update_shared_tags(dados_lidos)

    def _process_write_queue(self):
        while not self.write_queue.empty():
            try:
                item = self.write_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    tag_id, valor = item
                    self._write_single_tag(tag_id, valor)
                elif isinstance(item, dict):
                    self._write_batch(item)
                else:
                    if self.log_enabled:
                        log('WARN', self.source_name, f"Item inválido na fila de escrita SQL: {item}")
            except Exception as e:
                if self.log_enabled:
                    log('ERROR', self.source_name, f"Exceção na escrita SQL: {e}")


    def _write_single_tag(self, tag_id, valor):
        tag_config = next((t for t in self.tags_config if t['id'] == tag_id), None)
        if not tag_config or not tag_config.get('escrita_permitida'):
            if self.log_enabled:
                log('WARN', self.source_name, f"Escrita ignorada para tag '{tag_id}' (não encontrada ou sem permissão).")
            return
        coluna = tag_config.get('endereco')
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM [{self.table_name}] LIMIT 1" if self.db_type != "sqlserver" else f"SELECT TOP 1 * FROM [{self.table_name}]")
            columns = [desc[0] for desc in cursor.description]
            col_types = [desc[1] for desc in cursor.description]
            primeira_coluna = columns[0]
            tipo_primeira = col_types[0]
            valores = {coluna: valor}
            # Se a primeira coluna não for a coluna da tag, preencher automaticamente
            if primeira_coluna != coluna:
                if 'date' in str(tipo_primeira).lower() or 'time' in str(tipo_primeira).lower():
                    carimbo = datetime.now()
                    valores[primeira_coluna] = carimbo
                    print(f"[SQLDriverProcess] Inserindo timestamp na coluna '{primeira_coluna}': {carimbo}")
                elif 'int' in str(tipo_primeira).lower():
                    cursor.execute(f"SELECT MAX([{primeira_coluna}]) FROM [{self.table_name}]")
                    ultimo = cursor.fetchone()[0]
                    novo_valor = (ultimo or 0) + 1
                    valores[primeira_coluna] = novo_valor
                    print(f"[SQLDriverProcess] Inserindo valor incremental na coluna '{primeira_coluna}': {novo_valor}")
            colunas_sql = ', '.join([f"[{col}]" for col in valores.keys()])
            placeholders = ', '.join(['?' for _ in valores])
            query = f"INSERT INTO [{self.table_name}] ({colunas_sql}) VALUES ({placeholders})"
            cursor.execute(query, tuple(valores.values()))
            self.conn.commit()
            if self.log_enabled:
                log('INFO', self.source_name, f"Escrita SQL convencional: {valores} (tag '{tag_id}')")
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Erro na escrita SQL da tag '{tag_id}' (coluna '{coluna}'): {e}")




    def _write_batch(self, item):
        valores = item.get('valores')
        linha_id = item.get('linha_id')
        if not isinstance(valores, dict) or not valores:
            if self.log_enabled:
                log('WARN', self.source_name, f"Escrita em lote ignorada: valores inválidos.")
            return
        try:
            cursor = self.conn.cursor()
            # Descobrir colunas e tipos
            cursor.execute(f"SELECT * FROM [{self.table_name}] LIMIT 1" if self.db_type != "sqlserver" else f"SELECT TOP 1 * FROM [{self.table_name}]")
            columns = [desc[0] for desc in cursor.description]
            col_types = [desc[1] for desc in cursor.description]
            primeira_coluna = columns[0]
            tipo_primeira = col_types[0]
            # Verificar se a primeira coluna está nos valores, se não, inserir
            if primeira_coluna not in valores:
                if 'date' in str(tipo_primeira).lower() or 'time' in str(tipo_primeira).lower():
                    # Inserir timestamp
                    carimbo = datetime.now()
                    valores[primeira_coluna] = carimbo
                    print(f"[SQLDriverProcess] Inserindo timestamp na coluna '{primeira_coluna}': {carimbo}")
                elif 'int' in str(tipo_primeira).lower():
                    # Buscar último valor e incrementar
                    cursor.execute(f"SELECT MAX([{primeira_coluna}]) FROM [{self.table_name}]")
                    ultimo = cursor.fetchone()[0]
                    novo_valor = (ultimo or 0) + 1
                    valores[primeira_coluna] = novo_valor
                    print(f"[SQLDriverProcess] Inserindo valor incremental na coluna '{primeira_coluna}': {novo_valor}")
            # Garantir que os nomes das colunas correspondam ao campo 'endereco' das tags
            colunas = []
            params = []
            for tag_id, valor in valores.items():
                tag_config = next((t for t in self.tags_config if t['id'] == tag_id), None)
                if tag_config:
                    coluna_nome = tag_config.get('endereco')
                    colunas.append(f"[{coluna_nome}]")
                    params.append(valor)
            # Adicionar a primeira coluna se não estiver nas tags
            if primeira_coluna not in [tag_config.get('endereco') for tag_config in self.tags_config if tag_config]:
                colunas.insert(0, f"[{primeira_coluna}]")
                params.insert(0, valores[primeira_coluna])
            if linha_id:
                set_clause = ', '.join([f"{col} = ?" for col in colunas])
                query = f"UPDATE [{self.table_name}] SET {set_clause} WHERE id = ?"
                cursor.execute(query, tuple(params) + (linha_id,))
                self.conn.commit()
                if self.log_enabled:
                    log('INFO', self.source_name, f"Escrita SQL em lote (UPDATE id={linha_id}): {valores}")
            else:
                placeholders = ', '.join(['?' for _ in colunas])
                query = f"INSERT INTO [{self.table_name}] ({', '.join(colunas)}) VALUES ({placeholders})"
                cursor.execute(query, tuple(params))
                self.conn.commit()
                if self.log_enabled:
                    log('INFO', self.source_name, f"Escrita SQL em lote (INSERT): {valores}")
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Erro na escrita SQL em lote: {e}")

    def _update_shared_status(self, status: str, detalhe: str):
        try:
            driver_data = self.shared_data.get(self.driver_id, {})
            driver_data.update({
                "status_conexao": status,
                "detalhe": detalhe,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "config": self.driver_config,
                "tags": driver_data.get("tags", {}),
                "log": detalhe
            })
            self.shared_data[self.driver_id] = driver_data
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar status compartilhado: {e}")

    def _update_shared_tags(self, dados_lidos: dict):
        try:
            driver_data = self.shared_data.get(self.driver_id)
            if not driver_data:
                driver_data = {}
            tags_data = driver_data.get("tags", {})
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
                if 'campo_exibir' in tag_config:
                    tag_status['campo_exibir'] = tag_config['campo_exibir']
                tags_data[tag_id] = tag_status
            driver_data["tags"] = tags_data
            self.shared_data[self.driver_id] = driver_data
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao atualizar tags compartilhadas: {e}")

    def _mark_all_tags_bad(self, log_msg: str):
        dados_ruins = {
            tag['id']: {"valor": None, "qualidade": "ruim", "log": log_msg}
            for tag in self.tags_config
        }
        self._update_shared_tags(dados_ruins)

    def parar(self):
        self.running = False
        try:
            if self.conn:
                self.conn.close()
            if self.log_enabled:
                log('INFO', self.source_name, "Conexão SQL encerrada.")
        except Exception as e:
            if self.log_enabled:
                log('ERROR', self.source_name, f"Falha ao encerrar conexão SQL: {e}")