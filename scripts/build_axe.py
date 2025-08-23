# build_axe.py
# Script automatizado para criar ambiente virtual limpo, instalar dependências essenciais e gerar o AXE do serviço InLogic

import subprocess
import sys
import os
import shutil

# Caminhos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
venv_dir = os.path.join(project_root, 'venv_axe')
entrypoint = os.path.join(project_root, 'main.py')
icon = r"C:\SUP_CONFIG\icone.ico"

# 1. Cria ambiente virtual limpo
if os.path.exists(venv_dir):
    print("Removendo ambiente virtual antigo...")
    try:
        shutil.rmtree(venv_dir)
    except PermissionError as e:
        print(f"Aviso: não foi possível remover o ambiente virtual antigo ({e}). Continue apenas se ele não estiver em uso.")
print("Criando ambiente virtual limpo...")
subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)

# 2. Instala dependências essenciais
pip_path = os.path.join(venv_dir, 'Scripts', 'pip.exe')
python_path = os.path.join(venv_dir, 'Scripts', 'python.exe')
requirements = [
    'pywin32', 'pycomm3', 'pyModbusTCP', 'paho-mqtt', 'pyodbc', 'psutil',
    'numpy', 'scipy', 'colorama', 'pycryptodome', 'PyQt5', 'werkzeug',
    'blinker', 'certifi', 'charset_normalizer', 'idna', 'itsdangerous', 'MarkupSafe',
    'pytz', 'six', 'tzdata', 'urllib3', 'river', 'requests', 'flask', 'PyInstaller', 'sqlalchemy'
]
print("Instalando dependências essenciais...")
subprocess.run([pip_path, 'install'] + requirements, check=True)

# 3. Limpa build/dist antigos
for folder in ['build', 'dist']:
    path = os.path.join(project_root, folder)
    if os.path.exists(path):
        print(f"Removendo pasta {folder}...")
        shutil.rmtree(path)

# 4. Gera o AXE com PyInstaller no ambiente limpo
cmd = [
    python_path, '-m', 'PyInstaller',
    entrypoint,
    '--onefile',
    '--noconsole',
    '--icon=' + icon,
    '--add-data=' + icon + ';.',
    '--name=Service',
    '--hidden-import=win32timezone',
    '--hidden-import=win32service',
    '--hidden-import=win32serviceutil',
    '--hidden-import=win32event',
    '--hidden-import=servicemanager',
    '--hidden-import=multiprocessing',
    '--clean'
]
print("Comando PyInstaller gerado:")
print(" ".join(cmd))
result = subprocess.run(cmd)
if result.returncode == 0:
    print("Build concluído com sucesso!")
else:
    print("Erro ao gerar o executável.")
    print("Verifique se o PyInstaller está instalado corretamente no ambiente virtual. Tente rodar 'pip install PyInstaller' dentro do venv_axe se necessário.")
