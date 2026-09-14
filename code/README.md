# QA Platform — implementação (`code/`)

Esta pasta é a **raiz única de tudo que é implementado** na QA Platform: código-fonte,
IaC (AWS SAM), ambiente local (Docker Compose), dependências (uv), qualidade
(import-linter) e testes. A raiz do workspace guarda apenas documentação/metadados.

A documentação detalhada (arquitetura, tecnologias, escopo do compose, ambiente de
linter e deploy) está no **README da raiz do workspace** (`../README.md`).

## Início rápido

Rode tudo a partir desta pasta (`code/`):

```bash
uv sync                                                   # deps no .venv isolado
uv run python -m qa_platform.interface.cli.main serve     # sobe a API local (GET /health)
uv run --env-file .env python -m qa_platform.interface.cli.main suggest-manifest draft.example.json  # Fase 2 advisory (opt-in, exige MODEL_PROVIDER)
uv run pytest                                             # suíte de testes
uv run lint-imports --config importlinter.ini             # contratos de camada
docker compose config                                     # valida o ambiente local
```

Descoberta híbrida de alvo (Fase 1 determinística + Fase 2 advisory por LLM),
fronteiras de arquitetura e demais detalhes estão no README da raiz.

## Estrutura

- `src/qa_platform/` — camadas `domain` / `application` / `infrastructure` / `interface`.
- `tests/` — testes que espelham `src/` (+ `tests/architecture/` para o import-linter).
- `template.yaml`, `samconfig.toml`, `layers/runtime-deps/` — deploy serverless (SAM).
- `docker-compose.yml` + `otel/` `grafana/` `localstack/` `pgvector/` — ambiente local.
- `pyproject.toml`, `uv.lock` — dependências com versões exatas.
- `importlinter.ini` — contratos de arquitetura (ports & adapters).
- `.env.example` — catálogo de variáveis de configuração.
