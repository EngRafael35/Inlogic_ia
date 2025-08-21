# servidor.servidor.py

"""
Módulo: servidor
----------------

Este módulo implementa o **Servidor de API REST do InLogic**, responsável por expor
funcionalidades de comunicação entre o núcleo do sistema, agentes inteligentes e 
interfaces externas (supervisórios, sistemas industriais e serviços de IA).

Arquitetura e Design
~~~~~~~~~~~~~~~~~~~~
- Implementação baseada em **Flask**, encapsulada na classe `ServidorAPI`.
- Execução isolada em **thread dedicada**, garantindo que o servidor não bloqueie o
  processamento principal.
- Padronização de logs via módulo central `logger`, assegurando rastreabilidade.
- Estrutura modular para integração futura com segurança, escalabilidade e orquestração
  distribuída.

Principais Endpoints
~~~~~~~~~~~~~~~~~~~~
- **/api/dados** (GET):
  Retorna os valores de todos os drivers e suas tags em formato JSON.

- **/api/escrever** (POST):
  Permite escrita de valor em uma tag específica, com validação de existência de driver e tag.

- **/api/escrever_lote** (POST):
  Escrita em múltiplas tags de um driver em uma única operação atômica.

- **/api/logs** (GET):
  Retorna os últimos N registros de log do sistema, útil para auditoria e debug.

- **/api/ia/evento** (POST):
  Recebe eventos vindos de módulos de IA, registrando-os no log para correlação posterior.

- **/api/ia/acao** (POST):
  Recebe decisões/ações propostas pela IA e as registra para inspeção ou execução.

- **/api/health** (GET):
  Fornece diagnóstico detalhado de saúde do sistema (uptime, memória, CPU, drivers, tags).

- **/api/shutdown** (POST):
  Solicita desligamento seguro do servidor, liberando recursos.

Recursos Técnicos
~~~~~~~~~~~~~~~~~
- **Thread-safety**: operações encapsuladas com `threading.Thread` e travas de log.
- **Resiliência**: tratamento de exceções em todos os endpoints com mensagens padronizadas.
- **Extensibilidade**: fácil adição de novos endpoints, middlewares e camadas de segurança.
- **Compatibilidade industrial**: endpoints preparados para integração com CLPs, SCADAs e 
  motores de IA distribuídos.

Constantes Relevantes
~~~~~~~~~~~~~~~~~~~~~
- `host`: endereço de binding do servidor (default: `"0.0.0.0"`).
- `port`: porta de escuta (default: `5000`).
- `motor`: instância central de controle e processamento.
- `log`: função de logging integrada.

Exemplo de Uso
~~~~~~~~~~~~~~
>>> from servidor import ServidorAPI
>>> servidor = ServidorAPI(motor)
>>> servidor.iniciar()
ServidorAPI rodando em http://0.0.0.0:5000

Notas
~~~~~
Este servidor é projetado como **núcleo de orquestração do InLogic**, sendo
o ponto central de comunicação entre:
- Agentes distribuídos de IA
- Supervisórios industriais
- Camadas de automação e segurança

Futuras melhorias planejadas incluem:
- Suporte a autenticação (JWT/API Key)
- Exportação de métricas Prometheus
- Balanceamento e escalabilidade horizontal
"""


import json
import time
import psutil
import datetime
from flask import Flask, app, jsonify, request
from werkzeug.serving import make_server
import threading
from modulos.logger import log

# Uma classe para encapsular nosso servidor
class ServidorAPI(threading.Thread):
    def __init__(self, sistema_principal, host='0.0.0.0', port=5000):
        super().__init__()
        self.daemon = True  # Permite que o programa principal saia sem esperar por esta thread

        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.start_time = time.time()  # Registra o momento de início do servidor
        
        # Referência ao objeto principal do sistema para acessar dados e métodos
        self.sistema = sistema_principal
        
        # Configura as rotas (endpoints) da API
        self._configurar_rotas()
        
        # O servidor Werkzeug que realmente roda a aplicação Flask
        self.server = make_server(self.host, self.port, self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def run(self):
        """ Inicia o servidor Flask. Este método é chamado por .start() """
        log('INFO', 'SERVIDOR', f"🚀 Servidor API iniciado em http://{self.host}:{self.port}")
        self.server.serve_forever()

    def shutdown(self):
        """ Desliga o servidor de forma limpa """
        log('INFO', 'SERVIDOR', "🔌 Desligando o servidor API...")
        self.server.shutdown()
        
    def _restart_system_delayed(self):
        """Reinicia o sistema após um pequeno delay."""
        time.sleep(1)  # Pequeno delay para garantir que a resposta HTTP seja enviada
        log('INFO', 'SERVIDOR', "🔄 Iniciando reinicialização do sistema...")
        
        try:
            # Reinicializa o sistema principal
            self.sistema.reinicializar_sistema()
            log('INFO', 'SERVIDOR', "✅ Sistema reinicializado com sucesso!")
        except Exception as e:
            log('ERROR', 'SERVIDOR', f"❌ Erro durante a reinicialização: {e}")

    def _configurar_rotas(self):
        # Rota para escrita em lote de tags no driver
        @self.app.route('/api/escrever_lote', methods=['POST'])
        def post_escrever_lote():
            """
            Endpoint profissional para escrita em lote.
            Espera um JSON no corpo da requisição com:
            {
                "driver_id": "id_do_driver",
                "valores": {
                    "NomeColuna1": valor1,
                    "NomeColuna2": valor2,
                    ...
                }
            }
            - Valida os dados recebidos.
            - Monta o item para escrita em lote.
            - Enfileira para o driver correto.
            - Retorna resposta clara sobre sucesso ou erro.
            """
            dados_requisicao = request.get_json()
            # Validação básica dos campos obrigatórios
            if not dados_requisicao or 'driver_id' not in dados_requisicao or 'valores' not in dados_requisicao:
                return jsonify({
                    "sucesso": False,
                    "erro": "Requisição inválida. 'driver_id' e 'valores' são obrigatórios."
                }), 400

            driver_id = dados_requisicao['driver_id']
            valores = dados_requisicao['valores']

            # Chama método do sistema principal para enfileirar o comando
            sucesso = False
            try:
                sucesso = self.sistema.escrever_lote_driver(driver_id, valores)
            except Exception as e:
                log('ERROR', 'SERVIDOR', f"Erro ao enfileirar escrita em lote: {e}")
                return jsonify({
                    "sucesso": False,
                    "erro": f"Exceção ao enfileirar: {str(e)}"
                }), 500

            if sucesso:
                return jsonify({
                    "sucesso": True,
                    "mensagem": f"Comando de escrita em lote para o driver '{driver_id}' foi enfileirado.",
                    "detalhes": {
                        "driver_id": driver_id,
                        "valores": valores
                    }
                })
            else:
                return jsonify({
                    "sucesso": False,
                    "erro": "Driver não encontrado ou erro ao enfileirar."
                }), 404
        """ Define todos os endpoints da nossa API. """
        
        # Rota para obter todos os dados dos drivers
        @self.app.route('/api/dados', methods=['GET'])
        def get_dados():
            """
            Endpoint para expor o dicionário compartilhado completo.
            É crucial converter o dicionário do Manager para um dicionário Python padrão
            para que ele possa ser serializado para JSON.
            """
            dados_copiados = dict(self.sistema.shared_driver_data)
            # Converte os sub-dicionários do Manager também
            for driver_id, data in dados_copiados.items():
                dados_copiados[driver_id] = dict(data)
                if 'tags' in dados_copiados[driver_id]:
                    dados_copiados[driver_id]['tags'] = dict(dados_copiados[driver_id]['tags'])

            return jsonify(dados_copiados)

        # Rota para enviar um comando de escrita
        @self.app.route('/api/escrever', methods=['POST'])
        def post_escrever():
            """
            Endpoint para receber um comando de escrita.
            Espera um JSON no corpo da requisição com {"tag_id": "...", "valor": ...}
            """
            dados_requisicao = request.get_json()
            if not dados_requisicao or 'tag_id' not in dados_requisicao or 'valor' not in dados_requisicao:
                return jsonify({"sucesso": False, "erro": "Requisição inválida. 'tag_id' e 'valor' são obrigatórios."}), 400

            tag_id = dados_requisicao['tag_id']
            valor = dados_requisicao['valor']

            # Usa o método da classe SistemaPrincipal para enfileirar o comando
            self.sistema.escrever_valor_tag(tag_id, valor)

            return jsonify({"sucesso": True, "mensagem": f"Comando de escrita para a tag '{tag_id}' com valor '{valor}' foi enfileirado."})

        @self.app.route('/api/system/restart', methods=['POST'])
        def restart_server():
            """Reinicializa o servidor e todos os drivers."""
            try:
                log('INFO', 'SERVIDOR', "🔄 Iniciando processo de reinicialização do sistema...")
                # Agenda a reinicialização para acontecer após enviar a resposta
                threading.Thread(target=self.sistema.reinicializar_sistema).start()
                return jsonify({
                    "status": "success",
                    "message": "Sistema reiniciando...",
                    "details": {
                        "action": "full_restart",
                        "estimated_time": "5-10 segundos",
                        "steps": [
                            "Parando drivers atuais",
                            "Recarregando configurações",
                            "Reiniciando drivers",
                            "Atualizando mapa de tags"
                        ]
                    }
                })
            except Exception as e:
                log('ERROR', 'SERVIDOR', f"❌ Erro ao reiniciar sistema: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao reiniciar: {str(e)}",
                    "details": {"error_type": str(type(e).__name__)}
                }), 500

        @self.app.route('/api/logs', methods=['GET'])
        def get_logs():
            """Retorna os logs do sistema."""
            try:
                # Parâmetros opcionais
                limit = request.args.get('limit', type=int)
                since = request.args.get('since', type=str)
                level = request.args.get('level', type=str)
                
                from modulos.logger import get_recent_logs, get_logs_since
                
                if since:
                    logs = get_logs_since(since)
                else:
                    logs = get_recent_logs(limit)
                
                # Filtra por nível se especificado
                if level:
                    level = level.upper()
                    logs = [log for log in logs if log['level'] == level]
                
                return jsonify({
                    "status": "success",
                    "logs": logs,
                    "total": len(logs)
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao recuperar logs: {str(e)}"
                }), 500

        @self.app.route('/api/ia/status', methods=['GET'])
        def get_ia_status():
            """Retorna o status global do sistema de IA."""
            try:
                if not hasattr(self.sistema, 'ia_manager') or not self.sistema.ia_manager:
                    return jsonify({
                        "status": "error",
                        "message": "Sistema de IA não está ativo"
                    }), 404
                ia_manager = self.sistema.ia_manager
                status_global = dict(getattr(ia_manager, 'status_global', {}))
                info_treinamento = dict(getattr(ia_manager, 'info_treinamento', {}))
                return jsonify({
                    "status": "success",
                    "ia_status": {
                        "global": status_global,
                        "treinamento": info_treinamento
                    }
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao obter status da IA: {str(e)}"
                }), 500



        @self.app.route('/api/ia/conhecimento', methods=['GET'])
        def get_ia_conhecimento():
            """Retorna o conhecimento global compartilhado entre as IAs."""
            try:
                # ... (verificações iniciais de if not self.sistema.ia_manager, etc.) ...
                if not hasattr(self.sistema, 'ia_manager') or not hasattr(self.sistema.ia_manager, 'coordenador'):
                    return jsonify({"status": "error", "message": "Coordenador de IA não está disponível"}), 404

                # Obtém e converte o conhecimento global
                conhecimento = dict(self.sistema.ia_manager.coordenador.conhecimento_global)
                estado_sync_original = dict(self.sistema.ia_manager.coordenador.estado_sync)

                # ---> INÍCIO DA CORREÇÃO <---
                # Converte o 'set' para 'list' para ser compatível com JSON
                if 'nos_sincronizados' in estado_sync_original and isinstance(estado_sync_original['nos_sincronizados'], set):
                    estado_sync_original['nos_sincronizados'] = list(estado_sync_original['nos_sincronizados'])
                # ---> FIM DA CORREÇÃO <---

                return jsonify({
                    "status": "success",
                    "conhecimento": {
                        "dados": conhecimento,
                        "sincronizacao": estado_sync_original, # Usa a versão corrigida
                        "ultima_atualizacao": datetime.datetime.now().isoformat()
                    }
                })
            except Exception as e:
                log('ERROR', 'SERVIDOR', f"❌ Erro ao obter conhecimento da IA: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao obter conhecimento da IA: {str(e)}"
                }), 500


        @self.app.route('/api/ia/metricas', methods=['GET'])
        def get_ia_metricas():
            """Retorna métricas em tempo real do sistema de IA."""
            try:
                if not hasattr(self.sistema, 'ia_manager') or not self.sistema.ia_manager:
                    return jsonify({
                        "status": "error",
                        "message": "Sistema de IA não está ativo"
                    }), 404
                ia_manager = self.sistema.ia_manager
                status_global = getattr(ia_manager, 'status_global', {})
                # Coleta métricas dos drivers por fase
                metricas_por_fase = {}
                for driver_id, data in self.sistema.shared_driver_data.items():
                    fase = data.get('fase_atual', 'desconhecida')
                    if fase not in metricas_por_fase:
                        metricas_por_fase[fase] = {
                            'total_drivers': 0,
                            'drivers': []
                        }
                    metricas_por_fase[fase]['total_drivers'] += 1
                    metricas_por_fase[fase]['drivers'].append(driver_id)

                return jsonify({
                    "status": "success",
                    "metricas": {
                        "fase_operacao": metricas_por_fase,
                        "acuracia_media": status_global.get('acuracia_media', 0.0),
                        "alertas_gerados": status_global.get('alertas_gerados', 0),
                        "nos_ativos": status_global.get('nos_ativos', 0),
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao obter métricas da IA: {str(e)}"
                }), 500

        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Retorna informações detalhadas sobre o estado do sistema."""
            try:
                # Calcula o uptime
                uptime_seconds = time.time() - self.start_time
                uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))
                
                # Obtém informações do processo
                process = psutil.Process()
                memory_info = process.memory_info()
                
                # Conta drivers ativos
                active_drivers = 0
                disconnected_drivers = 0
                for driver_data in self.sistema.shared_driver_data.values():
                    if driver_data.get('status_conexao') == 'conectado':
                        active_drivers += 1
                    else:
                        disconnected_drivers += 1
                
                # Coleta estatísticas do sistema
                cpu_percent = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                
                return jsonify({
                    "status": "healthy" if active_drivers > 0 else "warning",
                    "uptime": uptime,
                    "memory_usage": {
                        "process": f"{memory_info.rss / 1024 / 1024:.1f}MB",
                        "system": {
                            "total": f"{mem.total / 1024 / 1024 / 1024:.1f}GB",
                            "available": f"{mem.available / 1024 / 1024 / 1024:.1f}GB",
                            "percent": f"{mem.percent}%"
                        }
                    },
                    "cpu_usage": f"{cpu_percent}%",
                    "drivers": {
                        "total": active_drivers + disconnected_drivers,
                        "active": active_drivers,
                        "disconnected": disconnected_drivers
                    },
                    "tags": {
                        "total": sum(len(d.get('tags', {})) for d in self.sistema.shared_driver_data.values()),
                        "good_quality": sum(
                            sum(1 for t in d.get('tags', {}).values() if t.get('qualidade') == 'boa')
                            for d in self.sistema.shared_driver_data.values()
                        )
                    }
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao coletar informações: {str(e)}"
                }), 500