---
inclusion: fileMatch
fileMatchPattern: "**/Dockerfile,**/samconfig.{toml,yaml},**/.github/workflows/*.yml,**/requirements.txt,**/pyproject.toml,**/package.json"
---

# Configuração e Infraestrutura como Código

Padrões para arquivos de configuração, dependências e pipelines CI/CD do time. Para padrões de templates SAM, consulte #[[file:.kiro/steering/05-sam-templates.md]]. Para padrões gerais, consulte #[[file:.kiro/steering/01-padroes-gerais.md]].

## Dockerfile

- Usar multi-stage builds para separar build e runtime — reduz tamanho da imagem final
- Preferir imagens base mínimas: `python:3.12-slim`, `node:20-alpine` ou `distroless`
- Executar aplicação como usuário non-root — nunca rodar como `root` em produção

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# Runtime stage
FROM python:3.12-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /app/deps /app/deps
COPY src/ ./src/
ENV PYTHONPATH=/app/deps
USER appuser
CMD ["python", "-m", "src.main"]
```

- Ordenar instruções do menos mutável para o mais mutável (cache de layers)
- Usar `.dockerignore` para excluir arquivos desnecessários (`.git`, `node_modules`, `__pycache__`, `.env`)
- Fixar versões de imagens base com tag específica — evitar `latest`
- Usar `COPY` em vez de `ADD` — `ADD` apenas para descompactar arquivos
- Não armazenar segredos na imagem — usar variáveis de ambiente ou secrets em runtime
- Executar scan de vulnerabilidades: `docker scout`, `trivy`, `snyk container`
- Definir `HEALTHCHECK` quando aplicável para monitoramento de containers

## samconfig — Configuração de Deploy SAM

- Organizar por ambiente usando seções `[default]`, `[staging]`, `[production]`
- Definir `stack_name`, `s3_bucket`, `region` e `capabilities` por ambiente

```toml
version = 0.1

[default.deploy.parameters]
stack_name = "meu-servico-dev"
resolve_s3 = true
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = "Environment=dev"
confirm_changeset = false

[staging.deploy.parameters]
stack_name = "meu-servico-staging"
resolve_s3 = true
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = "Environment=staging"
confirm_changeset = true

[production.deploy.parameters]
stack_name = "meu-servico-prod"
resolve_s3 = true
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = "Environment=prod"
confirm_changeset = true
```

- Usar `resolve_s3 = true` para criação automática do bucket de deploy
- Habilitar `confirm_changeset = true` em staging e produção
- Usar `parameter_overrides` para passar variáveis de ambiente ao template
- Nunca incluir segredos no samconfig — usar SSM Parameter Store ou Secrets Manager
- Manter samconfig versionado no repositório — é configuração de infraestrutura

## GitHub Actions — Pipeline Serverless

- Estruturar pipeline com jobs separados: `lint`, `test`, `build`, `deploy`
- Usar caching para acelerar builds (pip, npm, SAM)

```yaml
name: Deploy Serverless
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      - uses: aws-actions/setup-sam@v2
      - run: sam build
      - run: sam deploy --config-env production --no-confirm-changeset
```

- Usar OIDC (`id-token: write`) para autenticação AWS — nunca access keys estáticas
- Armazenar ARNs e configurações sensíveis em GitHub Secrets
- Usar `actions/cache` para dependências quando o setup action não suportar cache nativo
- Fixar versões de actions com tag completa (ex: `@v4`) — evitar `@main` ou `@latest`
- Executar testes em PRs e deploy apenas na branch principal
- Adicionar step de `sam validate` antes do build para validação antecipada
- Configurar timeout adequado para jobs de deploy (padrão: 30 minutos)
- Usar matrix strategy para testar em múltiplas versões quando necessário

## requirements.txt / pyproject.toml — Dependências Python

- Pinar versões exatas em `requirements.txt` para reprodutibilidade: `boto3==1.34.100`
- Separar dependências de produção e desenvolvimento:
  - `requirements.txt` — dependências de runtime
  - `requirements-dev.txt` — ferramentas de teste, lint, formatação
- Usar `pyproject.toml` como fonte única de configuração quando possível:

```toml
[project]
name = "meu-servico"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
    "boto3>=1.34,<2.0",
    "aws-lambda-powertools>=3.0,<4.0",
    "pydantic>=2.0,<3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "moto>=5.0",
    "ruff>=0.4",
    "mypy>=1.10",
]
```

- Usar range de versões compatíveis em `pyproject.toml` (`>=1.0,<2.0`) e pinar exato em `requirements.txt`
- Gerar `requirements.txt` a partir de `pyproject.toml`: `pip-compile pyproject.toml`
- Auditar dependências regularmente: `pip-audit`, `safety check`
- Manter dependências atualizadas — usar Dependabot ou Renovate para PRs automáticos
- Não incluir dependências desnecessárias — cada dependência aumenta cold start e superfície de ataque

## package.json — Dependências e Scripts Node.js

- Usar versionamento semântico com range adequado: `^` para minor updates, `~` para patch only
- Definir scripts padronizados para operações comuns:

```json
{
  "name": "meu-servico",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "lint": "eslint src/",
    "lint:fix": "eslint src/ --fix",
    "format": "prettier --write src/",
    "deploy": "sam build && sam deploy",
    "deploy:staging": "sam build && sam deploy --config-env staging",
    "deploy:prod": "sam build && sam deploy --config-env production"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}
```

- Separar `dependencies` (runtime) de `devDependencies` (build, test, lint)
- Definir `engines` para garantir versão mínima de Node.js
- Usar `package-lock.json` versionado no repositório — garante reprodutibilidade
- Scripts obrigatórios: `build`, `test`, `lint`, `deploy`
- Auditar dependências regularmente: `npm audit`
- Usar `--save-exact` para dependências críticas que precisam de versão fixa
- Manter dependências atualizadas — usar Dependabot ou Renovate para PRs automáticos
