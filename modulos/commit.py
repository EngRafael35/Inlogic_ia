# modulos.commit.py



import subprocess
import sys
import os

def git_sync(commit_message=None):
    """
    Sincroniza o repositório local com o remoto no GitHub.
    Adiciona todas as alterações, faz commit e push.
    Se houver conflitos, orienta o usuário.
    """
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_path)

    try:
        subprocess.run(["git", "add", "."], check=True)
        if not commit_message:
            commit_message = "Atualização"
        subprocess.run(["git", "commit", "-m", commit_message], check=False)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Repositório sincronizado com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao sincronizar o repositório: {e}")
        print("Verifique se há conflitos e resolva manualmente se necessário.")

if __name__ == "__main__":
    msg = None
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    git_sync(msg)
