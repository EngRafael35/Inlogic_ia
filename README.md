# InLogic IA - Plataforma Modular de Automação Industrial

## Visão Geral
InLogic IA é uma plataforma flexível para supervisão, controle e integração de processos industriais, desenvolvida em Python. Permite conectar CLPs, bancos de dados, sistemas de IA e interfaces humanas, com arquitetura extensível e API REST.

## Principais Recursos
- **Drivers Industriais**: Suporte a ControlLogix, Modbus, MQTT, SQL Server, MySQL, PostgreSQL e outros.
- **Núcleo de IA**: Ecossistema de aprendizado, otimização, diagnóstico e automação.
- **API REST**: Integração com sistemas externos, comandos, leitura/escrita de dados, monitoramento e autenticação.
- **Logging Profissional**: Auditoria detalhada de eventos, erros e diagnósticos.
- **Configuração Flexível**: Parametrização de drivers, tags, intervalos, permissões e lógica de negócio.
- **Escalabilidade**: Suporte a múltiplos projetos/fábricas, cada um com seu próprio ecossistema.

## Estrutura do Projeto
```
├── main.py                  # Orquestrador principal
├── driver/                  # Drivers industriais e de banco de dados
│   ├── controllogix_driver_process.py
│   ├── modbus_driver_process.py
│   ├── mqtt_driver_process.py
│   ├── sql_driver_process.py
│   └── ...
├── ia/                      # Núcleo de IA, ecossistemas, aprendizado
│   ├── ecossistema_projeto.py
│   ├── gerenciador.py
│   ├── motor/
│   ├── core/
│   ├── nos/
│   └── celebro_coletivo/
├── modulos/                 # Utilitários, logger, configuração, automação
│   ├── configuracao_utils.py
│   ├── logger.py
│   ├── commit.py / comit.py # Scripts de automação Git
│   └── ...
├── interface_humana/        # Interface de usuário (UI)
│   └── ui.py
├── servidor/                # Servidor Flask para API REST
│   └── servidor.py
├── arquitetura/             # Documentação e planejamento
│   └── IMPLEMENTAR.TXT
├── celebro_coletivo/        # Grafo de conhecimento
│   └── grafo_conhecimento.py
├── logs/                    # Arquivos de log
├── LICENSE                  # Licença MIT
├── README.md                # Este documento
└── .gitignore               # Exclusão de arquivos do Git
```

## Exemplos de Uso
### Execução do Sistema
```powershell
python main.py
```

### Requisição de Escrita em Lote via API REST
```http
POST /api/escrever_lote
Content-Type: application/json
{
  "driver_id": "sql1",
  "valores": {
    "coluna1": 123,
    "coluna2": "valor",
    "coluna3": true
  }
}
```

### Automação de Commit Git
```powershell
python modulos/comit.py
```

## Diretrizes de Contribuição
- Siga o padrão de modularização para novos drivers e algoritmos de IA.
- Documente novas funções e APIs no diretório `arquitetura/`.
- Utilize logging profissional para rastreabilidade.
- Teste alterações antes de enviar pull requests.

## Suporte e Contato
- Para dúvidas, sugestões ou reportar bugs, utilize o GitHub Issues.
- Para integração personalizada, entre em contato com o mantenedor do projeto.

## Observações
- Não execute módulos internos diretamente devido a imports relativos.
- O sistema é extensível para novos drivers, algoritmos de IA e integrações.
- Para automatizar commits e atualizações do repositório, utilize o script  `modulos/commit.py`.

## Licença
Este projeto é distribuído sob licença MIT. Consulte o arquivo LICENSE para mais detalhes.
