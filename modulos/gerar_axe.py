# modulos.gerar_axe.py

import subprocess
import os
import sys

"""
Script robusto para empacotamento automático do serviço InLogic com PyInstaller.
- Descobre dinamicamente todas as pastas e arquivos do projeto.
- Gera o executável .exe (AXE) pronto para rodar como serviço Windows.
- Funciona em qualquer estrutura de pastas.
"""

def find_project_dirs(base_dir):
    """Retorna lista de todas as subpastas relevantes do projeto."""
    ignore = {'__pycache__', '.git', '.venv', 'dist', 'build'}
    dirs = []
    for root, subdirs, files in os.walk(base_dir):
        for d in subdirs:
            if d not in ignore:
                abs_path = os.path.join(root, d)
                # Só adiciona se contiver arquivos .py
                if any(f.endswith('.py') for f in os.listdir(abs_path)):
                    dirs.append(abs_path)
    return dirs

def find_entrypoint(base_dir):
    """Tenta encontrar o arquivo principal do serviço (ex: main.py, win_service.py, InlogicService.py)."""
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower() in ['main.py']:
                return os.path.join(root, f)
    raise FileNotFoundError('Arquivo de entrada do serviço não encontrado.')

def find_icon(base_dir):
    """Tenta encontrar um arquivo .ico para o ícone."""
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.ico'):
                return os.path.join(root, f)
    return None

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
entrypoint = find_entrypoint(project_root)
icon = r'C:\SUP_CONFIG\icone.ico'
project_dirs = find_project_dirs(project_root)

cmd = [
    sys.executable, '-m', 'PyInstaller',
    entrypoint,
    '--onefile',
    '--noconsole',
    f'--name=Service',
    '--hidden-import=win32timezone',
    '--hidden-import=win32service',
    '--hidden-import=win32serviceutil',
    '--hidden-import=win32event',
    '--hidden-import=servicemanager',
    '--hidden-import=multiprocessing',
    '--clean'
]
if icon:
    cmd.append(f'--icon={icon}')
    cmd.append(f'--add-data={icon};.')

for d in project_dirs:
    rel_path = os.path.relpath(d, project_root)
    cmd.append(f'--add-data={d};{rel_path}')

print("Comando PyInstaller gerado:")
print(" ".join(cmd))

result = subprocess.run(cmd, shell=False)
if result.returncode == 0:
    print("Build concluído com sucesso!")
else:
    print("Erro ao gerar o executável.")


