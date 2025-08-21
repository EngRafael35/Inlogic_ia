# Pasta modulos

Contém utilitários e componentes centrais do sistema:

- **servidor.py**: Servidor Flask para API REST, expõe endpoints para dados, comandos, logs, saúde do sistema e IA.
- **logger.py**: Sistema de logging centralizado, usado por todos os módulos.
- **configuracao_utils.py**: Funções para validação e complementação da configuração do sistema.

Esses módulos são usados pelo núcleo do sistema (`main.py`) e pelos componentes de IA e drivers.
