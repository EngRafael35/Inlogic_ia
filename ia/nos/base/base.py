# ia/nos/base/base.py

class CognitiveNode:
    """
    Classe base para os Nós Cognitivos do Ecossistema IA.
    
    Esta classe define a estrutura fundamental e as operações básicas que
    todos os Nós Cognitivos devem implementar. Nós específicos, como
    NoDriverIA e NoTagIA, devem estender esta classe e fornecer
    implementações concretas para as operações definidas aqui.
    """
    
    def __init__(self, id_no, config, ecossistema):
        """
        Inicializa um Nó Cognitivo.
        
        Args:
            id_no (str): Identificador único do nó.
            config (dict): Configurações específicas do nó.
            ecossistema (Any): Referência à fachada do ecossistema, permitindo
                               interação com outros componentes do sistema.
        
        O construtor deve ser chamado por todas as subclasses para garantir
        a inicialização adequada do nó cognitivo.
        """
        self.id = id_no
        self.config = config
        self.ecossistema = ecossistema
        self.ativo = True
        
        # Estado e métricas do nó
        self.estado = {}
        self.metricas = {}
        self.saude = 'boa'  # Estado de saúde inicial
        
        # Registra o nó no ecossistema
        self.ecossistema.registrar_no(id_no, self)
    
    def ciclo_cognitivo(self, dados):
        """
        Executa um ciclo cognitivo com base nos dados recebidos.
        
        Args:
            dados (dict): Dados de entrada para o ciclo cognitivo.
        
        Este método deve ser implementado por subclasses para definir o
        comportamento específico de cada tipo de nó durante o ciclo cognitivo.
        """
        raise NotImplementedError("Subclasses devem implementar this method")
    
    def parar(self):
        """
        Para o nó cognitivo de forma limpa, liberando recursos e salvando estado,
        se necessário.
        """
        self.ativo = False
        # Implementar lógica de parada específica, se necessário
        self.ecossistema.desregistrar_no(self.id)
    
    def salvar_estado(self):
        """
        Salva o estado atual do nó em um formato persistente, como um arquivo ou
        banco de dados, para que possa ser recuperado posteriormente.
        
        O formato e o local de salvamento devem ser definidos nas subclasses,
        dependendo dos requisitos específicos de cada nó cognitivo.
        """
        raise NotImplementedError("Subclasses devem implementar this method")
    
    def carregar_estado(self, estado_salvo):
        """
        Carrega o estado de um nó a partir de um estado salvo anteriormente.
        
        Args:
            estado_salvo (Any): Dados do estado salvo, que podem ser usados para
                                restaurar o estado do nó.
        
        O formato e a estrutura dos dados de estado_salvo devem ser compatíveis
        com a implementação do método salvar_estado.
        """
        raise NotImplementedError("Subclasses devem implementar this method")