# Changelog

Todas as mudanças relevantes da **QA Platform** (implementação em `code/`) são
documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
versionamento segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.2.0] - 2026-09-12

### Added

- Núcleo de orquestração **Workflow-first** (ADR-001): orquestrador raiz como
  `Workflow` da Agno v2 que executa os passos de QA em ordem determinística
  (descoberta de alvo → planejamento por risco → roteamento/execução de camadas →
  consolidação → advisory judge → feedback), com o histórico de cada execução
  persistido por um contrato próprio (`RunStateStore`, in-memory nesta fase).
  Inclui o contrato de camada de QA (ponto de extensão), uma camada de IA mínima
  (stub) e o schema/parser do manifesto `qa-target.yaml`.
- Persistência **durável** do resultado de run (feature `durable-run-state-store`,
  ADR-003): adapter `DynamoDBRunStateStore` que implementa o contrato
  `RunStateStore` sobre DynamoDB, persistindo o `RunResult` final de forma durável
  (sobrevive ao encerramento do processo). Usa escrita condicional
  (`attribute_not_exists(run_id)`) para nunca sobrescrever um resultado já
  persistido, timeouts explícitos de conexão/leitura e retries, e `import boto3`
  tardio (o pacote continua importável sem o SDK quando só o backend in-memory é
  usado). Erros de infraestrutura viram `RunStorageError` (distinto de conflito e
  ausência) sem vazar segredos.
- Registro persistido do resultado (`RunRecordModel`, Pydantic `BaseModel`) com
  `schema_version` para evolução de formato, e `RunRecordSerializer` que faz o
  round-trip sem perda entre o `RunResult` de domínio e o item persistido
  (severity serializada pelo nome do enum; item malformado ou `schema_version` não
  suportado vira `RunRecordSerializationError` nomeando o run_id). O domínio
  permanece `@dataclass` puro; a persistência (fronteira externa) usa Pydantic na
  infraestrutura.
- Seleção do backend por ambiente (`RunStoreFactory.build_run_store`): variável
  `RUN_STORE_BACKEND` (default `in_memory`) escolhe entre in-memory e DynamoDB; o
  backend `dynamodb` exige `RUN_TABLE_NAME` e faz *fail-fast* com
  `RunStoreConfigError` quando ausente, sem cair silenciosamente no in-memory.
  Documentado no `.env.example`.
- Tabela DynamoDB de histórico de runs provisionada como código no `template.yaml`
  (SAM) com chave de partição `run_id`, `PAY_PER_REQUEST`, criptografia em repouso
  (`SSESpecification`) e policy de **menor privilégio** para a função (apenas
  `GetItem`/`PutItem` na tabela). Script `localstack/init/02-create-run-table.sh`
  cria a mesma tabela localmente de forma idempotente.
- Decisão de concorrência das camadas registrada no **ADR-002**: execução com
  limite de 8 camadas simultâneas e timeout de 300s por camada.
- Script executável `generate_quality_report.py` que executa todas as ferramentas
  de qualidade descritas em `scripts/README.md` (Ruff lint e format, mypy, Bandit,
  pip-audit, import-linter, Radon, Xenon e pytest com cobertura) e consolida os
  resultados em `reports/quality-report.md` e `reports/quality-report.pdf`. Roda
  cada ferramenta sem shell, captura status e saída, e se autoexecuta via
  `uv run --with reportlab` para gerar o PDF sem adicionar dependência ao projeto.
- Ambiente local de dependências (`docker-compose.yml`) com o conjunto padrão
  completo do portfólio: LocalStack (núcleo, sobe sempre e alcança healthy),
  Ollama, AgentOS, SigNoz, stack Grafana (Grafana + Tempo + Loki + Prometheus),
  Langfuse e pgvector. Tudo além do LocalStack fica atrás de perfis do Compose
  (`llm`, `agentos`, `signoz`, `grafana`, `langfuse`, `pgvector`), opt-in, para
  não pesar no fluxo padrão. Inclui as configs de suporte (`otel/`, `grafana/`,
  `localstack/init/`, `pgvector/init/`).
- `README.md` do pacote apontando para a documentação detalhada na raiz do
  workspace.

### Changed

- Documentação detalhada (layout, arquitetura em camadas, tecnologias, setup com
  uv, como rodar via CLI `serve`, escopo e uso do Docker Compose por perfil,
  ambiente de linter/qualidade e deploy serverless com AWS SAM).
- `RunResult` passou a carregar a identidade do alvo avaliado (`target_ref` +
  `target_version`, obrigatórios) para que o laudo seja atribuível e comparável por
  alvo; `consolidate` agora recebe o manifesto e preenche esses campos, e o
  contrato de fronteira do import-linter foi estendido para autorizar o novo
  adapter durável a importar `boto3` (mantendo `domain`/`interface` proibidos).

### Fixed

- Orquestrador agora executa de fato pela engine da Agno: os passos deixaram de ser
  `no-op` decorativos e passaram a rodar os executores reais, com a camada não
  conforme ao contrato sendo isolada e nomeada em vez de silenciada.
- Build editável (`uv sync`/`uv run`) que falhava porque `pyproject.toml`
  referenciava um `README.md` inexistente em `code/`; o arquivo foi criado,
  restaurando a instalação do pacote.
- Testes de propriedade de configuração e de secrets deixaram de falhar em
  Linux/WSL: os geradores de valor de variável de ambiente passaram a excluir
  surrogates Unicode isolados (categoria `Cs`), que o `os.environ` não aceita e
  que quebravam a suíte de forma dependente de plataforma.

### Documentation

- Idealização das Sprints 0 e 1 formalizada em `docs/ideation/`
  (`00-master-vision.md`, `01-architecture.md`) com os respectivos decks de review
  em HTML. As decisões de arquitetura ADR-002 (concorrência) e ADR-003
  (persistência) foram registradas, e a ADR-001 foi promovida a **Aceita**. O
  `PROJECT.md` foi reconciliado para refletir o fluxo real (idealização + esqueleto
  executável em paralelo) e o status por sprint.

## [0.1.0] - 2026-09-11

### Added

- Bootstrap do ambiente executável: esqueleto backend rodável localmente e
  implantável em serverless, expondo uma única rota HTTP de saúde (`GET /health`).
- Arquitetura em quatro camadas (ports & adapters) em `src/qa_platform/`
  (`domain`, `application`, `infrastructure`, `interface`), com a separação
  verificada por import-linter (`importlinter.ini`).
- App FastAPI compartilhada entre execução local (uvicorn, via CLI `serve`) e AWS
  Lambda (Mangum), montada pelo `composition_root`.
- CLI com os subcomandos `serve` (sobe o serviço) e `health` (imprime o
  `HealthStatus` em JSON).
- Segurança de borda: trusted host, CORS restritivo (sem `*`), cabeçalhos de
  segurança, tratadores de erro neutros e stubs seguros (rate limit e redirect
  HTTPS) que nunca "aprovam tudo" por padrão.
- Resolução de configuração/segredos pelo pipe `env -> AWS Secrets Manager`, com
  falha rápida para variáveis obrigatórias (`SERVICE_VERSION`).
- Observabilidade: logging estruturado em JSON e tracing OpenTelemetry opcional
  (no-op quando desligado).
- Deploy serverless com AWS SAM (`template.yaml`, `samconfig.toml`): uma função
  Lambda + API Gateway, com dependências de runtime em uma Lambda Layer separada
  (`layers/runtime-deps/`).
- Dependências gerenciadas por uv com versões exatas fixadas (`pyproject.toml`,
  `uv.lock`); `boto3` e OpenTelemetry como extras opcionais por import tardio.
- Catálogo de configuração (`.env.example`) documentando cada variável lida pelo
  serviço.

[Unreleased]: https://keepachangelog.com/pt-BR/1.1.0/
[0.2.0]: https://keepachangelog.com/pt-BR/1.1.0/
[0.1.0]: https://keepachangelog.com/pt-BR/1.1.0/
