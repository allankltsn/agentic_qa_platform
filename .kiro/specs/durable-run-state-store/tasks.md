# Implementation Plan: Durable Run State Store (Plano de Implementação)

## Overview

Este plano converte o design da **persistência durável do resultado de run** (escopo
enxuto) em tarefas de código incrementais e test-first. Cada tarefa constrói sobre a
anterior e termina com a integração (factory + composition_root + IaC), sem código órfão.
O escopo é um adapter **durável** do `RunStateStore` sobre **DynamoDB** (ADR-003), com
model de registro em **Pydantic `BaseModel`**, serializer isolado, seleção por env e
provisionamento da tabela — **sem alterar** o port de domínio.

Fora de escopo (specs futuras): listagem consultável de histórico e persistência durável
do estado intermediário (`start`/`record_failure` são implementados como no-op durável,
mantendo o contrato).

A feature **estende** o pacote `qa_platform` (em `code/`) e reusa: o port `RunStateStore`,
os VOs `RunResult`/`RunState`/`RunId`, os erros `RunIdConflictError`/`RunNotFoundError`, o
padrão do adapter `AWSSecretsManagerProvider` (import tardio de `boto3`, endpoint por env),
o import-linter e o Hypothesis. Todos os caminhos são relativos a `code/`.

A abordagem segue de dentro para fora (domain → infrastructure → wiring → IaC). Linguagem
**Python**, gerenciada por **uv** com versões fixas. Rodar os comandos pelo interpretador
do `.venv` do projeto (`code/.venv/Scripts/python.exe -m pytest`).

Convenções:
- Tarefas com `*` são de teste e podem ser puladas para um MVP mais rápido; as de
  implementação de núcleo nunca são opcionais.
- Testes de propriedade usam **Hypothesis** (mín. 100 iterações, uma propriedade por
  teste), com a tag `# Feature: durable-run-state-store, Property {n}`.
- Testes de DynamoDB usam **`moto`** (simulação em memória, sem rede).
- Cada tarefa referencia os requisitos que satisfaz e, quando aplicável, a propriedade.

## Tasks

- [x] 1. Preparar dependências e erros de domínio
  - [x] 1.1 Adicionar `moto` ao dev group (versão fixa) e atualizar o lock
    - Estender `code/pyproject.toml` (dependency-group `dev`) com `moto` em versão fixa;
      atualizar/versionar o `code/uv.lock`. Não alterar dependências de runtime existentes.
    - _Requirements: (suporte a testes) 1.1, 2.1_
  - [x] 1.2 Estender os erros de domínio de storage/serialização
    - Estender `code/src/qa_platform/domain/exceptions.py` com `RunStorageError`
      (operação + run_id + motivo, sem segredo) e `RunRecordSerializationError`
      (run_id + motivo), ambos sob `OrchestrationDomainError`. Puros.
    - _Requirements: 7.2, 7.3, 3.4, 3.5_

- [x] 1b. Adicionar a identidade do alvo ao RunResult (domínio + application + workflow)
  - [x] 1b.1 `RunResult` ganha `target_ref` + `target_version` obrigatórios
    - Estender `code/src/qa_platform/domain/entities/run_result.py`: adicionar os campos
      `target_ref` e `target_version` ao `RunResult`, com `__post_init__` rejeitando
      valor ausente/vazio (laudo órfão) (Req 8.1, 8.5). VO permanece puro.
    - _Requirements: 8.1, 8.5_
  - [x] 1b.2 `consolidate` passa a receber o manifest e preencher o alvo
    - Alterar `code/src/qa_platform/application/evidence_consolidator.py`: assinatura
      `consolidate(run_id, manifest, plan, evidences)`; preenche `target_ref`/
      `target_version` do `QATargetManifest` (Req 8.2, 8.3). Sem LLM/rede.
    - _Requirements: 8.2, 8.3_
  - [x] 1b.3 Ajustar o `workflow.py` para repassar o manifest ao consolidar
    - Em `code/src/qa_platform/infrastructure/orchestration/workflow.py`, o step de
      consolidação chama `consolidate(run_id, manifest, plan, evidences)` (o `manifest`
      já está disponível por closure). Sem outra mudança de fluxo.
    - _Requirements: 8.2_
  - [x] 1b.4 Atualizar os testes existentes afetados pela nova assinatura/campos
    - Ajustar os testes que constroem `RunResult`/chamam `consolidate` na feature
      `workflow-orchestrator-skeleton` (ex.: `test_evidence_consolidator.py`,
      `test_advisory_judge.py`, `test_workflow.py`, `test_run_result.py`) para incluir
      `target_ref`/`target_version`; garantir a suíte verde após a mudança de domínio.
    - _Requirements: 8.1, 8.2_

- [x] 2. Implementar o RunRecordModel (Pydantic) e o RunRecordSerializer (infra)
  - [x] 2.1 Implementar o `RunRecordModel` (Pydantic BaseModel) com `schema_version`
    - Criar `code/src/qa_platform/infrastructure/persistence/run_record_model.py`: os
      models Pydantic do registro (`RunRecordModel` + records aninhados de plano,
      evidência, achado, trabalho pulado), com `run_id`, `target_ref`, `target_version`,
      `schema_version` e `created_at`. Sem `boto3`. Segue a steering
      `12-organizacao-dataclasses` (persistência = fronteira externa → Pydantic na infra;
      domínio permanece `@dataclass` puro).
    - _Requirements: 3.1, 3.5, 6.1, 8.4_
  - [x] 2.2 Implementar `to_item`/`from_item` (round-trip domínio ↔ model)
    - Criar `code/src/qa_platform/infrastructure/persistence/run_record_serializer.py`:
      converte `RunResult` ↔ `RunRecordModel`/dict, serializando severity pelo nome do
      enum e reconstruindo as coleções aninhadas com ordem/identidade preservadas; item
      malformado (ValidationError) ou `schema_version` não suportado →
      `RunRecordSerializationError` nomeando run_id + motivo. Sem `boto3`.
    - _Requirements: 3.2, 3.3, 3.4, 3.5_
  - [x] 2.3 Escrever teste de propriedade do round-trip do serializer (Property 1)
    - `code/tests/infrastructure/persistence/test_run_record_serializer.py`
    - **Property 1: round-trip sem perda** — `from_item(to_item(...)) == RunResult`
      original, incluindo `target_ref`/`target_version` e as coleções aninhadas. Gerador
      de `RunResult` variados (com identidade de alvo). Comentário
      `# Feature: durable-run-state-store, Property 1`.
    - **Validates: Requirements 3.2, 3.3, 8.4; Property 1**
  - [x] 2.4 Escrever teste por exemplo do schema incompatível (Property 4)
    - No mesmo arquivo: item com `schema_version` ausente/desconhecido ou malformado →
      `RunRecordSerializationError` nomeando run_id + motivo, sem `RunResult` parcial.
    - **Validates: Requirements 3.4, 3.5; Property 4**

- [x] 3. Implementar o DynamoDBRunStateStore (adapter durável)
  - [x] 3.1 Implementar `save_result`/`get` com escrita condicional e timeouts
    - Criar `code/src/qa_platform/infrastructure/persistence/dynamodb_run_store.py`:
      implementa o `RunStateStore`; `import boto3`/`botocore.Config` **tardio** no ponto
      de uso, com timeouts explícitos (connect/read) e retries; `save_result` usa
      `ConditionExpression=attribute_not_exists(run_id)` → `RunIdConflictError` em
      conflito (Req 2.1, 2.4); `get` ausente → `RunNotFoundError` (Req 2.2); run_id
      inválido → erro de id inválido (Req 2.3); erro de infra → `RunStorageError`
      nomeando operação + run_id, distinto de conflito/ausência (Req 7.2, 7.3). Chave de
      partição = `run_id`.
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 6.4, 7.1, 7.2, 7.3_
  - [x] 3.2 Implementar `start`/`record_failure` como no-op durável (compatível com o port)
    - No mesmo adapter: `start` e `record_failure` validam o `run_id` e retornam sem
      persistir estado intermediário (fora de escopo nesta fase), mantendo o contrato do
      port sem quebrar o orquestrador.
    - _Requirements: 1.3_
  - [x] 3.3 Escrever teste de propriedade do round-trip persistir→recuperar (Property 2)
    - `code/tests/infrastructure/persistence/test_dynamodb_run_store.py` com `moto`
      (`@mock_aws`): cria a tabela, `save_result` → `get` retorna `RunResult` igual.
      Comentário `# Feature: durable-run-state-store, Property 2`.
    - **Validates: Requirements 1.1, 1.2; Property 2**
  - [x] 3.4 Escrever testes por exemplo do adapter (conflito, ausência, storage-error, run_id inválido)
    - No mesmo arquivo (`moto`): segundo `save_result` mesmo id → `RunIdConflictError` e
      `get` mantém o original (Property 3; Req 2.1/2.4); `get` de id nunca salvo →
      `RunNotFoundError` (Req 2.2); erro de infra simulado (ex.: tabela inexistente) →
      `RunStorageError` distinto de conflito/ausência (Req 7.2, 7.3); run_id vazio →
      erro de id inválido (Req 2.3).
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 7.2, 7.3; Property 3**

- [x] 4. Implementar a RunStoreFactory (seleção por env)
  - [x] 4.1 Implementar `build_run_store` com fail-fast
    - Criar `code/src/qa_platform/infrastructure/persistence/run_store_factory.py`:
      seleciona por `RUN_STORE_BACKEND` (default `in_memory`); backend `dynamodb` sem
      `RUN_TABLE_NAME` → `RunStoreConfigError` nomeando o parâmetro, sem cair no
      in-memory (Req 4.3); retorna sempre um `RunStateStore` (port). Import do adapter
      durável só quando selecionado (mantém importabilidade sem boto3).
    - _Requirements: 4.1, 4.2, 4.3, 6.4_
  - [x] 4.2 Escrever testes da factory (seleção + fail-fast)
    - `code/tests/infrastructure/persistence/test_run_store_factory.py`: default →
      in-memory; `dynamodb` + `RUN_TABLE_NAME` → adapter durável; `dynamodb` sem tabela →
      `RunStoreConfigError` nomeando o parâmetro (não cai no in-memory).
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 5. Integrar no composition_root e nas fronteiras
  - [x] 5.1 Cabear a factory no composition_root
    - Estender `code/src/qa_platform/composition_root.py`: `build_orchestrator_runner`
      usa `build_run_store()` em vez de instanciar `InMemoryRunStateStore` diretamente,
      consumindo o resultado apenas pelo port (Req 4.4).
    - _Requirements: 4.4_
  - [x] 5.2 Estender o import-linter (boto3 confinado ao novo adapter)
    - Estender `code/importlinter.ini`: adicionar
      `qa_platform.infrastructure.persistence.dynamodb_run_store` como origem autorizada
      a importar `boto3`, mantendo `domain`/`interface` proibidos (Req 6.2, 6.3).
    - _Requirements: 6.1, 6.2, 6.3_
  - [x] 5.3 Atualizar o `.env.example`
    - Estender `code/.env.example` com `RUN_STORE_BACKEND` (default `in_memory`),
      `RUN_TABLE_NAME` (obrigatória quando backend=`dynamodb`) e nota sobre reuso de
      `AWS_ENDPOINT_URL`/`AWS_REGION`.
    - _Requirements: 4.2_

- [x] 6. Provisionar a tabela como código (SAM + LocalStack)
  - [x] 6.1 Declarar a tabela DynamoDB no SAM com menor privilégio
    - Estender `code/template.yaml`: recurso `AWS::DynamoDB::Table` (PK `run_id` (S),
      `BillingMode=PAY_PER_REQUEST`, `SSESpecification` habilitado); passar o nome da
      tabela ao serviço por env (`RUN_TABLE_NAME`) e conceder à função uma policy de
      menor privilégio (apenas `GetItem`/`PutItem` na tabela) (Req 5.1, 5.3).
    - _Requirements: 5.1, 5.3_
  - [x] 6.2 Criar a tabela no LocalStack (init idempotente)
    - Criar `code/localstack/init/02-create-run-table.sh`: cria a mesma tabela de forma
      idempotente quando o LocalStack fica pronto, no padrão do script de bootstrap
      existente (Req 5.2).
    - _Requirements: 5.2_
  - [x] 6.3 Validar a infraestrutura
    - `sam validate` (ou `sam build`) sem erros de template; `docker compose config`
      válido. Confirma que a tabela é declarada e o env é exposto.
    - _Requirements: 5.1, 5.2_

- [x] 7. Checkpoint final - Suíte + fronteiras verdes
  - Rodar toda a suíte (`pytest`) pelo `.venv` (incluindo Properties 1–4 e os testes
    `moto`) e o import-linter (via `code/importlinter.ini`), garantindo todos verdes e o
    `boto3` confinado. Atualizar o `code/CHANGELOG.md` (seção [Unreleased]). Se surgirem
    dúvidas, pergunte ao usuário.

## Notes

- Tarefas com `*` são opcionais (testes) e podem ser puladas para um MVP mais rápido; as
  de implementação de núcleo nunca são opcionais.
- O port `RunStateStore` **não** é alterado; esta feature só adiciona adapters, model,
  serializer e a factory. O `RunResult` permanece a fonte de verdade do histórico (sem
  `db=` da Agno).
- O model de registro é Pydantic `BaseModel` em
  `code/src/qa_platform/infrastructure/persistence/` (fronteira externa; steering
  `12-organizacao-dataclasses`). O domínio permanece `@dataclass` puro.
- `moto` simula DynamoDB em memória (sem rede), no padrão do steering `03-sam-python`.
- Rodar pelo interpretador do `.venv` do projeto; os wrappers `.exe`/`uv run` podem falhar
  com "trampoline" neste ambiente.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1b.1", "1b.2", "1b.3"] },
    { "id": 2, "tasks": ["1b.4", "2.1"] },
    { "id": 3, "tasks": ["2.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "3.1"] },
    { "id": 5, "tasks": ["3.2", "3.3", "3.4", "4.1"] },
    { "id": 6, "tasks": ["4.2", "5.1", "5.2", "5.3", "6.1", "6.2"] },
    { "id": 7, "tasks": ["6.3", "7"] }
  ]
}
```
