# QA Platform

QA sênior autônomo orientado por IA: recebe um repositório/alvo, detecta a stack,
monta um plano de testes baseado em risco, orquestra camadas de validação
(núcleo: IA/Agentes), correlaciona evidências e centraliza tudo para o
desenvolvedor decidir. A fase atual é o **bootstrap do ambiente executável** — um
esqueleto backend rodável localmente e implantável em serverless, expondo uma
única rota HTTP de saúde (`GET /health`). Nenhuma regra de negócio de QA é
implementada ainda.

A visão completa, escopo, não-objetivos e decisões de arquitetura são a fonte de
verdade da skill `project_definition_important` (`.kiro/skills/`).

## Layout do repositório

> **Regra inviolável:** TUDO que é implementado na QA Platform vive em `code/`. A
> raiz do workspace guarda apenas documentação/metadados e o portfólio de estudo.

```
qa-platform/
├── code/                 # RAIZ ÚNICA da implementação da QA Platform
│   ├── src/qa_platform/  #   domain / application / infrastructure / interface
│   ├── tests/            #   testes (espelham src/) + tests/architecture (import-linter)
│   ├── layers/runtime-deps/  # dependências de runtime empacotadas na Lambda Layer
│   ├── pyproject.toml    #   dependências (uv), versões exatas
│   ├── uv.lock
│   ├── template.yaml     #   IaC serverless (AWS SAM)
│   ├── samconfig.toml    #   configuração de deploy do SAM
│   ├── docker-compose.yml#   ambiente local de dependências (Dependency_Environment)
│   ├── otel/ grafana/ localstack/ pgvector/   # configs de suporte do compose
│   ├── importlinter.ini  #   contratos de camada (arquitetura)
│   └── .env.example      #   catálogo de variáveis de configuração
├── agents/               # portfólio de estudo Agno, isolado (um projeto por agente)
├── README.md             # este arquivo
├── CHANGELOG.md          # Keep a Changelog + SemVer
└── .kiro/                # skills, specs, steering, hooks
```

Todos os comandos abaixo rodam a partir de `code/`.

## Arquitetura (ports & adapters)

O código vive em `code/src/qa_platform/`, organizado em quatro camadas com a
dependência sempre apontando para dentro (`interface → application → domain`; a
infraestrutura implementa as ports definidas por dentro):

- `domain` — regras e valores puros (sem framework web, sem infraestrutura, sem `boto3`).
- `application` — casos de uso que orquestram o domínio via ports.
- `infrastructure` — config/secrets, observabilidade e segurança de borda.
- `interface` — app FastAPI, rota de saúde, handler Lambda (Mangum) e CLI.

A separação é verificada fisicamente por **import-linter** (`code/importlinter.ini`):
`domain` não importa framework/infra, e o `boto3` fica confinado ao adapter de
Secrets Manager. Detalhes na skill `agno-project-architecture-solid`.

## Tecnologias utilizadas

| Camada | Tecnologia | Papel |
|--------|------------|-------|
| Runtime | **Python 3.12** | linguagem do backend |
| Web | **FastAPI** + **Uvicorn** | app HTTP / servidor ASGI local |
| Serverless | **Mangum** | adapta a app FastAPI ao evento do AWS Lambda |
| Validação | **Pydantic v2** | validação na borda (entrada/saída) |
| AWS SDK | **boto3** (opcional, extra `aws`) | adapter de Secrets Manager (import tardio) |
| Observabilidade | **OpenTelemetry** (opcional, extra `otel`) | tracing OTLP (no-op quando desligado) |
| IaC | **AWS SAM** (`template.yaml`) | Lambda + API Gateway + Lambda Layer |
| Ambiente local | **Docker Compose** + **LocalStack** | AWS emulada e stack de dependências |
| Gestor de deps | **uv** | ambiente isolado, versões exatas (`uv.lock`) |
| Arquitetura | **import-linter** | contratos de camada (gate de arquitetura) |
| Testes | **pytest** + **Hypothesis** + **httpx** | suíte de testes e property-based testing |

Dependências de runtime têm versões **exatas fixadas** em `code/pyproject.toml`;
`boto3` e OpenTelemetry são extras opcionais carregados por import tardio, só quando
o recurso correspondente é ligado.

## Ambiente e dependências (uv)

Pré-requisito: [`uv`](https://docs.astral.sh/uv/) e Python 3.12.

```bash
uv sync                    # cria o .venv e instala deps (runtime + dev)
uv run pytest              # roda a suíte de testes
```

Copie o catálogo de configuração e ajuste os valores (o `.env` real nunca é
versionado):

```bash
cp .env.example .env
```

`SERVICE_VERSION` é a única variável **obrigatória** (exposta em `/health`); as
demais têm default seguro. Nenhum valor de configuração é fixado no código: tudo
vem de variável de ambiente. Os segredos são resolvidos pelo pipe
`env → AWS Secrets Manager` com falha rápida para as obrigatórias (skill
`agno-secrets`) — **nunca** cole valores reais no `.env.example` nem no `.env`
versionado; represente-os por um marcador (ex.: `CHANGE_ME`).

### Variáveis de ambiente

Catálogo completo em `code/.env.example`. Toggles usam `true`/`false`
(case-insensitive); vazio significa desligado/sem valor.

| Variável | Obrigatória | Exemplo | Descrição |
|----------|:-----------:|---------|-----------|
| `SERVICE_VERSION` | **sim** | `0.1.0` | Versão do serviço exposta no campo `version` de `GET /health`. Ausente → o serviço falha rápido na inicialização. |
| `MODEL_PROVIDER` | condicional¹ | `stub` | Provider de modelo da camada de IA. Sem default no código; se a camada de IA inicializar sem ele, falha rápido. Ex.: `stub`, `bedrock`, `ollama`. |
| `LOG_LEVEL` | não | `INFO` | Nível do logging estruturado JSON: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Default `INFO`. |
| `ENVIRONMENT` | não | `local` | Rótulo do ambiente (`local`/`dev`/`prod`). Default `local`. |
| `TRACING_ENABLED` | não | `false` | Liga o tracing OpenTelemetry (no-op quando `false`). Ligado implicitamente se `OTEL_EXPORTER_OTLP_ENDPOINT` estiver definido. Default `false`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | não | `http://localhost:4317` | Endpoint OTLP do coletor de traces. Quando presente, também liga o tracing. Default vazio. |
| `AWS_ENDPOINT_URL` | não | `http://localhost:4566` | Endpoint da AWS. Quando presente, liga o provider do Secrets Manager (LocalStack em dev). Vazio → usa só variáveis de ambiente. Default vazio. |
| `LOCALSTACK_PORT` | não | `4566` | Porta do LocalStack publicada no host (usada pelo docker-compose). Default `4566`. |
| `SECRET_NAME` | não | `qa-platform-secrets` | Nome lógico do segredo JSON no Secrets Manager de onde as chaves são resolvidas. Default `qa-platform-secrets`. |
| `CORS_ALLOWED_ORIGINS` | não | `https://app.exemplo.com` | Origens CORS permitidas em CSV (sem `*`). Vazio → nenhuma origem cross-site. Default vazio. |
| `ALLOWED_HOSTS` | não | `api.exemplo.com,exemplo.com` | Hosts confiáveis (CSV) do `TrustedHostMiddleware`. Em produção, restrinja aos hosts reais. Default `*`. |
| `HTTPS_REDIRECT_ENABLED` | não | `false` | Liga o redirect HTTP→HTTPS. Em geral o TLS termina no API Gateway; mantenha `false` localmente. Default `false`. |
| `RATE_LIMIT_ENABLED` | não | `false` | Liga o rate limit por principal/IP (stub). Default `false`. |
| `AUTH_ENABLED` | não | `false` | Liga a autenticação por request (stub seguro: nega até o JWT estar configurado). Default `false`. |
| `HOST` | não | `0.0.0.0` | Endereço de bind do servidor local (CLI `serve`). Default `0.0.0.0`. |
| `PORT` | não | `8000` | Porta do servidor local (CLI `serve`). Default `8000`. |

¹ `MODEL_PROVIDER` só é exigida quando a camada de IA é inicializada; não é
necessária para subir apenas a rota de saúde do bootstrap atual.

## Rodar localmente

A borda de entrada é a CLI (`qa_platform.interface.cli.main`), com dois subcomandos:

```bash
# serve: sobe o serviço via uvicorn (host/porta por env HOST/PORT; default 0.0.0.0:8000).
uv run python -m qa_platform.interface.cli.main serve
curl http://127.0.0.1:8000/health

# health (default): resolve a config e imprime o HealthStatus em JSON, sem subir servidor.
uv run python -m qa_platform.interface.cli.main health
```

A app ASGI é `qa_platform.interface.api.main:app` (a mesma servida pelo uvicorn
localmente e pelo Mangum na Lambda), montada pelo `composition_root`. Se
`SERVICE_VERSION` faltar, a inicialização falha rápido — a app nunca sobe sem a
config obrigatória.

## Ambiente local de dependências (Docker Compose)

O `code/docker-compose.yml` sobe as tecnologias de terceiros necessárias para
desenvolver e observar a plataforma localmente, sem custo e sem rede externa. Ele
já declara, desde o início, o **conjunto padrão completo** de serviços do
portfólio; para não pesar no fluxo diário, tudo além do LocalStack fica atrás de
**perfis** do Compose (opt-in).

### Escopo do compose

| Serviço | Perfil | Porta (host) | Papel |
|---------|--------|--------------|-------|
| **LocalStack** | (núcleo, sobe sempre) | `${LOCALSTACK_PORT:-4566}` | AWS emulada: API Gateway, Lambda, DynamoDB, Secrets Manager, SSM, S3 |
| **Ollama** | `llm` | 11434 | provider de LLM local / fallback custo zero |
| **AgentOS** | `agentos` | 7777 | acompanhamento de runs/sessions/traces |
| **SigNoz** | `signoz` | 3301 | backend OTLP tudo-em-um (traces/logs/métricas) |
| **Grafana + Tempo + Loki + Prometheus** | `grafana` | 3000 | os três sinais em backends separados |
| **Langfuse (+ Postgres)** | `langfuse` | 3100 | tracing focado em LLM |
| **pgvector** | `pgvector` | 5433 | Postgres + extensão pgvector (RAG com PgVector) |

Configs de suporte (montadas nos serviços): `code/localstack/init/` (bootstrap
idempotente do segredo), `code/otel/collector-config.yaml` (fan-out OTLP no perfil
`grafana`), `code/grafana/datasources.yaml` (datasources provisionados) e
`code/pgvector/init/` (habilita a extensão `vector`).

### Uso

```bash
docker compose config                                 # valida a sintaxe do arquivo
docker compose up                                     # só o LocalStack (núcleo), alcança healthy
docker compose --profile llm --profile agentos up     # + Ollama + AgentOS (http://localhost:7777)
docker compose --profile signoz up                    # + backend OTLP SigNoz (http://localhost:3301)
docker compose --profile grafana up                   # + stack Grafana (http://localhost:3000)
docker compose --profile langfuse up                  # + Langfuse (http://localhost:3100)
docker compose --profile pgvector up                  # + Postgres/pgvector (porta 5433)
docker compose down                                   # derruba o ambiente
```

> **Conflito de porta OTLP (intencional):** SigNoz (`signoz`) e o OTel Collector
> (`grafana`) publicam as **mesmas** portas OTLP no host (`4317` gRPC, `4318`
> HTTP). Ative **um** backend de tracing OTLP por vez. O `langfuse` usa portas
> próprias e pode subir junto de qualquer um.

O AgentOS é conveniência de desenvolvimento; os endpoints (AWS, OTLP, Ollama) vêm
por variável de ambiente, então o código **não muda** entre local e produção —
troca-se apenas a env. Detalhes na skill `agno-local-dev-environment`.

## Ambiente de linter e qualidade

O gate de arquitetura roda localmente (e no CI), sem custo de token de LLM:

```bash
# Contratos de camada (arquitetura ports & adapters).
uv run lint-imports --config importlinter.ini

# Suíte de testes (inclui tests/architecture/ que valida o import-linter).
uv run pytest
```

- **import-linter** (`code/importlinter.ini`) — três contratos: camadas
  (`interface → application → domain`), `domain` puro (sem FastAPI/Pydantic/
  Starlette/uvicorn/mangum/boto3 nem outras camadas) e `boto3` confinado ao adapter
  de Secrets Manager.
- **pytest + Hypothesis** — testes unitários e property-based; a árvore de
  `code/tests/` espelha `code/src/`.

O tooling completo de qualidade recomendado (Ruff, mypy, Bandit, pip-audit,
gitleaks, Radon/Xenon, cobertura, pre-commit, commitizen) está detalhado na skill
`agno-code-quality-tools`, com scripts de setup em `scripts/`.

## Deploy (serverless: AWS SAM)

A mesma app FastAPI é publicada atrás do API Gateway via **AWS Lambda**, adaptada
por Mangum. O `template.yaml` declara exatamente uma função Lambda (`GET /health`)
com as dependências de runtime em uma **Lambda Layer separada** (`layers/runtime-deps/`)
— o artefato da função contém apenas o código da aplicação.

```bash
# Compila as deps do Layer no ambiente da Lambda e valida o template.
sam build --use-container
sam validate --lint

# Ensaio local (opcional): sobe a API em http://localhost:3000
sam local start-api

# Deploy (usa code/samconfig.toml; stack qa-platform em us-east-1 por padrão).
sam deploy --guided       # primeiro deploy (salva as escolhas em samconfig.toml)
sam deploy                # deploys seguintes
```

Ajuste `region` em `code/samconfig.toml` conforme a conta/ambiente alvo antes do
primeiro deploy. Antes de subir à AWS real, dá para ensaiar o fluxo serverless
contra o LocalStack do compose. Padrões de infra (IAM least-privilege, timeouts,
empacotamento) estão nas skills `agno-lambda-apigateway` e `agno-aws`.

## Referências

- `.kiro/skills/project_definition_important/` — escopo, visão e arquitetura (fonte de verdade).
- `.kiro/specs/executable-environment-bootstrap/` — requisitos, design e tarefas desta fase.
- Skills `agno-project-architecture-solid`, `agno-local-dev-environment`,
  `agno-lambda-apigateway`, `agno-secrets`, `agno-observability`, `agno-code-quality-tools`.
