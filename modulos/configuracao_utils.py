"""
InLogic Studio - Utilitários de Configuração
-------------------------------------------
Este módulo contém funções para validação e processamento de configurações.
"""

from typing import Dict, Any
from enum import Enum

class FaseOperacao(Enum):
    MONITORAMENTO = "MONITORAMENTO"
    SUGESTAO = "SUGESTAO"
    AUTONOMO = "AUTONOMO"

def validar_fase_operacao(fase: str) -> str:
    """Valida e normaliza a fase de operação."""
    try:
        return FaseOperacao[fase.upper()].value
    except (KeyError, AttributeError):
        return FaseOperacao.MONITORAMENTO.value

def get_nested_value(obj: Dict[str, Any], path: str) -> Any:
    """
    Obtém um valor aninhado de um dicionário, procurando primeiro na raiz
    e depois dentro do campo 'config' se existir.
    """
    parts = path.split('.')
    
    # Primeiro tenta encontrar na raiz do objeto
    value = obj
    for part in parts:
        value = value.get(part)
        if value is None:
            break
    
    # Se não encontrou e existe config, tenta lá
    if value is None and 'config' in obj:
        value = obj['config']
        for part in parts:
            if value is None:
                break
            value = value.get(part)
            if isinstance(value, dict) and 'restricoes' in value and 'restricoes' in parts:
                value = value.get('restricoes')
    
    return value

def set_nested_value(obj: Dict[str, Any], path: str, value: Any, prefer_config: bool = True) -> None:
    """
    Define um valor aninhado em um dicionário, optando por colocá-lo em 'config'
    se prefer_config for True.
    """
    parts = path.split('.')
    
    # Se preferir config e ele existir, usa ele
    target = obj.get('config', {}) if prefer_config and 'config' in obj else obj
    
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value

def validar_e_completar_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida e adiciona campos faltantes na configuração com valores default.
    """
    if not isinstance(config, dict):
        raise ValueError("Configuração inválida: deve ser um dicionário")
    
    if 'projetos' not in config:
        config['projetos'] = []
    
    for projeto in config['projetos']:
        # Valida drivers
        if 'drivers' not in projeto:
            projeto['drivers'] = []
            
        for driver in projeto['drivers']:
            # Campos obrigatórios do driver
            if 'id' not in driver:
                raise ValueError(f"Driver sem ID no projeto {projeto.get('nome', 'DESCONHECIDO')}")
            
            # Configuração de fases
            fase = get_nested_value(driver, 'fase_operacao')
            set_nested_value(driver, 'fase_operacao', validar_fase_operacao(fase if fase else 'MONITORAMENTO'))
            
            modo = get_nested_value(driver, 'modo_operacao')
            set_nested_value(driver, 'modo_operacao', modo if modo else 'normal')
            
            # Garante estrutura de restrições no local correto (config)
            restricoes = get_nested_value(driver, 'restricoes')
            if not restricoes and 'config' in driver:
                driver['config']['restricoes'] = {}
            elif not restricoes:
                driver['config'] = {'restricoes': {}}
                
        # Valida tags
        if 'tags' not in projeto:
            projeto['tags'] = []
            
        for tag in projeto['tags']:
            # Campos obrigatórios da tag
            if 'id' not in tag:
                raise ValueError(f"Tag sem ID no projeto {projeto.get('nome', 'DESCONHECIDO')}")
            if 'id_driver' not in tag:
                raise ValueError(f"Tag {tag['id']} sem id_driver no projeto {projeto.get('nome', 'DESCONHECIDO')}")
            
            # Configuração de escrita e restrições
            escrita = get_nested_value(tag, 'escrita')
            set_nested_value(tag, 'escrita', escrita if escrita is not None else False)
            
            # Garante estrutura de restrições no local correto (config)
            restricoes = get_nested_value(tag, 'restricoes')
            if not restricoes and 'config' in tag:
                tag['config']['restricoes'] = {}
            elif not restricoes:
                tag['config'] = {'restricoes': {}}
                
            # Garante que todas as tags tenham tipo_dado
            if 'tipo_dado' not in tag:
                tag['tipo_dado'] = 'indefinido'
                
    return config

def log_campos_faltantes(config: Dict[str, Any]) -> None:
    """
    Loga campos que podem ser úteis mas estão faltando na configuração.
    """
    campos_opcionais = {
        'driver': [
            'modo_operacao',
            'restricoes.horario_permitido',
            'restricoes.dias_permitidos'
        ],
        'tag': [
            'escrita',
            'restricoes.valor_minimo',
            'restricoes.valor_maximo',
            'restricoes.requer_confirmacao'
        ]
    }
    
    for projeto in config.get('projetos', []):
        # Verifica campos dos drivers
        for driver in projeto.get('drivers', []):
            for campo in campos_opcionais['driver']:
                valor = get_nested_value(driver, campo)
                if valor is None:
                    print(f"SUGESTÃO: Driver '{driver.get('nome', driver['id'])}' - Campo opcional '{campo}' não configurado")
                        
        # Verifica campos das tags
        for tag in projeto.get('tags', []):
            for campo in campos_opcionais['tag']:
                valor = get_nested_value(tag, campo)
                if valor is None:
                    print(f"SUGESTÃO: Tag '{tag.get('nome', tag['id'])}' - Campo opcional '{campo}' não configurado")
