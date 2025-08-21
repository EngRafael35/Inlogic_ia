# logger.py
from datetime import datetime
import threading
from collections import deque
import json
import os
from typing import Dict, Any

try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True, convert=True)  # Adicionado convert=True para forçar conversão em Windows
    CORES_ATIVAS = True
    print("Sistema de cores inicializado com sucesso")  # Debug
except ImportError:
    print("AVISO: Colorama não encontrado, logs serão exibidos sem cores")  # Debug
    class Fore: 
        GREEN = YELLOW = RED = CYAN = MAGENTA = BLUE = WHITE = ''
    class Style:
        BRIGHT = RESET_ALL = ''
    class Back:
        RED = BLUE = ''
    CORES_ATIVAS = False

# Lock para garantir que a escrita no console seja atômica entre processos/threads
log_lock = threading.Lock()

# Mantém um buffer circular com os últimos logs
MAX_LOGS = 5000  # Aumentado para 5000 logs
log_buffer = deque(maxlen=MAX_LOGS)

# Cores para diferentes níveis e módulos
CORES_NIVEL = {
    'INFO': Fore.GREEN,
    'WARN': Fore.YELLOW,
    'ERROR': Fore.RED,
    'DEBUG': Fore.CYAN,
    'FATAL': Back.RED + Fore.WHITE,
    'SUCCESS': Fore.GREEN + Style.BRIGHT,
    'IA_INFO': Fore.BLUE + Style.BRIGHT,  # Aumentado brilho para melhor visibilidade
    'IA_WARN': Fore.YELLOW + Style.BRIGHT,
    'IA_ERROR': Fore.RED + Style.BRIGHT,
    'IA_DEBUG': Fore.CYAN + Style.BRIGHT,
    'IA_MODEL': Fore.MAGENTA + Style.BRIGHT,
}

# Níveis de log válidos
NIVEIS_VALIDOS = set(CORES_NIVEL.keys())

# Diretório para salvar logs em arquivo
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Arquivo de log atual
current_log_file = os.path.join(LOG_DIR, f"inlogic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def log(level: str, source: str, message: str, details: Dict[str, Any] = None):
    """
    Função de log centralizada e thread-safe para todo o sistema.

    Args:
        level (str): Nível do log (e.g., 'INFO', 'WARN', 'ERROR', 'IA_INFO', etc.).
        source (str): Origem do log (e.g., 'MAIN', 'IA_NODE_123', 'MODEL_XYZ').
        message (str): A mensagem de log.
        details (Dict[str, Any], optional): Detalhes adicionais para o log.
    """
    # Verifica se o nível de log é válido
    if level not in NIVEIS_VALIDOS:
        print(f"{Fore.RED}Nível de log inválido: {level}. Níveis válidos: {', '.join(sorted(NIVEIS_VALIDOS))}{Style.RESET_ALL}", flush=True)
        level = 'ERROR'  # Fallback para ERROR em caso de nível inválido
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Prepara a entrada do log com detalhes extras
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'source': source,
        'message': message,
        'details': details or {}
    }
    
    # Formata a mensagem para console com cores
    cor = CORES_NIVEL.get(level, Fore.WHITE)  # Usa branco como cor padrão se nível não encontrado
    reset = Style.RESET_ALL if CORES_ATIVAS else ''
    
    # Formata a mensagem base com melhor visibilidade
    log_message = f"{Fore.WHITE}{timestamp}{reset} | {cor}{level:<8}{reset} | {Fore.CYAN}{source:<25}{reset} | {cor}{message}{reset}"
    
    # Adiciona detalhes se existirem
    if details:
        try:
            detail_str = json.dumps(details, ensure_ascii=False, indent=2)
            # Formata detalhes com indentação e cor
            detail_lines = detail_str.split('\n')
            formatted_details = '\n'.join(f"{' '*45}{Fore.WHITE}{line}{reset}" for line in detail_lines)
            log_message += f"\n{' '*45}{Fore.WHITE}Detalhes: {formatted_details}{reset}"
        except Exception as e:
            log_message += f"\n{' '*45}{Fore.RED}Erro ao formatar detalhes: {str(e)}{reset}"
    
    with log_lock:
        try:
            # Imprime no console
            print(log_message, flush=True)  # flush=True para garantir saída imediata
            
            # Salva no buffer
            log_buffer.append(log_entry)
            
            # Salva em arquivo
            with open(current_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}|{level}|{source}|{message}")
                if details:
                    f.write(f"|{json.dumps(details, ensure_ascii=False)}")
                f.write("\n")
                f.flush()  # Força escrita no arquivo
                
        except Exception as e:
            print(f"{Fore.RED}Erro ao processar log: {str(e)}{Style.RESET_ALL}", flush=True)

def get_recent_logs(limit=None):
    """Retorna os logs mais recentes."""
    with log_lock:
        if limit is None:
            return list(log_buffer)
        return list(log_buffer)[-limit:]

def get_logs_since(timestamp):
    """Retorna logs após um determinado timestamp."""
    with log_lock:
        return [
            log for log in log_buffer
            if log['timestamp'] > timestamp
        ]