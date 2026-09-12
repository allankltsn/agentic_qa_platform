# Implementation Plan: Executable Environment Bootstrap (Plano de Implementação)

## Overview

Este plano converte o design do **bootstrap do ambiente executável** em uma série de
tarefas de código incrementais e test-first. Cada tarefa constrói sobre as anteriores
e termina com a integração das partes (composition_root, handler Lambda, infra SAM),
sem código órfão. O escopo é um esqueleto **rodável e implantável** com uma única rota
`GET /health` — sem regra de negócio de QA.

A abordagem segue as camadas de dentro para fora (domain → application →
infrastructure → interface) e, ao final, a infraestrutura operacional (Docker Compose,
SAM, scripts) e as tarefas de validação. A linguagem é **Python** (definida no design),
gerenciada por **uv** com versões fixas.

Convenções:
- Tarefas marcadas com `*` são de teste e podem ser puladas para um MVP mais rápido.
- Testes de propriedade usam **Hypothesis** (mín. 100 iterações), uma propriedade por
  teste, com a tag de comentário `# Feature: executable-environment-bootstrap, Property {n}`.
- Cada tarefa referencia os requisitos que satisfaz.

## Tasks

- [x] 1. Configurar estrutura do projeto e ambiente com uv
  - Criar o diretório `qa-platform/` com o layout `src/qa_platform/` e as quatro
    camadas (`domain`, `application`, `infrastructure`, `interface`) como pacotes
    (`__init__.py` em cada), e o espelho em `tests/`
  - Criar `pyproject.toml` declarando as dependências via uv com **versões exatas
    fixadas** (fastapi, mangum, pydantic, uvicorn, hypothesis, pytest, import-linter;
    boto3 e opentelemetry como dependências de runtime/opcionais)
  - Gerar/versionar `uv.lock` reproduzível
  - Criar `importlinter.ini` com o contrato de camadas (domain isolado; boto3 confinado
    ao adapter de Secrets Manager)
  - _Requirements: 5.1, 5.4_

- [x] 2. Implementar a camada domain
  - [x] 2.1 Implementar `HealthStatus` (value object puro)
    - Criar `src/qa_platform/domain/health.py` com o dataclass frozen `HealthStatus`
      (campos `status`, `version`), a constante `STATUS_OK` e o construtor `healthy`
    - Sem qualquer import de framework web ou infraestrutura
    - _Requirements: 1.2, 1.3, 5.2_

  - [x] 2.2 Implementar hierarquia de erros de domínio
    - Criar `src/qa_platform/domain/exceptions.py` com `DomainError` (base) e
      `ConfigurationDomainError`, puros (sem status HTTP nem infraestrutura)
    - _Requirements: 5.2_

  - [x] 2.3 Escrever testes unitários do domain
    - `tests/domain/test_health.py`: `HealthStatus.healthy` produz `status == "ok"`
      e preserva a versão
    - `tests/domain/test_exceptions.py`: `ConfigurationDomainError` herda de
      `DomainError`
    - _Requirements: 1.2, 1.3, 5.2_

- [x] 3. Implementar o caso de uso da camada application
  - [x] 3.1 Implementar `GetHealthStatus`
    - Criar `src/qa_platform/application/get_health_status.py` recebendo a versão por
      injeção e produzindo o `HealthStatus`; sem ler env var nem conhecer FastAPI
    - _Requirements: 1.2, 1.3, 5.2_

  - [x] 3.2 Escrever teste de propriedade do fluxo de versão (Property 1)
    - `tests/application/test_get_health_status.py`
    - **Property 1: Versão da configuração flui íntegra para a resposta de saúde**
    - Hypothesis, mín. 100 iterações, gerador de strings de versão não-vazias
      (`st.text` filtrando vazio/whitespace); comentário
      `# Feature: executable-environment-bootstrap, Property 1`
    - **Validates: Requirements 1.2, 1.3**

- [x] 4. Implementar a infraestrutura de secrets (ports + adapters + resolver)
  - [x] 4.1 Definir a porta e os adapters de secrets
    - Criar `src/qa_platform/infrastructure/secrets/ports.py` (`SecretsProvider`
      Protocol) e `src/qa_platform/infrastructure/secrets/in_memory.py`
      (`InMemorySecretsProvider`, vazio == None)
    - _Requirements: 7.1_

  - [x] 4.2 Implementar o `SecretResolver` (pipe env → Secrets Manager, fail-fast)
    - Criar `src/qa_platform/infrastructure/secrets/resolver.py` com `MissingSecretError`
      e `SecretResolver.resolve` (env vence; vazio/whitespace == ausente; erro nomeia a
      variável, nunca o valor)
    - _Requirements: 7.1, 7.2_

  - [x] 4.3 Escrever teste de propriedade do pipe de fallback (Property 4)
    - `tests/infrastructure/test_secrets_resolver_property.py`
    - **Property 4: Pipe de fallback do SecretResolver (env vence; ausente em ambos → erro nomeando a variável)**
    - Hypothesis, mín. 100 iterações, gerando nome de var + distribuição de valores
      entre env e `InMemorySecretsProvider`; comentário
      `# Feature: executable-environment-bootstrap, Property 4`
    - **Validates: Requirements 7.1, 7.2**

  - [x] 4.4 Implementar o adapter AWS Secrets Manager (import tardio de boto3)
    - Criar `src/qa_platform/infrastructure/secrets/aws_secrets_manager.py`
      (`AWSSecretsManagerProvider`), com `import boto3` tardio dentro do `_load`, cache
      por processo, segredo não-JSON tratado como vazio, `AWS_ENDPOINT_URL`/`SECRET_NAME`
      por env
    - _Requirements: 7.1_

  - [x] 4.5 Escrever testes unitários dos secrets (3 ramos + importabilidade sem SDK)
    - `tests/infrastructure/test_config.py` (parte secrets): env presente vence; só no
      provider; ausente em ambos → `MissingSecretError`; verificar que o adapter é
      **importável sem boto3** (import tardio)
    - _Requirements: 7.1, 7.2_

- [x] 5. Implementar a configuração (`Settings` + `load_settings`)
  - [x] 5.1 Implementar `load_settings` consumindo o `SecretResolver` com fail-fast agregado
    - Criar `src/qa_platform/infrastructure/config.py` com `MissingConfigError`,
      `Settings` (frozen), `_REQUIRED`/`_OPTIONAL`; coletar **todas** as obrigatórias
      ausentes/vazias em uma passada e levantar um único erro nomeando cada uma;
      aplicar defaults às opcionais; `SERVICE_VERSION` obrigatória
    - _Requirements: 1.4, 7.1, 7.2, 7.3, 7.4_

  - [x] 5.2 Escrever teste de propriedade da falha rápida agregada (Property 2)
    - `tests/infrastructure/test_config_required_property.py`
    - **Property 2: Falha rápida agregada de variáveis obrigatórias**
    - Hypothesis, mín. 100 iterações, gerando subconjunto não-vazio de obrigatórias
      ausentes/vazias/whitespace; a mensagem deve conter o nome de **cada** ausente;
      comentário `# Feature: executable-environment-bootstrap, Property 2`
    - **Validates: Requirements 1.4, 7.2, 7.3**

  - [x] 5.3 Escrever teste de propriedade dos defaults opcionais (Property 3)
    - `tests/infrastructure/test_config_optional_property.py`
    - **Property 3: Defaults de variáveis opcionais**
    - Hypothesis, mín. 100 iterações, obrigatórias válidas + opcionais ora ausentes ora
      com valor; comentário `# Feature: executable-environment-bootstrap, Property 3`
    - **Validates: Requirements 7.4**

- [x] 6. Checkpoint - Garantir que os testes de núcleo passam
  - Garantir que todos os testes de domain, application, secrets e config passam. Se
    surgirem dúvidas, pergunte ao usuário.

- [x] 7. Implementar a observabilidade (logging + tracing)
  - [x] 7.1 Implementar logging JSON e tracing OTel (no-op quando desligado)
    - Criar `src/qa_platform/infrastructure/observability/logging.py`
      (`build_json_logger`, `log_event` uma linha JSON, sem PII/segredo) e
      `src/qa_platform/infrastructure/observability/tracing.py` (`configure_tracing`
      no-op quando desligado por env; import tardio de OTel; retorna bool)
    - _Requirements: 1.2, 1.3_

  - [x] 7.2 Escrever testes da observabilidade
    - `tests/infrastructure/observability/test_logging.py`: `log_event` emite JSON de
      uma linha, sem PII/segredo
    - `tests/infrastructure/observability/test_tracing.py`: `configure_tracing` retorna
      `False` e é no-op quando o tracing está desligado por env
    - _Requirements: 1.2, 1.3_

- [x] 8. Implementar a segurança de borda (funcionais + stubs seguros)
  - [x] 8.1 Implementar os controles funcionais de borda
    - Criar `src/qa_platform/infrastructure/security/headers.py` (nosniff/HSTS/X-Frame/CSP),
      `cors.py` (restritivo, sem `*`), `trusted_host.py`, `error_handlers.py` (resposta
      neutra, sem stack trace) e `input_limits.py` (limite de payload)
    - _Requirements: 1.1, 1.2, 1.5_

  - [x] 8.2 Implementar os stubs seguros dependentes de identidade
    - Criar `src/qa_platform/infrastructure/security/jwt.py` (stub que levanta
      `NotImplementedError`), `rate_limit.py` (default OFF por env) e
      `https_redirect.py` (default OFF por env); nunca "aprova tudo"
    - _Requirements: 1.5_

  - [x] 8.3 Escrever testes da segurança de borda
    - `tests/infrastructure/security/test_headers.py`: headers presentes na resposta
    - `tests/infrastructure/security/test_error_handlers.py`: erro não vaza stack trace
    - `tests/infrastructure/security/test_jwt.py`: stub levanta `NotImplementedError`
    - _Requirements: 1.5_

- [x] 9. Implementar a interface HTTP (app FastAPI + rota de saúde + segurança)
  - [x] 9.1 Implementar a rota de saúde
    - Criar `src/qa_platform/interface/api/health_routes.py` com `HealthResponse`
      (Pydantic) e `build_health_router(use_case)` expondo `GET /health`
    - _Requirements: 1.1, 1.2, 1.3, 5.5_

  - [x] 9.2 Implementar a factory `create_app` + `apply_security`
    - Criar `src/qa_platform/interface/api/api.py` com `apply_security` (trusted host,
      CORS, headers, error handlers, rate limit stub, https redirect stub) e
      `create_app` (docs desabilitadas, monta `GetHealthStatus` e inclui o router)
    - _Requirements: 1.1, 1.2, 1.5, 3.4, 5.5_

  - [x] 9.3 Implementar a dependency de authn (stub seguro)
    - Criar `src/qa_platform/interface/api/security.py` com `get_current_principal`
      (`AUTH_ENABLED` default false → `None`; ligado sem JWT → `401`; nunca aprova)
    - _Requirements: 1.5_

  - [x] 9.4 Escrever teste de propriedade da rota de saúde (Property 1) e testes por exemplo
    - `tests/interface/test_health_routes.py`: via `TestClient`, `GET /health` → `200`,
      corpo `{"status":"ok","version":...}`, headers de segurança presentes, e
      caminho/método não definido → `404`
    - **Property 1: Versão da configuração flui íntegra para a resposta de saúde** —
      variando a `service_version` da app e conferindo o campo `version` da resposta;
      Hypothesis, mín. 100 iterações, comentário
      `# Feature: executable-environment-bootstrap, Property 1`
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5, 3.5**

- [x] 10. Implementar o ponto de entrada Lambda (Mangum) e o CLI
  - [x] 10.1 Implementar o Lambda_Handler
    - Criar `src/qa_platform/interface/api/main.py` com `app = build_app()` e
      `handler = Mangum(app)`; falha de init sobe no import (nunca retorna 200)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 10.2 Escrever teste do Lambda_Handler
    - Invocar o `handler` com um evento API Gateway de `GET /health` → `200` com o corpo
      de saúde; verificar que init com config ausente falha sem `200`
    - _Requirements: 3.2, 3.3_

  - [x] 10.3 Implementar o CLI fino
    - Criar `src/qa_platform/interface/cli/main.py` com `main(argv)`: `serve` sobe via
      uvicorn; `health` imprime o status via composition_root/caso de uso, exit code 0
    - _Requirements: 6.2_

  - [x] 10.4 Escrever teste do CLI
    - `tests/interface/test_cli.py`: o comando `health` imprime o status e retorna exit
      code `0`
    - _Requirements: 6.2_

- [x] 11. Implementar o composition_root (wiring)
  - Criar `src/qa_platform/composition_root.py` montando o `SecretResolver` (com
    `AWSSecretsManagerProvider` opcional quando `AWS_ENDPOINT_URL` presente), resolvendo
    `Settings` (fail-fast na init), configurando logging e tracing e chamando
    `create_app` com `service_version`, `allowed_hosts` e `cors_origins`
  - _Requirements: 1.3, 1.4, 3.1, 7.1, 7.2_

- [x] 12. Escrever o teste de fronteiras de arquitetura
  - `tests/architecture/test_layer_boundaries.py`: via import-linter (ou verificação
    AST) garantir que `domain` não importa framework web, infraestrutura nem outras
    camadas, e que `boto3` não vaza para `domain` nem `interface` (só no adapter)
  - _Requirements: 5.2, 5.3, 5.5_

- [x] 13. Checkpoint - Garantir que a aplicação e seus testes passam
  - Garantir que toda a aplicação (domain → interface, wiring) e seus testes passam. Se
    surgirem dúvidas, pergunte ao usuário.

- [x] 14. Criar o ambiente local de dependências (Docker Compose)
  - Criar `qa-platform/docker-compose.yml` com o LocalStack (simulando AWS, incluindo
    Secrets Manager), portas configuráveis por variável de ambiente com default,
    healthchecks e o serviço considerado pronto quando healthy
  - _Requirements: 2.1, 2.2, 2.4, 2.5_

- [x] 15. Criar o empacotamento e deploy via AWS SAM
  - [x] 15.1 Criar o `template.yaml` e `samconfig.toml`
    - `template.yaml`: exatamente uma função Lambda com handler
      `qa_platform.interface.api.main.handler`, `Timeout: 30`, `MemorySize: 512`, evento
      API Gateway `GET /health`, dependências de runtime em uma Layer separada e as
      variáveis de ambiente obrigatórias declaradas com valor não vazio; criar
      `samconfig.toml`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 15.2 Criar os artefatos de suporte ao SAM
    - Criar `qa-platform/layers/runtime-deps/requirements.txt` (dependências de runtime
      da Layer) e `qa-platform/events/health-get.json` (evento API Gateway para
      `sam local invoke`)
    - _Requirements: 4.4_

- [x] 16. Criar os scripts de desenvolvedor
  - Criar `qa-platform/scripts/setup.sh`, `run-local.sh`, `build.sh` e `deploy.sh`; cada
    um deve encerrar com exit code 0 no sucesso e com exit code diferente de zero e uma
    mensagem que identifica a dependência ausente/causa da falha, sem aplicar mudanças
    parciais
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 17. Criar o catálogo de configuração e a exclusão de segredos
  - Criar `qa-platform/.env.example` com uma entrada para **cada** variável lida pelo
    Config_Resolver (incluindo as novas: `SERVICE_VERSION`, `LOG_LEVEL`, `ENVIRONMENT`,
    `AWS_ENDPOINT_URL`, `LOCALSTACK_PORT`, `SECRET_NAME`, `CORS_ALLOWED_ORIGINS`,
    `ALLOWED_HOSTS`, `HTTPS_REDIRECT_ENABLED`, `RATE_LIMIT_ENABLED`, `AUTH_ENABLED`,
    `TRACING_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`), com segredos como marcadores; e
    `qa-platform/.gitignore` excluindo `.env` e arquivos de segredos locais do VCS
  - _Requirements: 7.5, 7.6_

- [x] 18. Validação final
  - [x] 18.1 Validar a infraestrutura (SAM + Compose)
    - Rodar `docker compose config` para validar o arquivo e `sam build` (ou `sam
      validate`) para confirmar o empacotamento e a ausência de erros de validação de
      template
    - _Requirements: 2.1, 4.6, 4.7_

  - [x] 18.2 Rodar a suíte completa de testes
    - Executar toda a suíte (`pytest`), incluindo import-linter, garantindo que todos os
      testes passam
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 19. Checkpoint final - Garantir que tudo passa
  - Garantir que todos os testes passam, o `sam build` produz artefato e o Docker
    Compose valida. Se surgirem dúvidas, pergunte ao usuário.

## Notes

- Tarefas marcadas com `*` são opcionais (testes) e podem ser puladas para um MVP mais
  rápido; as tarefas de implementação de núcleo nunca são opcionais.
- Cada tarefa referencia requisitos específicos para rastreabilidade.
- Os checkpoints garantem validação incremental em quebras razoáveis.
- Os testes de propriedade (Hypothesis, mín. 100 iterações, uma propriedade por teste)
  validam as propriedades universais de correção; testes unitários/por exemplo cobrem
  casos concretos e de borda.
- PBT se aplica apenas à lógica pura (Properties 1–4); IaC, scripts, rota `/health`,
  observabilidade e segurança de borda usam testes por exemplo/integração, conforme a
  Testing Strategy do design.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "4.1"] },
    { "id": 2, "tasks": ["2.3", "3.1", "4.2", "4.4", "7.1", "8.1", "8.2"] },
    { "id": 3, "tasks": ["3.2", "4.3", "4.5", "5.1", "7.2", "8.3"] },
    { "id": 4, "tasks": ["5.2", "5.3", "9.1", "9.3"] },
    { "id": 5, "tasks": ["9.2"] },
    { "id": 6, "tasks": ["9.4", "10.1", "10.3"] },
    { "id": 7, "tasks": ["10.2", "10.4", "11"] },
    { "id": 8, "tasks": ["12", "14", "15.1", "15.2", "16", "17"] },
    { "id": 9, "tasks": ["18.1", "18.2"] }
  ]
}
```
