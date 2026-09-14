# scripts/

Utilitarios deterministicos de uso geral do workspace — sem logica de negocio de
nenhum agente. Cobrem dois propositos:

1. **Developer_Scripts** do ciclo dev/deploy da QA Platform (setup, execucao
   local, build e deploy serverless).
2. **Tooling de qualidade de codigo** reaproveitavel entre os agentes Agno
   (`setup_code_quality.sh` + `templates/`).

Todos os scripts falham rapido: verificam as dependencias de sistema ANTES de
qualquer trabalho e encerram com exit code != 0 e uma mensagem nomeando a
dependencia/causa ausente, sem aplicar mudancas parciais.

## Conteudo

| Arquivo | Proposito |
| --- | --- |
| `setup.sh` | Instala deps e prepara o ambiente isolado (`uv sync`); cria `.env` a partir de `.env.example` se ausente. |
| `run-local.sh` | Sobe o servico localmente (uvicorn) expondo `GET /health`. |
| `build.sh` | Build do artefato serverless (`sam build`). |
| `deploy.sh` | Deploy do artefato serverless (`sam deploy`, usando `samconfig.toml`). |
| `setup_code_quality.sh` | Instala e configura o tooling de qualidade de codigo num agente. |
| `commit_flow.py` | Fluxo commit/push/PR guiado por um arquivo em `commits/` (conteudo redigido por fora; script so executa o git). |
| `templates/pyproject.quality.toml` | Bloco base das secoes `[tool.*]` de qualidade, para mesclar ao `pyproject.toml`. |
| `templates/.pre-commit-config.yaml` | Hooks de pre-commit (rodam local, sem token de LLM). |
| `templates/import-linter.toml` | Contrato de arquitetura em camadas (import-linter). |

---

## 1. Developer_Scripts (ciclo dev/deploy)

Rode a partir da raiz do projeto onde vivem `pyproject.toml`, `template.yaml` e
`samconfig.toml` — ou seja, `code/` na QA Platform. Os scripts resolvem a raiz a
partir da propria localizacao, entao `bash scripts/<nome>.sh` tambem funciona da
raiz do workspace quando os scripts estao ao lado do projeto.

### Ferramentas usadas

| Ferramenta | Para que serve | Onde instalar |
| --- | --- | --- |
| **uv** | Gestor de dependencias/ambiente Python isolado (versoes exatas via `uv.lock`); executa comandos no `.venv` com `uv run`. | https://docs.astral.sh/uv/ |
| **AWS SAM CLI** (`sam`) | Build e deploy do app serverless (Lambda + API Gateway + Lambda Layer) a partir do `template.yaml`. | https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html |
| **uvicorn** | Servidor ASGI que sobe a app FastAPI localmente (invocado via `uv run`, nao precisa estar no PATH do sistema). | dependencia do projeto (`uv sync`) |

### Como usar

```bash
# 1) Preparar o ambiente (deps + .env). Requer: uv.
bash scripts/setup.sh

# 2) Rodar localmente em http://0.0.0.0:8000 (rota GET /health). Requer: uv.
#    Le SERVICE_VERSION do .env/ambiente (OBRIGATORIA; falha rapido se ausente).
#    Ajustaveis por env: HOST (default 0.0.0.0), PORT (default 8000).
bash scripts/run-local.sh

# 3) Build do artefato serverless. Requer: sam. Args extras vao para o sam.
bash scripts/build.sh
bash scripts/build.sh --use-container   # compila as deps no runtime alvo da Lambda

# 4) Deploy. Requer: sam + samconfig.toml + credenciais AWS.
bash scripts/deploy.sh                   # deploy usando o samconfig.toml
bash scripts/deploy.sh --guided          # primeiro deploy interativo (gera o samconfig)
```

---

## 2. Tooling de qualidade de codigo

`setup_code_quality.sh` configura, de forma idempotente, o gate de qualidade num
agente: adiciona as deps de dev via `uv`, copia os templates que faltam (sem
sobrescrever), instala os hooks do pre-commit e roda uma verificacao inicial.

```bash
# a partir da raiz do workspace, aponte para o projeto/agente alvo
bash scripts/setup_code_quality.sh code
bash scripts/setup_code_quality.sh agents/01-suporte-sla-fallback
```

> As secoes `[tool.ruff]`, `[tool.mypy]`, `[tool.bandit]`, `[tool.importlinter]`
> e `[tool.commitizen]` precisam ser **mescladas** ao `pyproject.toml` do alvo
> (o script nao edita o `pyproject.toml`); use `templates/pyproject.quality.toml`
> como referencia e ajuste `packages`/`root_package` para o pacote do projeto
> (ex.: `qa_platform`).

### Ferramentas usadas, para que servem e como usar

Todas rodam LOCALMENTE (e no CI), sem gasto de token de LLM. Os comandos abaixo
rodam dentro da pasta do alvo (`code/` na QA Platform).

| Ferramenta | Para que serve | Como usar |
| --- | --- | --- |
| **Ruff** | Lint + format (substitui Flake8/isort/pyupgrade/Black); tambem cobre complexidade (mccabe) e regras de seguranca. | `uv run ruff check . --fix && uv run ruff format .` |
| **mypy** | Checagem estatica de tipos. | `uv run mypy src` |
| **Bandit** | SAST: detecta padroes inseguros no codigo (nao roda em `tests/`). | `uv run bandit -c pyproject.toml -r src` |
| **pip-audit** | Audita dependencias com vulnerabilidades conhecidas (CVEs). | `uv run pip-audit` |
| **gitleaks** | Impede que segredos (chaves/tokens) vazem em commit (via pre-commit). | roda automaticamente no commit; instalado como hook |
| **import-linter** | Garante a direcao de dependencia entre camadas (ports & adapters). | `uv run lint-imports` |
| **Radon / Xenon** | Metricas de complexidade; Xenon falha o build acima do limite configurado. | `uv run radon cc src -a` / `uv run xenon --max-absolute B src` |
| **pytest** (+ **pytest-cov**) | Testes unitarios com relatorio de cobertura. | `uv run pytest --cov=<pacote>` |
| **Hypothesis** | Property-based testing (gera entradas para exercitar propriedades). | usado dentro dos testes pytest |
| **pre-commit** | Orquestra todos os hooks acima antes de cada commit. | `uv run pre-commit install` (uma vez); `uv run pre-commit run --all-files` |
| **commitizen** | Valida Conventional Commits e automatiza bump SemVer + CHANGELOG. | `uv run cz commit` (commit guiado); `uv run cz bump` (release) |

### Instalar os hooks (uma vez por clone)

```bash
uv run pre-commit install                       # hooks de pre-commit
uv run pre-commit install --hook-type commit-msg # valida a mensagem (commitizen)
```

O detalhamento de cada ferramenta, o mapeamento com clean code/SOLID, a
justificativa do gate local e a disciplina de versionamento (Conventional
Commits + SemVer + Keep a Changelog) estao na skill
`.kiro/skills/agno-code-quality-tools/SKILL.md` (fonte de verdade).

---

## 3. Fluxo de commit (`commit_flow.py`)

Fluxo de versionamento simplificado com responsabilidades separadas:

- O **conteudo** (mensagem de commit em Conventional Commits, entrada de
  CHANGELOG, calculo de SemVer e descricao de PR) e redigido por fora e salvo em
  **um arquivo por commit** dentro de `commits/`, nomeado `<N>-<nome>.md` (a
  pasta e ignorada pelo git, exceto `_TEMPLATE.md` e `.gitkeep`).
- O **script apenas executa** o fluxo git a partir desse arquivo. Por padrao:
  `git add` -> `commit` -> `push` explicito -> remove o arquivo consumido. O PR
  e **opt-in** via `--pr` (nunca abre sozinho, mesmo com a secao `PR` presente).

### Como usar (comando minimalista)

Rode a partir da **raiz do workspace** (onde vive o `.git`). O comando `commit`
e um entry point declarado no `pyproject.toml` da raiz; `uv` cuida do ambiente
(o dev-tooling nao tem dependencias):

```bash
# Padrao: add + commit + push (SEM PR). SEM argumento => arquivo de MAIOR numero.
uv run commit

# Igual ao anterior, e ALEM disso abre o PR (usa a secao PR do arquivo).
uv run commit --pr

# Escolher um arquivo especifico (nome com ou sem .md, ou um caminho).
uv run commit 3-fix-parser

# Ver o que faria, sem tocar no repo.
uv run commit --dry-run

# Sem confirmacao interativa.
uv run commit --yes

# So commit, sem push (preserva o arquivo de commit).
uv run commit --no-push

# Nao remover o arquivo de commit ao concluir.
uv run commit --keep

# Trocar a branch base do PR (default: main).
uv run commit --base develop
```

> Alternativa equivalente (sem o entry point): `uv run --script
> scripts/commit_flow.py [arquivo] [opcoes]`.

### Selecao automatica do arquivo

Nomeie os arquivos `<N>-<nome>.md` (`0-setup.md`, `1-fix.md`, ...). Sem
argumento, o script escolhe SEMPRE o de maior `N`. Ao concluir com sucesso, o
arquivo e removido (use `--keep` para preserva-lo).

### Formato do arquivo de commit

Copie `commits/_TEMPLATE.md`. Secoes delimitadas por `>>> NOME` ... `<<<`:

| Secao | Obrigatoria | Uso |
| --- | --- | --- |
| `COMMIT` | sim | Mensagem completa (titulo + corpo), em Conventional Commits. |
| `FILES` | nao | Um caminho por linha (`git add`). Vazia/ausente => `git add -A`. |
| `CHANGELOG` | nao | Texto de referencia; **nao** e aplicado automaticamente. |
| `PR` | nao | Titulo (1a linha) + descricao. Usada apenas quando voce passa `--pr`. |

### Comportamento e garantias

- **Fail-fast:** valida `git`, o repo e o arquivo ANTES de qualquer mudanca.
- **Push explicito:** sempre `git push -u origin <branch-atual>` — nunca push
  "pelado". Recusa commit/push direto em `main`/`master`.
- **PR (opt-in `--pr`):** so abre PR quando voce passa `--pr` (e exige a secao
  `PR` no arquivo). Usa `gh pr create` se o `gh` estiver instalado; caso
  contrario, faz o push e imprime a URL de *compare* do GitHub (`base...branch`)
  com o titulo pronto, alem do titulo/descricao para colar.
- Nada staizado => erro claro (evita commit vazio silencioso).
- **Limpeza:** o arquivo de commit e consumido (removido) ao concluir com
  sucesso; `--no-push` e `--keep` preservam o arquivo.

## Comandos uteis

```bash
uv run ruff check . --fix && uv run ruff format .
uv run mypy src
uv run bandit -c pyproject.toml -r src
uv run pip-audit
uv run lint-imports
uv run pytest -m 'not e2e and not system and not integration' --cov=<pacote>
```
