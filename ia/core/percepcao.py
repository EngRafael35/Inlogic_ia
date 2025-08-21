"""
Módulo de Processamento e Percepção de Dados do InLogic ECID.
Responsável pelo processamento inicial de dados e detecção de padrões.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime

class ProcessadorBase:
    """Classe base para processadores de dados."""
    
    def processar(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados brutos."""
        raise NotImplementedError()

class ProcessadorNumerico(ProcessadorBase):
    """Processador especializado em dados numéricos."""
    
    def __init__(self):
        self.historico_valores = []
        self.limites = {
            'superior': float('inf'),
            'inferior': float('-inf')
        }
        
    def definir_limites(self, inferior: float, superior: float):
        """Define limites de validação."""
        self.limites = {
            'superior': superior,
            'inferior': inferior
        }
        
    def processar(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa dados numéricos aplicando validações e transformações.
        
        Args:
            dados: Dicionário com valores numéricos
            
        Returns:
            Dict com dados processados e métricas
        """
        try:
            valor = float(dados.get('valor', 0))
            
            # Validação de limites
            if not (self.limites['inferior'] <= valor <= self.limites['superior']):
                return {
                    'status': 'erro',
                    'mensagem': 'Valor fora dos limites',
                    'valor_original': valor,
                    'limites': self.limites
                }
                
            # Atualiza histórico
            self.historico_valores.append(valor)
            if len(self.historico_valores) > 1000:
                self.historico_valores.pop(0)
                
            # Calcula métricas
            metricas = self._calcular_metricas()
            
            return {
                'status': 'sucesso',
                'valor_processado': valor,
                'metricas': metricas,
                'timestamp': datetime.now().isoformat()
            }
            
        except ValueError:
            return {
                'status': 'erro',
                'mensagem': 'Valor não numérico',
                'valor_original': dados.get('valor')
            }
            
    def _calcular_metricas(self) -> Dict[str, float]:
        """Calcula métricas estatísticas básicas."""
        valores = np.array(self.historico_valores)
        return {
            'media': float(np.mean(valores)),
            'desvio_padrao': float(np.std(valores)),
            'minimo': float(np.min(valores)),
            'maximo': float(np.max(valores))
        }

class ProcessadorTexto(ProcessadorBase):
    """Processador especializado em dados textuais."""
    
    def __init__(self):
        self.padroes_conhecidos = set()
        self.historico_padroes = []
        
    def adicionar_padrao(self, padrao: str):
        """Adiciona um padrão conhecido."""
        self.padroes_conhecidos.add(padrao)
        
    def processar(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa dados textuais.
        
        Args:
            dados: Dicionário com texto a ser processado
            
        Returns:
            Dict com análise do texto
        """
        texto = str(dados.get('valor', ''))
        
        # Análise básica
        analise = {
            'tamanho': len(texto),
            'palavras': len(texto.split()),
            'padrao_conhecido': texto in self.padroes_conhecidos
        }
        
        # Registra padrão
        if analise['padrao_conhecido']:
            self.historico_padroes.append({
                'texto': texto,
                'timestamp': datetime.now().isoformat()
            })
            
        return {
            'status': 'sucesso',
            'texto_processado': texto,
            'analise': analise,
            'timestamp': datetime.now().isoformat()
        }

class GerenciadorPercepcao:
    """
    Gerenciador central de processamento e percepção.
    Coordena diferentes processadores especializados.
    """
    
    def __init__(self):
        self.processadores = {
            'numerico': ProcessadorNumerico(),
            'texto': ProcessadorTexto()
        }
        
    def processar_dados(self, tipo: str, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa dados usando processador apropriado.
        
        Args:
            tipo: Tipo de dados ('numerico' ou 'texto')
            dados: Dados a serem processados
            
        Returns:
            Dict com resultado do processamento
        """
        if tipo not in self.processadores:
            return {
                'status': 'erro',
                'mensagem': f'Tipo de dados não suportado: {tipo}'
            }
            
        return self.processadores[tipo].processar(dados)
        
    def registrar_processador(self, tipo: str, processador: ProcessadorBase):
        """Registra um novo processador especializado."""
        if not isinstance(processador, ProcessadorBase):
            raise ValueError("Processador deve herdar de ProcessadorBase")
        self.processadores[tipo] = processador
        
    def definir_limites_numericos(self, inferior: float, superior: float):
        """Define limites para processador numérico."""
        if 'numerico' in self.processadores:
            self.processadores['numerico'].definir_limites(inferior, superior)
            
    def adicionar_padrao_texto(self, padrao: str):
        """Adiciona padrão conhecido ao processador de texto."""
        if 'texto' in self.processadores:
            self.processadores['texto'].adicionar_padrao(padrao)
