from modulos.logger import log

class GrafoDeConhecimento:
    """
    Representa o cérebro coletivo da IA, mantendo o estado de todos os nós.
    Utiliza um dicionário gerenciado para ser seguro entre processos.
    """
    def __init__(self, manager):
        self.manager = manager
        # Dicionário compartilhado para armazenar o estado de todos os nós
        self.nos = self.manager.dict()
        self.fonte = "GRAFO_CONHECIMENTO"
        log('INFO', self.fonte, "Cérebro coletivo (Grafo de Conhecimento) inicializado.")

    def registrar_no(self, id_no: str, tipo_no: str, metadados: dict = None):
        """
        Registra um novo nó no grafo.
        """
        if id_no not in self.nos:
            self.nos[id_no] = self.manager.dict({
                'tipo': tipo_no,
                'estado': 'INICIALIZADO',
                'metadados': metadados or {},
                'metricas': self.manager.dict(),
                'saude': 100
            })
            log('DEBUG', self.fonte, f"Nó '{id_no}' do tipo '{tipo_no}' registrado no grafo.")
        else:
            log('WARN', self.fonte, f"Tentativa de registrar um nó já existente: '{id_no}'.")

    def atualizar_estado_no(self, id_no: str, novo_estado: dict):
        """
        Atualiza o estado ou as métricas de um nó existente.
        """
        if id_no in self.nos:
            # Para atualizar um dict gerenciado, é preciso obter o proxy e modificá-lo
            no_atual = self.nos[id_no]
            for chave, valor in novo_estado.items():
                if chave == 'metricas' and isinstance(valor, dict):
                    # Atualiza o sub-dicionário de métricas
                    metricas_atuais = no_atual['metricas']
                    metricas_atuais.update(valor)
                    no_atual['metricas'] = metricas_atuais
                else:
                    no_atual[chave] = valor
            
            # É preciso reatribuir para garantir a sincronização
            self.nos[id_no] = no_atual
        else:
            log('ERROR', self.fonte, f"Tentativa de atualizar um nó inexistente: '{id_no}'.")