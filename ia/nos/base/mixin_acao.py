# ia/nos/base/mixin_acao.py
from typing import Dict
from modulos.registrador import log

class MixinExecutorDeAcao:
    """Mixin que adiciona a habilidade de um nó executar ações no mundo real."""
    
    def _executar_acao_local(self, acao: Dict) -> Dict:
        """Ponto de entrada que roteia a ação para o executor correto."""
        tipo_acao = acao.get('tipo')
        params = acao.get('params')

        if not all([tipo_acao, params]):
            return {'status': 'falha', 'motivo': 'formato_acao_invalido'}

        if tipo_acao == 'escrita_tag':
            return self._executar_escrita(params)
        else:
            log('IA_WARN', self.fonte_log, "Tipo de ação desconhecido.", details=acao)
            return {'status': 'falha', 'motivo': 'tipo_de_acao_desconhecido'}

    def _executar_escrita(self, params: Dict) -> Dict:
        """Executa uma operação de escrita validada."""
        tag_id = params.get('tag_id')
        valor = params.get('valor')
        
        if not all([tag_id, valor is not None]):
            return {'status': 'falha', 'motivo': 'parametros_escrita_invalidos'}

        log('IA_INFO', self.fonte_log, f"Executando escrita na tag {tag_id} com valor {valor}.")
        # Chama o sistema principal para executar a escrita via fachada do ecossistema
        self.ecossistema.escrever_valor_tag(tag_id, valor)
        return {'status': 'sucesso'}