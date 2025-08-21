# -*- coding: utf-8 -*-
import sys
import time
import json
import csv
from datetime import datetime
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QHeaderView, QLabel, QTextEdit, QFrame, QSplitter, QAction, QMenu,
    QInputDialog, QMessageBox, QPushButton, QToolBar, QStatusBar, QLineEdit,
    QComboBox, QTabWidget, QGroupBox, QDialog, QFileDialog, QGridLayout,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import (
    QAbstractTableModel, Qt, QTimer, QSortFilterProxyModel, QSize, QThread,
    pyqtSignal, QObject
)
from PyQt5.QtGui import QColor, QFont, QIcon

# ==============================================================================
# ESTILO DA APLICAÇÃO (STYLESHEET - QSS)
# ==============================================================================
MODERN_STYLESHEET = """
    /* ... (O mesmo stylesheet da resposta anterior, mantido por brevidade) ... */
    QMainWindow, QWidget {
        background-color: #2B2B2B; color: #D3D3D3; font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt;
    }
    QTableView {
        background-color: #2B2B2B; border: 1px solid #3C3C3C; gridline-color: #3C3C3C;
        alternate-background-color: #323232; selection-background-color: #007ACC; selection-color: #FFFFFF;
    }
    QTableView::item { padding: 5px; border: none; }
    QHeaderView::section {
        background-color: #3C3C3C; color: #D3D3D3; padding: 6px; border: 1px solid #4A4A4A; font-weight: bold;
    }
    QGroupBox {
        border: 1px solid #3C3C3C; border-radius: 5px; margin-top: 0.5em; font-weight: bold;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
    QPushButton {
        background-color: #3C3C3C; border: 1px solid #5A5A5A; padding: 6px 12px; border-radius: 4px;
    }
    QPushButton:hover { background-color: #4A4A4A; border-color: #007ACC; }
    QPushButton:pressed { background-color: #2A2A2A; }
    QLineEdit, QComboBox {
        border: 1px solid #3C3C3C; border-radius: 4px; padding: 5px; background-color: #212121;
    }
    QLineEdit:focus, QComboBox:focus { border-color: #007ACC; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView { background-color: #3C3C3C; border: 1px solid #5A5A5A; selection-background-color: #007ACC; }
    QTabWidget::pane { border: 1px solid #3C3C3C; }
    QTabBar::tab {
        background-color: #2B2B2B; border: 1px solid #3C3C3C; padding: 8px 15px;
        border-top-left-radius: 4px; border-top-right-radius: 4px;
    }
    QTabBar::tab:selected { background-color: #3C3C3C; border-bottom-color: #3C3C3C; }
    QTabBar::tab:!selected:hover { background-color: #353535; }
    QSplitter::handle { background: #3C3C3C; }
    QSplitter::handle:hover { background: #007ACC; }
    QSplitter::handle:horizontal { width: 2px; }
    QSplitter::handle:vertical { height: 2px; }
    QStatusBar { background-color: #007ACC; color: white; font-weight: bold; }
    QStatusBar::item { border: none; }
    QTextEdit { background-color: #212121; border: 1px solid #3C3C3C; font-family: 'Consolas', 'Courier New', monospace; }
    QToolBar { background-color: #333333; border: none; padding: 2px; spacing: 5px; }
    QToolButton { background-color: transparent; color: #D3D3D3; padding: 5px; margin: 2px; }
    QToolButton:hover { background-color: #4A4A4A; border-radius: 4px; }
    QListWidget { background-color: #2B2B2B; border: 1px solid #3C3C3C; }
    QListWidget::item { padding: 6px; }
    QListWidget::item:hover { background-color: #353535; }
    QListWidget::item:selected { background-color: #007ACC; color: white; }
    #KPI_Label { font-size: 14pt; font-weight: bold; }
    #KPI_Value { font-size: 18pt; font-weight: bold; color: #2ECC71; }
"""

# ==============================================================================
# WORKER E API CLIENT (Idênticos à resposta anterior, mantidos por completude)
# ==============================================================================
class DataWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    # Contadores para erros repetidos
    error_counters = {
        'ia_status': 0,
        'ia_metricas': 0,
        'ia_conhecimento': 0
    }
    def run(self):
        print("[DEBUG] DataWorker.run: INICIO")
        try:
            results = {}
            endpoints = {
                'main_data': self.api_client.get_data,
                'logs': self.api_client.get_logs,
                'ia_status': self.api_client.get_ia_status,
                'ia_metricas': self.api_client.get_ia_metricas,
                'ia_conhecimento': self.api_client.get_ia_conhecimento,
            }
            for key, func in endpoints.items():
                try:
                    data, error = func()
                except Exception as e:
                    print(f"[DEBUG] DataWorker.run: erro em {key}: {e}")
                    data, error = None, str(e)
                if error:
                    if key in self.error_counters:
                        self.error_counters[key] += 1
                        if self.error_counters[key] == 1 or self.error_counters[key] % 10 == 0:
                            print(f"[IMPORTANTE] {self.error_counters[key]}x Falha ao buscar dados para '{key}': {error}")
                    elif key == 'main_data':
                        print(f"[IMPORTANTE] Falha ao buscar dados principais: {error}")
                    results[key] = None
                else:
                    results[key] = data
            if results['main_data'] is None:
                self.error.emit("Falha ao obter dados principais do servidor.")
                print("[DEBUG] DataWorker.run: FIM (erro)")
                return
            else:
                self.finished.emit(results)
                print("[DEBUG] DataWorker.run: FIM (sucesso)")
                return
        except Exception as e:
            self.error.emit(f"Erro inesperado no worker: {e}")
            print(f"[ERRO] DataWorker.run: {e}")
            print("[DEBUG] DataWorker.run: FIM (exception)")
            return

class ApiClient:
    """Cliente para interagir com a API do servidor."""
    def __init__(self, base_url):
        # Corrige para garantir que o endereço está correto e sem barras duplas
        self.base_url = base_url.rstrip('/')

    def _request(self, method, endpoint, **kwargs):
        """Método genérico para fazer requisições."""
        try:
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            url = f"{self.base_url}{endpoint}"
            # Print apenas para requisições principais
            if endpoint in ['/api/dados', '/api/logs']:
                print(f"[INFO] Requisitando URL: {url}")
            response = requests.request(method, url, timeout=5, **kwargs)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.ConnectionError as e:
            print(f"[ERRO] ConnectionError: {e}")
            return None, "Servidor offline ou inacessível. Verifique se 'main.py' está rodando."
        except requests.exceptions.Timeout as e:
            print(f"[ERRO] Timeout: {e}")
            return None, f"Tempo de requisição esgotado para {endpoint}."
        except requests.exceptions.RequestException as e:
            error_details = f" (Detalhe: {e.response.text})" if hasattr(e, 'response') and e.response else ""
            # Print apenas para erros importantes
            if endpoint in ['/api/dados', '/api/logs']:
                print(f"[ERRO] RequestException em {endpoint}: {e}")
            return None, f"Erro na requisição para {endpoint}: {e}{error_details}"

    def get_data(self): return self._request('get', '/api/dados')
    def get_ia_status(self): return self._request('get', '/api/ia/status')
    def get_ia_metricas(self): return self._request('get', '/api/ia/metricas')
    def get_ia_conhecimento(self): return self._request('get', '/api/ia/conhecimento')
    def get_logs(self):
        data, error = self._request('get', '/api/logs', params={'limit': 200})
        return (data.get('logs', []) if data else [], error)
    def write_tag(self, tag_id, value): return self._request('post', '/api/escrever', json={"tag_id": tag_id, "valor": value})
    def restart_system(self): return self._request('post', '/api/system/restart')
    def get_health(self): return self._request('get', '/api/health')


# ==============================================================================
# MODELO DE TABELA (Idêntico, para a aba de Tags)
# ==============================================================================
class TagTableModel(QAbstractTableModel):
    # ... (código idêntico ao da resposta anterior, mantido por completude) ...
    def __init__(self):
        super().__init__()
        self._data = []
        self._headers = ['Driver', 'Status', 'Nome da Tag', 'Valor', 'Qualidade', 'Timestamp', 'Tipo', 'Endereço', 'ID da Tag', 'Log']
        self.quality_colors = {
            'boa': QColor("#2ECC71"), 'ruim': QColor("#E74C3C"), 'incerta': QColor("#F1C40F")
        }
    def rowCount(self, parent=None): return len(self._data)
    def columnCount(self, parent=None): return len(self._headers)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        try:
            row_data = self._data[index.row()]
            col = index.column()
            if role == Qt.DisplayRole: return str(row_data[col])
            if role == Qt.ForegroundRole:
                if col == 4: return self.quality_colors.get(row_data[col].lower(), QColor("#D3D3D3"))
                if row_data[1] != 'conectado': return QColor("#E74C3C")
                return QColor("#D3D3D3")
            if role == Qt.TextAlignmentRole and col == 3: return Qt.AlignRight | Qt.AlignVCenter
        except (IndexError, KeyError) as e:
            # Apenas printa erro importante uma vez a cada 10 ocorrências
            if not hasattr(self, 'error_count'): self.error_count = 0
            self.error_count += 1
            if self.error_count == 1 or self.error_count % 10 == 0:
                print(f"[ERRO] TagTableModel.data: {self.error_count}x {e} | Index: {index.row()},{index.column()}")
            return None
        return None
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal: return self._headers[section]
        return None
    def update_data(self, new_data):
        self.beginResetModel()
        self._data = []
        if not new_data:
            self.endResetModel()
            return
        try:
            for driver_id, driver_data in new_data.items():
                nome_driver = driver_data.get('config', {}).get('nome', driver_id)
                status_conexao = driver_data.get('status_conexao', 'desconhecido')
                tags = driver_data.get('tags', {})
                if not tags:
                    self._data.append([nome_driver, status_conexao, 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'Nenhuma tag configurada'])
                else:
                    for tag_id, tag_info in tags.items():
                        log_msg = tag_info.get('log', '')
                        if not log_msg and status_conexao != 'conectado':
                            log_msg = driver_data.get('detalhe', 'Driver desconectado')
                        row = [
                            nome_driver, status_conexao, tag_info.get('nome', 'N/A'), str(tag_info.get('valor', '')),
                            tag_info.get('qualidade', 'incerta'), tag_info.get('timestamp', 'N/A'), tag_info.get('tipo', 'N/A'),
                            tag_info.get('endereco', 'N/A'), tag_id, log_msg
                        ]
                        self._data.append(row)
        except Exception as e:
            print(f"[ERRO] TagTableModel.update_data: {e}")
        self.endResetModel()
    def get_tag_info(self, row):
        if 0 <= row < len(self._data): return dict(zip(self._headers, self._data[row]))
        return None


# ==============================================================================
# JANELA PRINCIPAL DA APLICAÇÃO
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("InLogic Studio - Supervisor")
        self.setStyleSheet(MODERN_STYLESHEET)
        
        # --- Abrir janela ocupando toda a tela do Windows ---
        self.showMaximized()
        
        self.api_client = ApiClient("http://127.0.0.1:5000")
        self.all_driver_data = {} # Cache dos dados para o painel de detalhes
        self.is_shutting_down = False

        # --- Chama setup_ui depois de showMaximized para garantir widgets prontos ---
        self.setup_ui()
        self.setup_worker()
        self.setup_timers()
        self.force_update()
        
    def setup_ui(self):
        """Configura todos os widgets e layouts da UI."""
        self.setMinimumSize(1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.create_toolbar()
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        self.tab_widget.addTab(self.create_tags_tab(), "📊 Monitoramento de Tags")
        self.tab_widget.addTab(self.create_ia_dashboard_tab(), "🧠 Dashboard IA")
        self.tab_widget.addTab(self.create_logs_tab(), "📜 Logs do Sistema")
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Iniciando...")
        self.last_update_label = QLabel("Última atualização: --:--:--")
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.last_update_label)

    def center_window(self):
        # Este método não é mais necessário, pois a janela já abre maximizada
        pass

    # --- Criação das Abas ---
    def create_tags_tab(self):
        # (código idêntico ao da resposta anterior)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        filter_layout = QHBoxLayout()
        filter_group = QGroupBox("Filtros")
        filter_group.setLayout(filter_layout)
        self.tags_search_box = QLineEdit()
        self.tags_search_box.setPlaceholderText("Buscar em todas as colunas...")
        self.tags_filter_driver = QComboBox()
        self.tags_filter_status = QComboBox()
        self.tags_filter_quality = QComboBox()
        filter_layout.addWidget(QLabel("Busca:")); filter_layout.addWidget(self.tags_search_box)
        filter_layout.addWidget(QLabel("Driver:")); filter_layout.addWidget(self.tags_filter_driver)
        filter_layout.addWidget(QLabel("Status:")); filter_layout.addWidget(self.tags_filter_status)
        filter_layout.addWidget(QLabel("Qualidade:")); filter_layout.addWidget(self.tags_filter_quality)
        self.tags_table_view = QTableView()
        self.tags_table_model = TagTableModel()
        self.tags_proxy_model = QSortFilterProxyModel()
        self.tags_proxy_model.setSourceModel(self.tags_table_model)
        self.tags_table_view.setModel(self.tags_proxy_model)
        self.configure_table(self.tags_table_view)
        self.tags_table_view.setColumnHidden(6, True); self.tags_table_view.setColumnHidden(7, True); self.tags_table_view.setColumnHidden(8, True)
        self.tags_search_box.textChanged.connect(self.filter_tags_table)
        self.tags_filter_driver.currentTextChanged.connect(self.filter_tags_table)
        self.tags_filter_status.currentTextChanged.connect(self.filter_tags_table)
        self.tags_filter_quality.currentTextChanged.connect(self.filter_tags_table)
        self.tags_table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tags_table_view.customContextMenuRequested.connect(self.open_tags_context_menu)
        layout.addWidget(filter_group)
        layout.addWidget(self.tags_table_view)
        return widget

    def create_ia_dashboard_tab(self):
        """Cria o novo dashboard de IA."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 1. Painel de Controle Global (KPIs)
        kpi_panel = self.create_ia_kpi_panel()
        layout.addWidget(kpi_panel)

        # Splitter principal para organizar os outros painéis
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 2. Painel da Esquerda: Visão Operacional e Treinamento
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        operational_panel = self.create_ia_operational_panel()
        training_panel = self.create_ia_training_panel()
        
        left_layout.addWidget(operational_panel)
        left_layout.addWidget(training_panel)
        
        # 3. Painel da Direita: Detalhes do Item Selecionado
        details_panel = self.create_ia_details_panel()

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(details_panel)
        main_splitter.setSizes([600, 400]) # Tamanhos iniciais

        layout.addWidget(main_splitter)
        return widget

    def create_logs_tab(self):
        # (código idêntico ao da resposta anterior)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        log_group = QGroupBox("Logs em Tempo Real (últimos 200 eventos)")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        layout.addWidget(log_group)
        return widget

    # --- Criação dos Painéis do Dashboard de IA ---
    def create_ia_kpi_panel(self):
        kpi_group = QGroupBox("Painel de Controle Global")
        layout = QGridLayout(kpi_group)
        self.ia_kpi_labels = {}
        kpis = {
            "nos_ativos": ("🧠 Nós Ativos", "#3498DB"),
            "acuracia_media": ("🎯 Acurácia Média", "#2ECC71"),
            "alertas_gerados": ("⚠️ Alertas Gerados", "#F1C40F"),
            "drivers_conectados": ("🔌 Drivers Conectados", "#2ECC71")
        }
        col = 0
        for key, (text, color) in kpis.items():
            label = QLabel(text)
            label.setObjectName("KPI_Label")
            value = QLabel("N/A")
            value.setObjectName("KPI_Value")
            value.setStyleSheet(f"color: {color};")
            layout.addWidget(label, 0, col)
            layout.addWidget(value, 1, col)
            self.ia_kpi_labels[key] = value
            col += 1
        return kpi_group

    def create_ia_operational_panel(self):
        op_group = QGroupBox("Visão Operacional por Fase")
        layout = QVBoxLayout(op_group)
        self.ia_phase_lists = {}
        # As chaves aqui devem corresponder às fases retornadas pela sua API
        phases = ["monitorando", "otimizando", "aprendendo", "desconhecida"]
        for phase in phases:
            phase_group = QGroupBox(phase.capitalize())
            phase_layout = QVBoxLayout(phase_group)
            list_widget = QListWidget()
            list_widget.currentItemChanged.connect(self.update_ia_details_panel)
            self.ia_phase_lists[phase] = list_widget
            phase_layout.addWidget(list_widget)
            layout.addWidget(phase_group)
        return op_group

    def create_ia_training_panel(self):
        train_group = QGroupBox("Treinamento e Conhecimento")
        layout = QVBoxLayout(train_group)
        self.ia_training_info = QTextEdit()
        self.ia_training_info.setReadOnly(True)
        layout.addWidget(self.ia_training_info)
        return train_group

    def create_ia_details_panel(self):
        details_group = QGroupBox("Detalhes do Driver Selecionado")
        layout = QVBoxLayout(details_group)
        self.ia_details_text = QTextEdit()
        self.ia_details_text.setReadOnly(True)
        layout.addWidget(self.ia_details_text)
        return details_group

    # --- Lógica de Atualização da UI ---
    def process_data(self, data):
        """Processa todos os dados recebidos do worker."""
        try:
            if not data or not isinstance(data, dict):
                self.handle_error("Nenhum dado recebido do servidor.")
                if not self.data_timer.isActive():
                    self.data_timer.start()
                return
            if not data.get('main_data'):
                self.handle_error("Dados principais dos drivers/tags não recebidos.")
                if not self.data_timer.isActive():
                    self.data_timer.start()
                return
            self.status_label.setText("✔️ Conectado")
            self.last_update_label.setText(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
            self.all_driver_data = data['main_data']
            self.update_tags_tab(data.get('main_data'))
            self.update_ia_dashboard_tab(data)
            self.update_logs_tab(data.get('logs'))
        except Exception as e:
            print(f"ERROR in process_data: {e}")
            self.handle_error(f"Erro ao processar dados: {e}")
            if not self.data_timer.isActive():
                self.data_timer.start()

    def update_tags_tab(self, main_data):
        if main_data is None: return
        self.tags_table_model.update_data(main_data)
        self.update_tag_filters(self.tags_table_model._data)

    def update_ia_dashboard_tab(self, all_data):
        """Atualiza todos os painéis do dashboard de IA."""
        # Extrai os dados necessários
        ia_status = all_data.get('ia_status', {}).get('ia_status', {}) if all_data.get('ia_status') else {}
        ia_metricas = all_data.get('ia_metricas', {}).get('metricas', {}) if all_data.get('ia_metricas') else {}
        ia_conhecimento = all_data.get('ia_conhecimento', {}).get('conhecimento', {}) if all_data.get('ia_conhecimento') else {}
        
        # 1. Atualizar KPIs
        kpi_data = {
            'nos_ativos': ia_metricas.get('nos_ativos', 'N/A'),
            'acuracia_media': f"{ia_metricas.get('acuracia_media', 0.0):.2f}%",
            'alertas_gerados': ia_metricas.get('alertas_gerados', 'N/A'),
            'drivers_conectados': f"{len([d for d in self.all_driver_data.values() if d.get('status_conexao') == 'conectado'])} / {len(self.all_driver_data)}"
        }
        for key, value_widget in self.ia_kpi_labels.items():
            value_widget.setText(str(kpi_data.get(key, "N/A")))

        # 2. Atualizar Visão Operacional
        fase_operacao = ia_metricas.get('fase_operacao', {})
        # Limpa todas as listas primeiro
        for list_widget in self.ia_phase_lists.values():
            list_widget.clear()
        # Preenche com os dados mais recentes
        for fase, info in fase_operacao.items():
            if fase in self.ia_phase_lists:
                for driver_id in info.get('drivers', []):
                    # Adiciona o nome do driver se disponível, senão o ID
                    driver_name = self.all_driver_data.get(driver_id, {}).get('config', {}).get('nome', driver_id)
                    item = QListWidgetItem(driver_name)
                    item.setData(Qt.UserRole, driver_id) # Armazena o ID no item
                    self.ia_phase_lists[fase].addItem(item)
                    
        # 3. Atualizar Painel de Treinamento
        training_info = ia_status.get('treinamento', {})
        sync_info = ia_conhecimento.get('sincronizacao', {})
        html = "<h3>Treinamento de Modelos</h3>"
        html += f"<p><b>Modelos Ativos:</b> {len(training_info.get('modelos_ativos', []))}</p>"
        html += f"<p><b>Fila de Treinamento:</b> {training_info.get('fila_treinamento', 'N/A')}</p>"
        html += "<h3>Sincronização de Conhecimento</h3>"
        html += f"<p><b>Última Atualização:</b> {ia_conhecimento.get('ultima_atualizacao', 'N/A')}</p>"
        html += f"<p><b>Nós Sincronizados:</b> {len(sync_info.get('nos_sincronizados', []))}</p>"
        self.ia_training_info.setHtml(html)

    def update_ia_details_panel(self, current_item, previous_item):
        """Atualiza o painel de detalhes quando um item é selecionado."""
        if not current_item:
            self.ia_details_text.clear()
            return
            
        driver_id = current_item.data(Qt.UserRole)
        driver_data = self.all_driver_data.get(driver_id, {})
        
        # Aqui, você pode formatar e exibir os dados do driver como quiser.
        # Idealmente, você combinaria dados de vários endpoints para este driver.
        # Exemplo simples:
        details_html = f"<h2>{driver_data.get('config', {}).get('nome', driver_id)}</h2>"
        details_html += f"<h4>ID: {driver_id}</h4><hr>"
        
        # Transforma o dicionário em uma lista HTML bonita
        def format_dict_to_html(d, indent=0):
            html = "<ul>"
            for k, v in d.items():
                if isinstance(v, dict):
                    html += f"<li><b>{str(k).replace('_', ' ').title()}:</b>{format_dict_to_html(v, indent+1)}</li>"
                elif isinstance(v, list):
                     html += f"<li><b>{str(k).replace('_', ' ').title()}:</b><ul>{''.join(f'<li>{item}</li>' for item in v)}</ul></li>"
                else:
                    html += f"<li><b>{str(k).replace('_', ' ').title()}:</b> {v}</li>"
            html += "</ul>"
            return html

        details_html += format_dict_to_html(driver_data)
        self.ia_details_text.setHtml(details_html)

    def update_logs_tab(self, logs):
        if not logs: return
        # (código idêntico ao da resposta anterior)
        try:
            log_colors = {
                'ERROR': '#E74C3C', 'WARN': '#F1C40F', 'INFO': '#2ECC71', 'DEBUG': '#3498DB'
            }
            html_lines = []
            for log in reversed(logs):
                color = log_colors.get(log['level'], '#D3D3D3')
                line = (f"<span style='color:#888;'>{log['timestamp']}</span> | "
                        f"<b style='color:{color};'>{log['level']:<5}</b> | "
                        f"<span style='color:#00A0A0;'>{log['source']:<15}</span> | "
                        f"{log['message']}")
                html_lines.append(line)
            
            self.log_area.setHtml("<pre>" + "<br>".join(html_lines) + "</pre>")
        except Exception as e:
            print(f"ERROR in update_log_area: {e}")


    # --- Métodos de Setup e Lógica Auxiliar (a maioria idêntica) ---
    def setup_worker(self):
        # --- Corrige para garantir que o worker é reiniciado a cada atualização ---
        self.thread = QThread()
        self.worker = DataWorker(self.api_client)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.process_data)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        # --- Adiciona reconexão automática ---
        self.thread.finished.connect(self.on_worker_finished)

    def on_worker_finished(self):
        # Permite que o timer continue disparando atualizações, mesmo após erro
        if not self.is_shutting_down:
            if not self.data_timer.isActive():
                self.data_timer.start()

    def setup_timers(self):
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.trigger_update)
        self.data_timer.start(2000)  # Intervalo de 2 segundos para evitar flood

    def trigger_update(self):
        print(f"[DEBUG] trigger_update: thread rodando? {hasattr(self, 'thread') and self.thread.isRunning()}")
        if self.is_shutting_down:
            return
        if hasattr(self, 'thread') and self.thread.isRunning():
            return
        # Destroi thread anterior se existir
        if hasattr(self, 'thread') and not self.thread.isRunning():
            try:
                self.thread.quit()
                self.thread.wait(1000)
                del self.thread
                del self.worker
            except Exception as e:
                print(f"[DEBUG] erro ao destruir thread: {e}")
        # Cria nova thread/worker
        self.thread = QThread()
        self.worker = DataWorker(self.api_client)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.process_data)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.on_worker_finished)
        self.thread.start()
        print("[DEBUG] trigger_update: nova thread/worker criada e iniciada.")

    def on_worker_finished(self):
        print("[DEBUG] on_worker_finished: reiniciando timer para nova tentativa.")
        if not self.is_shutting_down:
            self.data_timer.start()  # SEMPRE reinicia o timer

    def handle_error(self, error_msg):
        self.status_label.setText(f"🔄 Reconectando... {error_msg.split('(Detalhe:')[0]}")
        print(f"API_ERROR: {error_msg}")
        # Não para o timer nunca

    def configure_table(self, table_view):
        table_view.setSortingEnabled(True)
        table_view.setAlternatingRowColors(True)
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table_view.horizontalHeader().setStretchLastSection(True)
        table_view.verticalHeader().setVisible(False)
        table_view.setSelectionBehavior(QTableView.SelectRows)
        table_view.setSelectionMode(QTableView.SingleSelection)
        table_view.resizeColumnsToContents()

    def update_tag_filters(self, data):
        # (código idêntico ao da resposta anterior)
        try:
            drivers, statuses, qualities = set(), set(), set()
            for row in data:
                drivers.add(row[0]); statuses.add(row[1]); qualities.add(row[4])
            self.update_combo_box(self.tags_filter_driver, sorted(list(drivers)), "Todos os Drivers")
            self.update_combo_box(self.tags_filter_status, sorted(list(statuses)), "Todos os Status")
            self.update_combo_box(self.tags_filter_quality, sorted(list(qualities)), "Todas as Qualidades")
        except Exception as e:
            print(f"ERROR in update_tag_filters: {e}")

    def update_combo_box(self, combo, items, default_text):
        # (código idêntico ao da resposta anterior)
        current_text = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(default_text)
        combo.addItems(items)
        index = combo.findText(current_text)
        if index != -1: combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def filter_tags_table(self):
        # (código idêntico ao da resposta anterior)
        try:
            search_text = self.tags_search_box.text().lower()
            driver = self.tags_filter_driver.currentText()
            status = self.tags_filter_status.currentText()
            quality = self.tags_filter_quality.currentText()
            def filter_row(row_idx):
                row_data = self.tags_table_model._data[row_idx]
                if driver != "Todos os Drivers" and row_data[0] != driver: return False
                if status != "Todos os Status" and row_data[1] != status: return False
                if quality != "Todas as Qualidades" and row_data[4] != quality: return False
                if search_text and search_text not in " ".join(map(str, row_data)).lower(): return False
                return True
            for row in range(self.tags_table_model.rowCount()):
                self.tags_table_view.setRowHidden(row, not filter_row(row))
        except Exception as e:
            print(f"ERROR in filter_tags_table: {e}")

    # --- Métodos de Ações e Contexto (a maioria idêntica) ---
    def create_toolbar(self):
        # (código idêntico ao da resposta anterior)
        toolbar = QToolBar("Ações Principais")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        refresh_action = QAction("🔄 Atualizar Agora", self); refresh_action.triggered.connect(self.force_update)
        restart_action = QAction("🔃 Reiniciar Sistema", self); restart_action.triggered.connect(self.confirm_restart_system)
        health_action = QAction("💓 Status do Sistema", self); health_action.triggered.connect(self.check_system_health)
        toolbar.addAction(refresh_action); toolbar.addSeparator(); toolbar.addAction(restart_action); toolbar.addAction(health_action)

    def open_tags_context_menu(self, position):
        # (código idêntico ao da resposta anterior)
        try:
            indexes = self.tags_table_view.selectedIndexes()
            if not indexes: return
            source_index = self.tags_proxy_model.mapToSource(indexes[0])
            tag_info = self.tags_table_model.get_tag_info(source_index.row())
            if not tag_info: return
            menu = QMenu()
            write_action = QAction(f"✍️ Escrever na Tag '{tag_info['Nome da Tag']}'", self)
            write_action.triggered.connect(lambda: self.write_tag_dialog(tag_info))
            menu.addAction(write_action)
            copy_menu = menu.addMenu("📋 Copiar")
            for key, value in tag_info.items():
                action = QAction(f"Copiar {key}", self)
                action.triggered.connect(lambda _, v=value: QApplication.clipboard().setText(str(v)))
                copy_menu.addAction(action)
            menu.exec_(self.tags_table_view.viewport().mapToGlobal(position))
        except Exception as e:
            print(f"ERROR in open_tags_context_menu: {e}")

    def write_tag_dialog(self, tag_info):
        # (código idêntico ao da resposta anterior)
        try:
            new_value, ok = QInputDialog.getText(self, "Escrever Valor na Tag",
                f"<b>Tag:</b> {tag_info['Nome da Tag']} (ID: {tag_info['ID da Tag']})<br>"
                f"<b>Valor Atual:</b> {tag_info['Valor']}<br><br>Digite o novo valor:",
                QLineEdit.Normal, str(tag_info['Valor']))
            if ok and new_value != str(tag_info['Valor']):
                result, error = self.api_client.write_tag(tag_info['ID da Tag'], new_value)
                if error: QMessageBox.critical(self, "Erro na Escrita", f"Falha ao enviar comando:\n{error}")
                else: QMessageBox.information(self, "Sucesso", result.get("mensagem", "Comando enfileirado!"))
                self.force_update()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro inesperado: {e}")
            
    def confirm_restart_system(self):
        # (código idêntico ao da resposta anterior)
        reply = QMessageBox.question(self, 'Confirmação', "Tem certeza que deseja reiniciar todo o sistema?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes: self.restart_system()
    
    def restart_system(self):
        # (código idêntico ao da resposta anterior)
        self.data_timer.stop()
        self.status_label.setText("🔃 Reiniciando o sistema...")
        result, error = self.api_client.restart_system()
        if error:
            QMessageBox.critical(self, "Erro", f"Não foi possível reiniciar:\n{error}")
            self.data_timer.start()
        else:
            QMessageBox.information(self, "Sucesso", "Comando de reinicialização enviado.\nAguarde 10 segundos para a reconexão.")
            QTimer.singleShot(10000, self.post_restart_connect)
    
    def post_restart_connect(self):
        # (código idêntico ao da resposta anterior)
        self.status_label.setText("🔄 Tentando reconectar...")
        self.data_timer.start()
        self.force_update()

    def check_system_health(self):
        # (código idêntico ao da resposta anterior)
        health_data, error = self.api_client.get_health()
        if error:
            QMessageBox.warning(self, "Erro", f"Não foi possível obter status de saúde:\n{error}")
            return
        try:
            msg = (f"<b>Status:</b> <font color='{'#2ECC71' if health_data['status'] == 'healthy' else '#E74C3C'}'>{health_data['status'].capitalize()}</font><br>"
                   f"<b>Uptime:</b> {health_data['uptime']}<br>"
                   f"<b>CPU:</b> {health_data['cpu_usage']}<br>"
                   f"<b>Memória:</b> {health_data['memory_usage']['process']}<br>"
                   f"<b>Drivers:</b> {health_data['drivers']['active']} ativos / {health_data['drivers']['disconnected']} offline")
            QMessageBox.information(self, "Status de Saúde do Sistema", msg)
        except (KeyError, TypeError):
            QMessageBox.warning(self, "Dados Incompletos", "Dados de saúde recebidos estão malformados.")

    def closeEvent(self, event):
        # (código idêntico ao da resposta anterior)
        self.is_shutting_down = True
        self.data_timer.stop()
        if self.thread.isRunning():
            self.thread.quit()
            if not self.thread.wait(3000):
                self.thread.terminate()
        event.accept()

    def force_update(self):
        self.status_label.setText("🔄 Atualizando dados...")
        self.trigger_update()

# ==============================================================================
# PONTO DE ENTRADA DA APLICAÇÃO
# ==============================================================================
if __name__ == '__main__':
    # Diagnóstico: Mostra qual URL está sendo usada
    print("DEBUG: API base URL:", "http://127.0.0.1:5000")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"FATAL_ERROR: {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Ocorreu um erro fatal ao iniciar:\n{e}")
        sys.exit(1)