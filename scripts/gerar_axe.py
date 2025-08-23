# modulos.gerar_axe.py

import subprocess
import os
import sys

r"""

-------------------------- Inlogic Service --------------------------- 

Script robusto para empacotamento automático do serviço InLogic com PyInstaller.
- Descobre dinamicamente todas as pastas e arquivos do projeto.
- Gera o executável .exe (AXE) pronto para rodar como serviço Windows.
- Funciona em qualquer estrutura de pastas.

-------------------- Gerar o axe do Inlogic Service CMD ------------------------ 

C:\Users\lenovo\AppData\Local\Programs\Python\Python313\python.exe -m PyInstaller ^
 "C:\Users\lenovo\Desktop\InLogic\InLogic_Studio\inlogic_IA\main.py" ^
 --onefile ^
 --noconsole ^
 --icon="C:\SUP_CONFIG\icone.ico" ^
 --add-data "C:\SUP_CONFIG\icone.ico;." ^
 --name Service ^
 --hidden-import=win32timezone ^
 --hidden-import=win32service ^
 --hidden-import=win32serviceutil ^
 --hidden-import=win32event ^
 --hidden-import=servicemanager ^
 --hidden-import=multiprocessing ^
 --clean

-------------------- Gerar o serviço do Inlogic Service CMD ------------------------ 

sc create InLogicService binPath= "C:\Users\lenovo\Desktop\InLogic\InLogic_Studio\inlogic_IA\dist\Service.exe" start= auto DisplayName= "InLogic Service"

sc start InLogicService

sc stop InLogicService

sc delete InLogicService

"""



# Caminhos fixos para build enxuto
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
entrypoint = os.path.join(project_root, 'main.py')
icon = "C:\SUP_CONFIG\icone.ico"

# Pastas essenciais do projeto
folders = [
    'modulos', 'ia', 'driver', 'interface_humana', 'servidor', 'celebro_coletivo', 'arquitetura'
]

cmd = [
    sys.executable, '-m', 'PyInstaller',
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

# Adiciona todas as pastas e submódulos essenciais
for folder in folders:
    folder_path = os.path.join(project_root, folder)
    if os.path.exists(folder_path):
        cmd.append('--add-data=' + folder_path + ';' + folder)
        cmd.append('--collect-submodules=' + folder)

print("Comando PyInstaller gerado:")
print(" ".join(cmd))

result = subprocess.run(cmd, shell=False)
if result.returncode == 0:
    print("Build concluído com sucesso!")
else:
    print("Erro ao gerar o executável.")


