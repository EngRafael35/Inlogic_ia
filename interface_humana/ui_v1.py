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
# WORKER E API CLIENT (Comportamento Robusto)
# ==============================================================================
class DataWorker(QObject):
    """Worker que vive em uma thread separada para buscar dados da API."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def run(self):
        """Este método é chamado pelo sinal 'request_update' da MainWindow."""
        print("[DEBUG] DataWorker.run: Recebeu sinal para iniciar a busca de dados.")
        try:
            results = {}
            # Define todos os endpoints que precisam ser chamados
            endpoints = {
                'main_data': self.api_client.get_data,
                'logs': self.api_client.get_logs,
                'ia_status': self.api_client.get_ia_status,
                'ia_metricas': self.api_client.get_ia_metricas,
                'ia_conhecimento': self.api_client.get_ia_conhecimento,
            }

            has_critical_error = False
            for key, func in endpoints.items():
                data, error = func()
                if error:
                    print(f"[WARN] Falha ao buscar dados para '{key}': {error}")
                    results[key] = None
                    # Consideramos a falha em 'main_data' como crítica
                    if key == 'main_data':
                        has_critical_error = True
                        # Emitimos o erro crítico imediatamente para a UI reagir
                        self.error.emit(error)
                        return # Aborta o resto das chamadas se o principal falhou
                else:
                    results[key] = data

            # Se chegamos aqui, mesmo que alguns endpoints secundários tenham falhado,
            # a requisição principal foi bem-sucedida.
            self.finished.emit(results)

        except Exception as e:
            # Captura qualquer exceção inesperada dentro do worker
            error_msg = f"Erro inesperado no worker: {e}"
            print(f"[CRITICAL] {error_msg}")
            self.error.emit(error_msg)

class ApiClient:
    """Cliente para interagir com a API do servidor de forma segura."""
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session() # Usa uma sessão para reutilizar conexões

    def _request(self, method, endpoint, **kwargs):
        """Método genérico para fazer requisições com tratamento de erro robusto."""
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            # Define um timeout padrão para todas as requisições
            kwargs.setdefault('timeout', 5)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status() # Lança um erro para status 4xx/5xx
            return response.json(), None
        except requests.exceptions.ConnectionError:
            return None, "Servidor offline ou inacessível."
        except requests.exceptions.Timeout:
            return None, f"Tempo de requisição esgotado para {endpoint}."
        except requests.exceptions.HTTPError as e:
            # Erro de resposta do servidor (ex: 404, 500)
            return None, f"Erro do servidor ({e.response.status_code}) para {endpoint}."
        except requests.exceptions.RequestException as e:
            # Captura qualquer outro erro de requisição
            return None, f"Erro de rede para {endpoint}: {e}"

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
# MODELO DE TABELA (VERSÃO DINÂMICA E AUTOADAPTÁVEL)
# ==============================================================================
class TagTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        # Inicia com dados e cabeçalhos vazios. Eles serão descobertos dinamicamente.
        self._data = []  # Agora será uma lista de dicionários
        self._headers = [] # Será preenchido com base nos dados
        self.quality_colors = {
            'boa': QColor("#2ECC71"), 'ruim': QColor("#E74C3C"), 'incerta': QColor("#F1C40F")
        }

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        try:
            row_data_dict = self._data[index.row()]
            column_name = self._headers[index.column()]

            if role == Qt.DisplayRole:
                return str(row_data_dict.get(column_name, ''))

            if role == Qt.ForegroundRole:
                # Cor para coluna 'qualidade'
                if column_name.lower() in ['qualidade', 'quality']:
                    qualidade = str(row_data_dict.get(column_name, '')).lower()
                    color = self.quality_colors.get(qualidade)
                    if color:
                        return color
                # Cor para coluna 'status'
                if column_name.lower() in ['status', 'status_conexao']:
                    status = str(row_data_dict.get(column_name, '')).lower()
                    if status == 'conectado':
                        return QColor("#2ECC71") # verde
                    elif status == 'desconectado':
                        return QColor("#E74C3C") # vermelho
                return QColor("#D3D3D3")

            if role == Qt.TextAlignmentRole and column_name.lower() in ['valor', 'value']:
                return Qt.AlignRight | Qt.AlignVCenter

        except (IndexError, KeyError) as e:
            print(f"[WARN] Erro ao acessar dados da tabela: {e}")
            return None
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            try:
                # Retorna o nome do cabeçalho da lista dinâmica
                return self._headers[section].replace('_', ' ').title()
            except IndexError:
                return None
        return None

    def update_data(self, new_data):
        """
        Processa os novos dados, descobre colunas dinamicamente e atualiza o modelo.
        Retorna True se a estrutura da tabela (colunas) mudou, False caso contrário.
        """
        if not new_data:
            if self._data: # Limpa a tabela se não há mais dados
                self.beginResetModel()
                self._data = []
                self._headers = []
                self.endResetModel()
                return True
            return False

        temp_data_list = []
        discovered_headers = set()

        # Itera sobre os dados para achatar a estrutura e descobrir todos os cabeçalhos
        for driver_id, driver_data in new_data.items():
            tags = driver_data.get('tags', {})
            if not tags:
                # Adiciona uma linha para drivers sem tags
                row_dict = {
                    'Driver': driver_data.get('config', {}).get('nome', driver_id),
                    'Status': driver_data.get('status_conexao', 'desconhecido'),
                    'Detalhe': driver_data.get('detalhe', 'Nenhuma tag configurada')
                }
                temp_data_list.append(row_dict)
                discovered_headers.update(row_dict.keys())
            else:
                for tag_id, tag_info in tags.items():
                    # Começa com os dados de nível superior (driver)
                    row_dict = {
                        'Driver': driver_data.get('config', {}).get('nome', driver_id),
                        'Status': driver_data.get('status_conexao', 'desconhecido'),
                        'ID da Tag': tag_id
                    }
                    
                    # Adiciona todos os campos da própria tag
                    row_dict.update(tag_info)

                    # Garante que o log de erro do driver seja propagado para a tag
                    if not row_dict.get('log') and row_dict['Status'] != 'conectado':
                        row_dict['log'] = driver_data.get('detalhe', 'Driver desconectado')
                    
                    temp_data_list.append(row_dict)
                    discovered_headers.update(row_dict.keys())

        # Define uma ordem de colunas preferencial para melhor visualização
        preferred_order = [
            'Driver', 'Status', 'nome', 'valor', 'qualidade', 'timestamp',
            'tipo', 'endereco', 'ID da Tag', 'log'
        ]
        
        # Ordena os cabeçalhos descobertos: primeiro os preferenciais, depois o resto em ordem alfabética
        sorted_headers = sorted(
            list(discovered_headers),
            key=lambda x: (preferred_order.index(x) if x in preferred_order else len(preferred_order), x)
        )
        
        structure_changed = (self._headers != sorted_headers)

        # Inicia a atualização do modelo. beginResetModel() é necessário quando a estrutura muda.
        self.beginResetModel()
        
        self._headers = sorted_headers
        self._data = temp_data_list
        
        # Finaliza a atualização
        self.endResetModel()

        return structure_changed

    def get_tag_info(self, row):
        # Este método agora retorna o dicionário diretamente, que é mais útil
        if 0 <= row < len(self._data):
            return self._data[row]
        return None


# ==============================================================================
# JANELA PRINCIPAL DA APLICAÇÃO (COM LÓGICA DE RESILIÊNCIA)
# ==============================================================================
class MainWindow(QMainWindow):
    def open_write_dialog(self, mode="unit"):  # mode: "unit" ou "lote"
        dialog = QDialog(self)
        dialog.setWindowTitle("Escrever Tag" if mode=="unit" else "Escrever em Lote")
        layout = QVBoxLayout(dialog)
        driver_label = QLabel("Driver:")
        driver_combo = QComboBox()
        drivers = [d for d in self.all_driver_data.keys()]
        driver_combo.addItems(drivers)
        layout.addWidget(driver_label)
        layout.addWidget(driver_combo)

        tag_widgets = []
        def update_tags():
            for w in tag_widgets:
                layout.removeWidget(w)
                w.deleteLater()
            tag_widgets.clear()
            driver_id = driver_combo.currentText()
            driver_data = self.all_driver_data.get(driver_id, {})
            tags = driver_data.get('tags', {})
            if mode == "unit":
                tag_label = QLabel("Tag:")
                tag_combo = QComboBox()
                tag_combo.addItems(tags.keys())
                value_label = QLabel("Valor:")
                value_edit = QLineEdit()
                layout.addWidget(tag_label)
                layout.addWidget(tag_combo)
                layout.addWidget(value_label)
                layout.addWidget(value_edit)
                tag_widgets.extend([tag_label, tag_combo, value_label, value_edit])
            else:
                tag_label = QLabel("Tags e Valores:")
                layout.addWidget(tag_label)
                tag_widgets.append(tag_label)
                for tag_id in tags.keys():
                    h = QHBoxLayout()
                    tag_name = QLabel(tag_id)
                    value_edit = QLineEdit()
                    h.addWidget(tag_name)
                    h.addWidget(value_edit)
                    w = QWidget(); w.setLayout(h)
                    layout.addWidget(w)
                    tag_widgets.append(w)

        driver_combo.currentTextChanged.connect(update_tags)
        update_tags()

        btn_send = QPushButton("Enviar")
        btn_cancel = QPushButton("Cancelar")
        btns = QHBoxLayout()
        btns.addWidget(btn_send)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        def send():
            driver_id = driver_combo.currentText()
            driver_data = self.all_driver_data.get(driver_id, {})
            tags = driver_data.get('tags', {})
            if mode == "unit":
                tag_combo = tag_widgets[1]
                value_edit = tag_widgets[3]
                tag_id = tag_combo.currentText()
                value = value_edit.text()
                if not tag_id or value == "":
                    QMessageBox.warning(dialog, "Erro", "Selecione uma tag e digite um valor.")
                    return
                result, error = self.api_client.write_tag(tag_id, value)
                if error:
                    QMessageBox.critical(dialog, "Erro", f"Falha ao escrever: {error}")
                else:
                    QMessageBox.information(dialog, "Sucesso", result.get("mensagem", "Comando enviado!"))
                    dialog.accept()
                    self.force_update()
            else:
                valores = {}
                for w in tag_widgets[1:]:
                    h = w.layout()
                    tag_id = h.itemAt(0).widget().text()
                    value = h.itemAt(1).widget().text()
                    if value != "":
                        valores[tag_id] = value
                if not valores:
                    QMessageBox.warning(dialog, "Erro", "Digite ao menos um valor.")
                    return
                payload = {"driver_id": driver_id, "valores": valores}
                result, error = self.api_client._request('post', '/api/escrever_lote', json=payload)
                if error:
                    QMessageBox.critical(dialog, "Erro", f"Falha ao escrever em lote: {error}")
                else:
                    QMessageBox.information(dialog, "Sucesso", result.get("mensagem", "Comando enviado!"))
                    dialog.accept()
                    self.force_update()

        btn_send.clicked.connect(send)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec_()
    def create_toolbar(self):
        toolbar = QToolBar("Ações Principais")
        toolbar.setIconSize(QSize(24, 24)); self.addToolBar(toolbar)
        refresh_action = QAction("🔄 Atualizar Agora", self); refresh_action.triggered.connect(self.force_update)
        restart_action = QAction("🔃 Reiniciar Sistema", self); restart_action.triggered.connect(self.confirm_restart_system)
        health_action = QAction("💓 Status do Sistema", self); health_action.triggered.connect(self.check_system_health)
        write_action = QAction("✍️ Escrever Tag", self); write_action.triggered.connect(lambda: self.open_write_dialog("unit"))
        write_lote_action = QAction("📝 Escrever em Lote", self); write_lote_action.triggered.connect(lambda: self.open_write_dialog("lote"))
        toolbar.addAction(refresh_action); toolbar.addSeparator(); toolbar.addAction(restart_action); toolbar.addAction(health_action)
        toolbar.addSeparator(); toolbar.addAction(write_action); toolbar.addAction(write_lote_action)
    # Sinal para pedir uma nova atualização ao worker de forma segura (thread-safe)
    request_update = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("InLogic Studio - Supervisor")
        self.setStyleSheet(MODERN_STYLESHEET)
        self.showMaximized()

        self.api_client = ApiClient("http://127.0.0.1:5000")
        self.all_driver_data = {}

        # Flags para controle de estado robusto
        self.is_shutting_down = False
        self.is_running_update = False # Impede requisições sobrepostas

        # A ordem do setup é importante para a lógica de resiliência
        self.setup_ui()
        self.setup_worker_and_thread()
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

    # --- Criação das Abas e Painéis (sem alterações lógicas) ---
    def create_tags_tab(self):
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
        widget = QWidget()
        layout = QVBoxLayout(widget)
        kpi_panel = self.create_ia_kpi_panel()
        layout.addWidget(kpi_panel)
        main_splitter = QSplitter(Qt.Horizontal)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        operational_panel = self.create_ia_operational_panel()
        training_panel = self.create_ia_training_panel()
        left_layout.addWidget(operational_panel)
        left_layout.addWidget(training_panel)
        details_panel = self.create_ia_details_panel()
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(details_panel)
        main_splitter.setSizes([600, 400])
        layout.addWidget(main_splitter)
        return widget

    def create_logs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        log_group = QGroupBox("Logs em Tempo Real (últimos 200 eventos)")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        layout.addWidget(log_group)
        return widget

    def create_ia_kpi_panel(self):
        kpi_group = QGroupBox("Painel de Controle Global")
        layout = QGridLayout(kpi_group)
        self.ia_kpi_labels = {}
        kpis = {
            "nos_ativos": ("🧠 Nós Ativos", "#3498DB"), "acuracia_media": ("🎯 Acurácia Média", "#2ECC71"),
            "alertas_gerados": ("⚠️ Alertas Gerados", "#F1C40F"), "drivers_conectados": ("🔌 Drivers Conectados", "#2ECC71")
        }
        for col, (key, (text, color)) in enumerate(kpis.items()):
            label = QLabel(text); label.setObjectName("KPI_Label")
            value = QLabel("N/A"); value.setObjectName("KPI_Value"); value.setStyleSheet(f"color: {color};")
            layout.addWidget(label, 0, col); layout.addWidget(value, 1, col)
            self.ia_kpi_labels[key] = value
        return kpi_group

    def create_ia_operational_panel(self):
        op_group = QGroupBox("Visão Operacional por Fase")
        layout = QVBoxLayout(op_group)
        self.ia_phase_lists = {}
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
        self.ia_training_info = QTextEdit(); self.ia_training_info.setReadOnly(True)
        layout.addWidget(self.ia_training_info)
        return train_group

    def create_ia_details_panel(self):
        details_group = QGroupBox("Detalhes do Driver Selecionado")
        layout = QVBoxLayout(details_group)
        self.ia_details_text = QTextEdit(); self.ia_details_text.setReadOnly(True)
        layout.addWidget(self.ia_details_text)
        return details_group

    # --- Lógica de Atualização da UI (sem alterações) ---
    def process_data(self, data):
        """Processa todos os dados recebidos do worker."""
        try:
            if not data or not data.get('main_data'):
                self.status_label.setText("✔️ Conectado (sem dados)")
                print("[WARN] Conexão bem-sucedida, mas dados principais estão vazios.")
            else:
                self.status_label.setText("✔️ Conectado")
                self.last_update_label.setText(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
                self.all_driver_data = data['main_data']
                self.update_tags_tab(data.get('main_data'))
                self.update_ia_dashboard_tab(data)
                self.update_logs_tab(data.get('logs'))
        except Exception as e:
            print(f"[ERRO] Erro crítico em process_data: {e}")
            self.handle_error(f"Erro ao processar dados: {e}")
        finally:
            self.is_running_update = False

    def update_tags_tab(self, main_data):
        if main_data is None: return
        self.tags_table_model.update_data(main_data)
        self.update_tag_filters(self.tags_table_model._data)

    def update_ia_dashboard_tab(self, all_data):
        ia_status = all_data.get('ia_status', {}).get('ia_status', {}) if all_data.get('ia_status') else {}
        ia_metricas = all_data.get('ia_metricas', {}).get('metricas', {}) if all_data.get('ia_metricas') else {}
        ia_conhecimento = all_data.get('ia_conhecimento', {}).get('conhecimento', {}) if all_data.get('ia_conhecimento') else {}
        kpi_data = {
            'nos_ativos': ia_metricas.get('nos_ativos', 'N/A'),
            'acuracia_media': f"{ia_metricas.get('acuracia_media', 0.0):.2f}%",
            'alertas_gerados': ia_metricas.get('alertas_gerados', 'N/A'),
            'drivers_conectados': f"{len([d for d in self.all_driver_data.values() if d.get('status_conexao') == 'conectado'])} / {len(self.all_driver_data)}"
        }
        for key, value_widget in self.ia_kpi_labels.items():
            value_widget.setText(str(kpi_data.get(key, "N/A")))
        fase_operacao = ia_metricas.get('fase_operacao', {})
        for list_widget in self.ia_phase_lists.values(): list_widget.clear()
        for fase, info in fase_operacao.items():
            if fase in self.ia_phase_lists:
                for driver_id in info.get('drivers', []):
                    driver_name = self.all_driver_data.get(driver_id, {}).get('config', {}).get('nome', driver_id)
                    item = QListWidgetItem(driver_name); item.setData(Qt.UserRole, driver_id)
                    self.ia_phase_lists[fase].addItem(item)
        training_info = ia_status.get('treinamento', {}); sync_info = ia_conhecimento.get('sincronizacao', {})
        html = (f"<h3>Treinamento de Modelos</h3><p><b>Modelos Ativos:</b> {len(training_info.get('modelos_ativos', []))}</p>"
                f"<p><b>Fila de Treinamento:</b> {training_info.get('fila_treinamento', 'N/A')}</p>"
                f"<h3>Sincronização de Conhecimento</h3><p><b>Última Atualização:</b> {ia_conhecimento.get('ultima_atualizacao', 'N/A')}</p>"
                f"<p><b>Nós Sincronizados:</b> {len(sync_info.get('nos_sincronizados', []))}</p>")
        self.ia_training_info.setHtml(html)

    def update_ia_details_panel(self, current_item, previous_item):
        if not current_item:
            self.ia_details_text.clear()
            return
        driver_id = current_item.data(Qt.UserRole)
        driver_data = self.all_driver_data.get(driver_id, {})
        def format_dict_to_html(d):
            html = "<ul>"
            for k, v in d.items():
                if isinstance(v, dict): html += f"<li><b>{str(k).replace('_', ' ').title()}:</b>{format_dict_to_html(v)}</li>"
                elif isinstance(v, list): html += f"<li><b>{str(k).replace('_', ' ').title()}:</b><ul>{''.join(f'<li>{item}</li>' for item in v)}</ul></li>"
                else: html += f"<li><b>{str(k).replace('_', ' ').title()}:</b> {v}</li>"
            return html + "</ul>"
        details_html = f"<h2>{driver_data.get('config', {}).get('nome', driver_id)}</h2><h4>ID: {driver_id}</h4><hr>"
        details_html += format_dict_to_html(driver_data)
        self.ia_details_text.setHtml(details_html)

    def update_logs_tab(self, logs):
        if not logs: return
        log_colors = {'ERROR': '#E74C3C', 'WARN': '#F1C40F', 'INFO': '#2ECC71', 'DEBUG': '#3498DB'}
        html_lines = [
            (f"<span style='color:#888;'>{log['timestamp']}</span> | "
             f"<b style='color:{log_colors.get(log['level'], '#D3D3D3')};'>{log['level']:<5}</b> | "
             f"<span style='color:#00A0A0;'>{log['source']:<15}</span> | {log['message']}")
            for log in reversed(logs)
        ]
        self.log_area.setHtml("<pre>" + "<br>".join(html_lines) + "</pre>")

    # --- LÓGICA DE RESILIÊNCIA (Coração da solução) ---
    def setup_worker_and_thread(self):
        """Cria UMA thread e UM worker que viverão durante toda a aplicação."""
        print("[INFO] Configurando worker e thread persistentes...")
        self.thread = QThread()
        self.worker = DataWorker(self.api_client)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.process_data)
        self.worker.error.connect(self.handle_error)
        self.request_update.connect(self.worker.run)
        self.thread.start()
        print("[INFO] Thread persistente iniciada e aguardando sinais.")

    def setup_timers(self):
        """Configura o QTimer para disparar o sinal de atualização periodicamente."""
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.trigger_update)
        self.data_timer.start(2000)

    def trigger_update(self):
        """Slot chamado pelo QTimer. Apenas emite um sinal para o worker se não houver outra atualização em andamento."""
        if self.is_shutting_down or self.is_running_update:
            return
        self.is_running_update = True
        print("[DEBUG] Disparando sinal request_update para o worker.")
        self.request_update.emit()

    def handle_error(self, error_msg):
        """Lida com erros de conexão de forma resiliente, permitindo novas tentativas."""
        self.status_label.setText(f"🔄 Tentando reconectar... (Erro: {error_msg.split('(Detalhe:')[0].strip()})")
        print(f"[API_ERROR] {error_msg}")
        self.is_running_update = False # Libera para a próxima tentativa do timer

    # --- Métodos Auxiliares e de Ações (sem alterações) ---
    def configure_table(self, table_view):
        table_view.setSortingEnabled(True); table_view.setAlternatingRowColors(True)
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table_view.horizontalHeader().setStretchLastSection(True)
        table_view.verticalHeader().setVisible(False)
        table_view.setSelectionBehavior(QTableView.SelectRows); table_view.setSelectionMode(QTableView.SingleSelection)
        table_view.resizeColumnsToContents()

    def update_tag_filters(self, data):
        drivers, statuses, qualities = set(), set(), set()
        for row in data:
            drivers.add(row.get('Driver', ''))
            statuses.add(row.get('Status', ''))
            qualities.add(row.get('qualidade', ''))
        self.update_combo_box(self.tags_filter_driver, sorted(list(drivers)), "Todos os Drivers")
        self.update_combo_box(self.tags_filter_status, sorted(list(statuses)), "Todos os Status")
        self.update_combo_box(self.tags_filter_quality, sorted(list(qualities)), "Todas as Qualidades")

    def update_combo_box(self, combo, items, default_text):
        current_text = combo.currentText()
        combo.blockSignals(True)
        combo.clear(); combo.addItem(default_text); combo.addItems(items)
        index = combo.findText(current_text)
        if index != -1: combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def filter_tags_table(self):
        search_text = self.tags_search_box.text().lower()
        driver = self.tags_filter_driver.currentText()
        status = self.tags_filter_status.currentText()
        quality = self.tags_filter_quality.currentText()
        for row in range(self.tags_table_model.rowCount()):
            row_data = self.tags_table_model._data[row]
            hide = ( (driver != "Todos os Drivers" and row_data[0] != driver) or
                     (status != "Todos os Status" and row_data[1] != status) or
                     (quality != "Todas as Qualidades" and row_data[4] != quality) or
                     (search_text and search_text not in " ".join(map(str, row_data)).lower()) )
            self.tags_table_view.setRowHidden(row, hide)

    def create_toolbar(self):
        toolbar = QToolBar("Ações Principais")
        toolbar.setIconSize(QSize(24, 24)); self.addToolBar(toolbar)
        refresh_action = QAction("🔄 Atualizar Agora", self); refresh_action.triggered.connect(self.force_update)
        restart_action = QAction("🔃 Reiniciar Sistema", self); restart_action.triggered.connect(self.confirm_restart_system)
        health_action = QAction("💓 Status do Sistema", self); health_action.triggered.connect(self.check_system_health)
        toolbar.addAction(refresh_action); toolbar.addSeparator(); toolbar.addAction(restart_action); toolbar.addAction(health_action)

    def open_tags_context_menu(self, position):
        indexes = self.tags_table_view.selectedIndexes()
        if not indexes: return
        source_index = self.tags_proxy_model.mapToSource(indexes[0])
        tag_info = self.tags_table_model.get_tag_info(source_index.row())
        if not tag_info: return
        menu = QMenu()
        # Tenta usar 'Nome da Tag', senão 'ID da Tag', senão qualquer chave
        tag_name = tag_info.get('Nome da Tag') or tag_info.get('ID da Tag') or next(iter(tag_info.keys()), 'Tag')
        write_action = QAction(f"✍️ Escrever na Tag '{tag_name}'", self)
        write_action.triggered.connect(lambda: self.write_tag_dialog(tag_info))
        menu.addAction(write_action)
        # Nova opção: escrita em lote para o driver
        driver_id = tag_info.get('Driver') or tag_info.get('driver')
        if driver_id:
            write_lote_action = QAction(f"📝 Escrever em Lote no Driver '{driver_id}'", self)
            write_lote_action.triggered.connect(lambda: self.open_write_dialog("lote"))
            menu.addAction(write_lote_action)
        copy_menu = menu.addMenu("📋 Copiar")
        for key, value in tag_info.items():
            action = QAction(f"Copiar {key}", self)
            action.triggered.connect(lambda _, v=value: QApplication.clipboard().setText(str(v)))
            copy_menu.addAction(action)
        menu.exec_(self.tags_table_view.viewport().mapToGlobal(position))

    def write_tag_dialog(self, tag_info):
        tag_name = tag_info.get('Nome da Tag') or tag_info.get('ID da Tag') or next(iter(tag_info.keys()), 'Tag')
        tag_id = tag_info.get('ID da Tag') or tag_info.get('Nome da Tag') or next(iter(tag_info.keys()), '')
        valor_atual = tag_info.get('Valor') or tag_info.get('valor') or ''
        new_value, ok = QInputDialog.getText(self, "Escrever Valor na Tag",
            f"<b>Tag:</b> {tag_name} (ID: {tag_id})<br>"
            f"<b>Valor Atual:</b> {valor_atual}<br><br>Digite o novo valor:",
            QLineEdit.Normal, str(valor_atual))
        if ok and new_value != str(valor_atual):
            result, error = self.api_client.write_tag(tag_id, new_value)
            if error:
                QMessageBox.critical(self, "Erro na Escrita", f"Falha ao enviar comando:\n{error}")
            else:
                QMessageBox.information(self, "Sucesso", result.get("mensagem", "Comando enfileirado!"))
            self.force_update()

    def confirm_restart_system(self):
        if QMessageBox.question(self, 'Confirmação', "Tem certeza que deseja reiniciar todo o sistema?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes: self.restart_system()

    def restart_system(self):
        self.data_timer.stop(); self.status_label.setText("🔃 Reiniciando o sistema...")
        result, error = self.api_client.restart_system()
        if error:
            QMessageBox.critical(self, "Erro", f"Não foi possível reiniciar:\n{error}"); self.data_timer.start()
        else:
            QMessageBox.information(self, "Sucesso", "Comando de reinicialização enviado.\nAguarde 10 segundos para a reconexão.")
            QTimer.singleShot(10000, self.post_restart_connect)

    def post_restart_connect(self):
        self.status_label.setText("🔄 Tentando reconectar..."); self.data_timer.start(); self.force_update()

    def check_system_health(self):
        health_data, error = self.api_client.get_health()
        if error:
            QMessageBox.warning(self, "Erro", f"Não foi possível obter status de saúde:\n{error}"); return
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
        """Finaliza a aplicação de forma limpa, encerrando a thread do worker."""
        print("[INFO] Fechando a aplicação...")
        self.is_shutting_down = True
        self.data_timer.stop()
        if hasattr(self, 'thread') and self.thread.isRunning():
            print("[INFO] Solicitando o encerramento da thread do worker...")
            self.thread.quit()
            if not self.thread.wait(3000):
                print("[WARN] A thread não respondeu a tempo. Forçando o encerramento.")
                self.thread.terminate()
        print("[INFO] Fechamento concluído."); event.accept()

    def force_update(self):
        """Força uma atualização imediata, respeitando a lógica de controle de fluxo."""
        self.status_label.setText("🔄 Atualizando dados...")
        self.trigger_update()

# ==============================================================================
# PONTO DE ENTRADA DA APLICAÇÃO
# ==============================================================================
if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"[ERRO FATAL] Erro não tratado ao iniciar a aplicação: {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Ocorreu um erro fatal ao iniciar:\n{e}")
        sys.exit(1)