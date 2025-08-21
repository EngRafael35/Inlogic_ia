# ia/gerenciador.py

from typing import Dict, Any
from modulos.logger import log
from .ecossistema_projeto import EcossistemaProjeto

class GerenciadorIA:
    """
    Gerencia múltiplos Ecossistemas de IA, um para cada projeto.
    Atua como um orquestrador de alto nível, isolando completamente a inteligência
    de cada fábrica/projeto.
    """
    def __init__(self, manager, config: Dict[str, Any], fachada_ecossistema_geral: Any):
        self.fonte = "GERENCIADOR_IA"
        self.manager = manager
        self.config_geral = config
        self.ecossistema_geral = fachada_ecossistema_geral
        
        self.ecossistemas_projetos: Dict[str, EcossistemaProjeto] = {}
        
        try:
            self._iniciar_ecossistemas()
            log('SUCCESS', self.fonte, f"{len(self.ecossistemas_projetos)} ecossistema(s) de IA iniciados com sucesso.")
        except Exception as e:
            log('FATAL', self.fonte, "Erro fatal ao iniciar ecossistemas de IA", details={'erro': str(e)})
            raise

    def _iniciar_ecossistemas(self):
        """Cria uma instância de IA isolada para cada projeto encontrado na configuração."""
        projetos = self.config_geral.get('projetos', [])
        if not projetos:
            log('WARN', self.fonte, "Nenhum projeto encontrado na configuração para iniciar ecossistemas de IA.")
            return

        for config_projeto in projetos:
            id_projeto = config_projeto.get('id_projeto')
            if id_projeto:
                ecossistema = EcossistemaProjeto(id_projeto, config_projeto, self.manager, self.ecossistema_geral)
                self.ecossistemas_projetos[id_projeto] = ecossistema
            else:
                log('ERROR', self.fonte, "Projeto encontrado sem 'id_projeto', não foi possível iniciar seu ecossistema de IA.")
    



    def processar_atualizacao_dados(self, tipo_dado: str, id_alvo: str, dados: Dict):
        """
        Roteia os dados recebidos do Sistema Nervoso para o Ecossistema de Projeto correto.
        """
        # O ID do driver é a chave para encontrar o projeto/ecossistema correto.
        id_driver_associado = None
        
        if tipo_dado == 'tag':
            # O "CEP" para uma tag é o ID do seu driver pai.
            # Certifique-se que o processo do driver adicione este campo!
            id_driver_associado = dados.get('id_driver') 
        elif tipo_dado == 'driver':
            # O "CEP" para um driver é seu próprio ID.
            id_driver_associado = id_alvo
        elif tipo_dado == 'processo':
             # Roteia para todos os ecossistemas, pois a saúde do sistema afeta todos.
            for ecossistema in self.ecossistemas_projetos.values():
                 ecossistema.processar_atualizacao_dados(tipo_dado, id_alvo, dados)
            return

        if not id_driver_associado:
            # Não é possível rotear dados de tag sem um driver associado.
            return

        # Itera sobre os ecossistemas para encontrar o que "possui" este driver.
        for ecossistema in self.ecossistemas_projetos.values():
            # A configuração do ecossistema contém a lista de seus drivers.
            drivers_no_ecossistema = [d.get('id') for d in ecossistema.config.get('drivers', [])]
            
            if id_driver_associado in drivers_no_ecossistema:
                # Encontrou a "casa" certa. Delega o processamento final para ela.
                ecossistema.processar_atualizacao_dados(tipo_dado, id_alvo, dados)
                return  # Para após encontrar e entregar.


    def validar_escrita(self, tag_id, valor):
        # Lógica real de validação pode ser implementada depois
        return {'permitido': True, 'erro': '', 'fase_atual': 'MONITORAMENTO'}


    def parar(self):
        """Sinaliza a parada para todos os ecossistemas gerenciados."""
        log('INFO', self.fonte, "Parando todos os ecossistemas de IA...")
        for ecossistema in self.ecossistemas_projetos.values():
            ecossistema.parar()