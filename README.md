<<<<<<< HEAD
# Inlogic_ia
Sistema de supervisão e controle autonomo industrial
=======
# InLogic Studio - Arquitetura do Sistema

## Visão Geral

O InLogic Studio é um sistema de supervisão industrial modular, desenvolvido em Python, que integra drivers de comunicação, processamento de IA, API REST e interface de monitoramento. O sistema é orientado a processos e utiliza multiprocessing para garantir escalabilidade e isolamento entre componentes.

## Principais Módulos

- **main.py**: Ponto de entrada do sistema. Gerencia inicialização, configuração, drivers, IA e API.
- **modulos/**: Contém módulos utilitários, servidor Flask para API REST, logger, configuração, etc.
- **ia/**: Núcleo de Inteligência Artificial. Gerencia fases, nós de IA, persistência, escrita e monitoramento de treinamento.
- **drivers/**: Implementações dos drivers industriais (Modbus, ControlLogix, etc).
- **Setup.cfg**: Arquivo de configuração criptografado do sistema.

## Fluxo de Inicialização

1. Carregamento e validação da configuração.
2. Inicialização dos drivers de comunicação.
3. Inicialização do Gerenciador de IA e dos nós de IA.
4. Inicialização do servidor de API REST.
5. Monitoramento contínuo do sistema e interface.

## Comunicação

- Dados compartilhados entre processos via `multiprocessing.Manager`.
- API REST para integração externa e monitoramento.
- Sistema de logging centralizado.

## IA

- Gerenciador de IA orquestra fases, permissões e processamento cognitivo.
- Nós de IA especializados para drivers, tags e processos.
- Persistência de estado e checkpoints dos modelos.
- Monitoramento de treinamento e métricas.

## Como executar

Execute sempre pelo arquivo principal:

```bash
python main.py
```

## Observações

- Não execute módulos internos diretamente devido a imports relativos.
- O sistema é extensível para novos drivers e algoritmos de IA.
>>>>>>> 24ed2da (Versão inicial do projeto InLogic IA)
