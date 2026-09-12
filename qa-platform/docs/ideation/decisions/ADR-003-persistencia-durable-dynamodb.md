# ADR-003 — Persistência durável do estado de run: DynamoDB (+ fallback in-memory)

- **Status:** Aceita (feature `durable-run-state-store`)
- **Data:** 2026-09-11
- **Contexto do projeto:** QA Platform (`qa-platform/PROJECT.md`, seções 8 e 10; ADR-001)
- **Decisores:** autor (Product Owner / Tech Lead), Kiro (assistente)

## Contexto

O esqueleto do orquestrador entregou o port `RunStateStore` (domínio) e um adapter
**in-memory** que satisfaz o contrato, mas perde tudo quando o processo encerra. O
`PROJECT.md` (seções 8 e 10) exige **histórico de runs** — logo, é preciso um adapter
**durável** que sobreviva ao reinício do processo.

O ADR-001 já decidiu que o `RunResult` é a **fonte de verdade** do histórico e que o
domínio não depende de framework (o `db=` da Agno não é usado como histórico oficial).
Falta decidir **qual armazenamento durável** realiza o port, sem violar essa fronteira.

## Decisão

Adotar **DynamoDB** como backend durável do `RunStateStore`, mantendo o **in-memory** como
fallback local. A seleção é feita por variável de ambiente (`RUN_STORE_BACKEND`, default
`in_memory`), com **fail-fast** quando o backend durável é pedido sem os parâmetros
obrigatórios (ex.: nome da tabela). O `RunResult` é persistido como **um item por run**,
com **escrita condicional** (`attribute_not_exists`) para a semântica de conflito do port.

Princípio-guia (coerente com o ADR-001): **o domínio define o contrato; a infraestrutura o
realiza.** O port `RunStateStore` **não** muda; o adapter, o model de registro (Pydantic)
e o serializer vivem na infraestrutura, sem vazar tipos para o domínio.

## Justificativa

- **Serverless e alinhado à stack:** o bootstrap já usa AWS (Secrets Manager, deploy SAM);
  DynamoDB é serverless (escala a zero, sem gestão de conexão) e coerente com Lambda.
- **Já disponível localmente:** o LocalStack **núcleo** do `docker-compose` já habilita
  `dynamodb` (sobe sem perfil), então o desenvolvimento local com o backend durável não
  exige serviço extra.
- **Semântica de conflito nativa:** a escrita condicional do DynamoDB
  (`attribute_not_exists`) implementa diretamente o "não sobrescrever + sinalizar
  conflito" exigido pelo port, inclusive sob concorrência.
- **Fronteiras limpas:** o SDK (`boto3`) fica confinado ao adapter (import tardio), e o
  domínio permanece puro — verificado por import-linter.
- **Persistência como fronteira externa:** o registro persistido é modelado com Pydantic
  `BaseModel` na infraestrutura (validação/serialização na borda), conforme a steering de
  organização de dataclasses (`12-organizacao-dataclasses`).

## Alternativas consideradas

1. **SQLite (rejeitada).** Simples e local, porém não serverless e **não persiste entre
   invocações Lambda** (arquivo local efêmero no ambiente de execução). Conflita com o
   deploy serverless do projeto.
2. **Postgres / pgvector (rejeitada nesta fase).** Já existe no `docker-compose`, mas
   atrás de um **perfil opt-in** e voltado a RAG; exige gestão de conexão e esquema
   relacional, sem ganho frente ao DynamoDB para um armazenamento chave-valor por `run_id`.
3. **`db=` da Agno (rejeitada).** Delegaria o histórico ao esquema interno da Agno,
   ferindo a independência do domínio decidida no ADR-001 e amarrando o histórico ao
   framework.

## Consequências

- Positivas: histórico durável serverless, disponível local sem serviço extra; conflito
  garantido por escrita condicional; domínio intacto; evolução de formato via
  `schema_version`.
- Negativas / trade-offs: modelo chave-valor por `run_id` — **consultas de listagem/
  histórico** (paginação, ordenação por data) exigem um índice (GSI) ou varredura
  paginada, tratadas em **spec futura** (fora do escopo enxuto atual). A provisão da tabela
  passa a ser responsabilidade de infraestrutura (SAM + init do LocalStack).

## Referências

- `qa-platform/PROJECT.md` (seções 8 e 10 — histórico de runs).
- `ADR-001-orquestracao-workflow-first.md` (RunResult como fonte de verdade; domínio
  independente de framework).
- `.kiro/specs/durable-run-state-store/{requirements,design,tasks}.md`.
- Steering `12-organizacao-dataclasses` (model de persistência em `infrastructure/`,
  Pydantic na fronteira externa) e `03-sam-python` (padrão DynamoDB, testes com `moto`).
- Adapter de referência `infrastructure/secrets/aws_secrets_manager.py` (import tardio de
  `boto3`, endpoint por env, sem vazar segredos).
