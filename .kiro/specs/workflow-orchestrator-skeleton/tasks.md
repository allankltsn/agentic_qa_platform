# Implementation Plan: Workflow Orchestrator Skeleton (Plano de Implementação)

## Overview

Este plano converte o design do **esqueleto do orquestrador Workflow-first** em uma
série de tarefas de código incrementais e test-first. Cada tarefa constrói sobre as
anteriores e termina com a integração das partes (composition_root + Orchestrator_Workflow),
sem código órfão. O escopo é o **núcleo de orquestração** determinístico do ADR-001:
fluxo raiz em ordem definida, primitivos de controle (roteamento, concorrência,
condição de custo), Executor_Functions puros, o contrato de camada de QA (port), uma
camada de IA mínima/stub, o schema do `qa-target.yaml` e o contrato de persistência de
run (adapter in-memory nesta fase).

Esta feature **estende** o pacote existente `code/src/qa_platform/` e **reusa** a
infraestrutura do bootstrap (SecretResolver/config, observabilidade, segurança de borda,
import-linter, Hypothesis). Nenhum artefato do bootstrap é recriado — apenas adicionamos
os arquivos novos indicados na estrutura de diretórios do design e estendemos os pontos
existentes (`domain/exceptions.py`, `composition_root.py`, `importlinter.ini`).

A abordagem segue as camadas de dentro para fora (domain → application →
infrastructure) e, ao final, monta o `Workflow` da Agno e o wiring no composition_root.
A linguagem é **Python** (definida no design), gerenciada por **uv** com versões fixas.

Princípio-guia (ADR-001): **determinístico por fora (o `Workflow` orquestra passos em
ordem definida), inteligente por dentro (Agents/Teams confinados aos passos que exigem
julgamento — não usados nesta fase).**

Convenções:
- Tarefas marcadas com `*` são de teste e podem ser puladas para um MVP mais rápido;
  as tarefas de implementação de núcleo nunca são opcionais.
- Testes de propriedade usam **Hypothesis** (mín. 100 iterações, uma propriedade por
  teste), com a tag de comentário `# Feature: workflow-orchestrator-skeleton, Property {n}`.
- As 15 Correctness Properties do design cobrem a **lógica pura determinística**;
  concorrência real (Parallel_Runner), o `Workflow` da Agno, o parser YAML, as
  fronteiras de arquitetura e os requisitos de "ausência de LLM/rede" ficam em testes
  por exemplo/integração, conforme a Testing Strategy do design.
- Cada tarefa referencia os requisitos que satisfaz e, quando aplicável, a propriedade
  de correção correspondente.

## Tasks

- [x] 1. Preparar dependências e fronteiras de arquitetura
  - [ ] 1.1 Adicionar dependências uv (Agno v2 + parser YAML) com versões exatas
    - Estender o `code/pyproject.toml` declarando **Agno v2** e a lib de parsing de YAML
      (`ruamel.yaml` ou `pyyaml`) com **versões exatas fixadas**; atualizar/versionar o
      `uv.lock` reproduzível
    - Não alterar as dependências já existentes do bootstrap
    - _Requirements: 12.2_

  - [x] 1.2 Estender o import-linter (confinar Agno + YAML fora do domain/interface)
    - Estender `code/importlinter.ini`: adicionar `agno` e o parser YAML
      (`yaml`/`ruamel`) à lista de módulos proibidos do contrato `domain-puro` e criar um
      contrato confinando `agno` a `qa_platform.infrastructure.orchestration.*` e
      `qa_platform.infrastructure.layers.*` (análogo ao confinamento do `boto3` do
      bootstrap)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 2. Implementar identidades e severidade no domain
  - [x] 2.1 Implementar `LayerId` e `RunId` (value objects puros)
    - Criar `src/qa_platform/domain/ids.py` com os dataclasses frozen `LayerId` e
      `RunId`, rejeitando valor ausente/vazio/whitespace no `__post_init__`
    - Sem qualquer import de framework de orquestração ou infraestrutura
    - _Requirements: 6.1, 7.1, 1.3, 11.6_

  - [x] 2.2 Implementar `Severity` (ordem total para priorização)
    - Criar `src/qa_platform/domain/severity.py` com o `IntEnum` `Severity`
      (`INFO < LOW < MEDIUM < HIGH < CRITICAL`)
    - _Requirements: 10.1_

  - [x]* 2.3 Escrever testes unitários de identidades e severidade
    - `tests/domain/test_ids.py`: `LayerId`/`RunId` rejeitam vazio/whitespace; iguais por
      valor quando o valor é igual
    - `tests/domain/test_severity.py`: ordem total (`CRITICAL` é a maior)
    - _Requirements: 6.1, 11.6, 10.1_

- [x] 3. Implementar os value objects de domínio da orquestração
  - [x] 3.1 Implementar `QATargetManifest` (VO puro)
    - Criar `src/qa_platform/domain/manifest.py` com o VO frozen `QATargetManifest`
      (target ref/version, `applicable_layers`, `risk_parameters`, `cost_parameters`) e
      acessores puros como `cost_parameters_for(layer_id)`
    - Sem tipos de framework nem de parser YAML
    - _Requirements: 6.2, 8.1, 12.1_

  - [x] 3.2 Implementar `ExecutionPlan` e `PlannedLayer` (VOs puros)
    - Criar `src/qa_platform/domain/execution_plan.py` com `PlannedLayer`
      (`layer_id`, `priority`, `reduced_mode`) e `ExecutionPlan` (`layers` como tuple,
      imutável e comparável por valor)
    - _Requirements: 6.5, 12.1, 3.6_

  - [x] 3.3 Implementar `LayerEvidence` e `Finding` (VOs puros, sem veredito)
    - Criar `src/qa_platform/domain/evidence.py` com `Finding` (code, severity, detail)
      e `LayerEvidence` (`layer_id`, `metrics`, `findings`, `reduced_mode`), **sem**
      qualquer campo de veredito pass/fail
    - _Requirements: 6.5, 6.6, 2.4, 12.1_

  - [x] 3.4 Implementar `RunResult`, `RunState` e `SkippedWork` (VOs puros)
    - Criar `src/qa_platform/domain/run_result.py` com `SkippedWork` (layer_id, reason),
      `RunState` (estado da run com `with_failure`) e `RunResult`
      (`run_id`, `plan`, `evidences`, `prioritized`, `skipped`, `failures`)
    - _Requirements: 6.5, 2.4, 4.3, 5.2, 12.1_

  - [x]* 3.5 Escrever testes unitários dos value objects de domínio
    - `tests/domain/test_execution_plan.py`: imutabilidade e igualdade por valor
    - `tests/domain/test_evidence.py`: `LayerEvidence` **não** expõe nenhum
      campo/atributo pass/fail/verdict
    - `tests/domain/test_run_result.py`: agregação preserva campos; `with_failure`
      registra step + causa
    - _Requirements: 6.5, 6.6, 2.4_

- [x] 4. Estender os erros de domínio da orquestração
  - Estender `src/qa_platform/domain/exceptions.py` adicionando
    `OrchestrationDomainError` (base) e `InvalidManifestError`, `UnknownLayerError`,
    `RunIdConflictError`, `RunNotFoundError`, `LayerContractViolation` e
    `TargetResolutionError`, todos puros (nomeiam campos/ids/steps, nunca valores de
    segredo)
  - _Requirements: 2.3, 8.3, 3.3, 8.5, 11.3, 11.5, 6.4, 9.5, 12.1_

- [x] 5. Definir os ports (contratos puros) no domain
  - [x] 5.1 Implementar `QALayerContract` (Protocol)
    - Criar `src/qa_platform/domain/ports/__init__.py` e
      `src/qa_platform/domain/ports/qa_layer.py` com o `Protocol` `runtime_checkable`
      `QALayerContract` (propriedade `layer_id`; `execute(plan, manifest) -> LayerEvidence`)
    - Puro: nenhuma dependência de Agno/ferramentas de avaliação/infraestrutura
    - _Requirements: 6.1, 6.2, 6.3, 12.1_

  - [x] 5.2 Implementar `RunStateStore` (Protocol)
    - Criar `src/qa_platform/domain/ports/run_state_store.py` com o `Protocol`
      `RunStateStore` (`start`, `record_failure`, `save_result`, `get`)
    - _Requirements: 11.1, 12.1_

  - [x]* 5.3 Escrever testes de contrato dos ports
    - `tests/domain/test_ports.py`: os Protocols são `runtime_checkable`; uma
      implementação mínima é reconhecida como conforme
    - _Requirements: 6.1, 11.1_

- [x] 6. Implementar o Risk_Planner (Executor_Function)
  - [x] 6.1 Implementar `plan_by_risk`
    - Criar `src/qa_platform/application/risk_planner.py`: função pura que deriva
      prioridade em `[1,100]` dos parâmetros de risco, ordena de forma estável (por
      prioridade desc, depois `layer_id`) e produz `ExecutionPlan`; rejeita manifest
      inválido/sem risco com `InvalidManifestError` nomeando o campo. Sem LLM, sem rede
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 3.6_

  - [x] 6.2 Escrever teste de propriedade do determinismo do Risk_Planner (Property 1)
    - `tests/application/test_risk_planner.py`
    - **Property 1: Determinismo do Risk_Planner** — planejar duas vezes o mesmo manifest
      produz `ExecutionPlan`s iguais em valor (serialização idêntica)
    - Gerador de manifests válidos (camadas + parâmetros de risco); comentário
      `# Feature: workflow-orchestrator-skeleton, Property 1`
    - **Validates: Requirements 1.2, 2.5, 8.6; Property 1**

  - [x] 6.3 Escrever teste de propriedade de prioridades e cobertura (Property 2)
    - No mesmo arquivo `tests/application/test_risk_planner.py`
    - **Property 2: Prioridades no intervalo válido e cobertura das camadas** — o plano
      contém exatamente as camadas aplicáveis, cada uma com `priority` inteira em `[1,100]`
    - Gerador de manifests válidos com N camadas; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 2`
    - **Validates: Requirements 2.2; Property 2**

  - [x] 6.4 Escrever teste de propriedade da rejeição de manifest inválido (Property 3)
    - No mesmo arquivo `tests/application/test_risk_planner.py`
    - **Property 3: Rejeição de manifest inválido pelo Risk_Planner** — manifest sem/ com
      risco inválido levanta `InvalidManifestError` sem produzir plano, nomeando o campo
    - Gerador de manifests sem risco / com risco inválido; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 3`
    - **Validates: Requirements 2.3; Property 3**

- [x] 7. Implementar o Evidence_Consolidator (Executor_Function)
  - [x] 7.1 Implementar `consolidate`
    - Criar `src/qa_platform/application/evidence_consolidator.py`: agrega as
      `LayerEvidence` num `RunResult` preservando a identidade de origem e sendo
      invariante à ordem de fornecimento (ordena por `layer_id`). Puro
    - _Requirements: 2.1, 2.4, 2.6_

  - [x]* 7.2 Escrever teste de propriedade da consolidação (Property 4)
    - `tests/application/test_evidence_consolidator.py`
    - **Property 4: Consolidação preserva origem e é invariante à ordem** — qualquer
      permutação da ordem de fornecimento produz `RunResult`s iguais em valor, mesma
      contagem e mesmas `layer_id`
    - Gerador de listas de `LayerEvidence` + permutação da ordem; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 4`
    - **Validates: Requirements 2.4, 2.6; Property 4**

- [x] 8. Implementar o Advisory_Judge (determinístico mínimo)
  - [x] 8.1 Implementar `prioritize`
    - Criar `src/qa_platform/application/advisory_judge.py`: ordena as evidências por
      severidade máxima (desc, estável), preserva todas as evidências de origem, não
      emite veredito; `RunResult` sem evidências → priorização vazia sem erro. Sem LLM
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x]* 8.2 Escrever teste de propriedade do Advisory_Judge (Property 12)
    - `tests/application/test_advisory_judge.py`
    - **Property 12: Priorização determinística, por severidade, preservadora e sem
      veredito** — ordena por severidade estável, preserva contagem/identidades, sem
      pass/fail, idêntica em execuções repetidas, vazia quando não há evidências
    - Gerador de `RunResult` com evidências variadas (incl. vazio); comentário
      `# Feature: workflow-orchestrator-skeleton, Property 12`
    - **Validates: Requirements 10.1, 10.2, 10.4, 10.5; Property 12**

- [x] 9. Implementar o Feedback_Dispatcher (Executor_Function)
  - [x] 9.1 Implementar `dispatch` + `FeedbackSink`
    - Criar `src/qa_platform/application/feedback_dispatcher.py` com o `Protocol`
      `FeedbackSink` (`emit(result)`) e a função `dispatch(result, sink)` que apenas
      encaminha ao sink plugável; sem integrações externas reais. Puro em rede/token
    - _Requirements: 2.1_

  - [ ]* 9.2 Escrever teste unitário do Feedback_Dispatcher
    - `tests/application/test_feedback_dispatcher.py`: `dispatch` chama `sink.emit` uma
      vez com o `RunResult`; sink fake in-memory registra o resultado
    - _Requirements: 2.1_

- [x] 10. Checkpoint - Garantir que domain e application passam
  - Garantir que todos os testes de domain e application (VOs, ports, Executor_Functions,
    Properties 1–4 e 12) passam. Se surgirem dúvidas, pergunte ao usuário.

- [x] 11. Implementar o schema, parser e discovery do manifesto (infrastructure)
  - [x] 11.1 Implementar o schema e validador do `QA_Target_Manifest`
    - Criar `schemas/qa-target.schema.json` e
      `src/qa_platform/infrastructure/manifest/schema.py` + `__init__.py`: define campos
      (alvo, camadas aplicáveis, parâmetros de risco), obrigatoriedade, tipo e
      valores/limites; valida agregando **todos** os campos problemáticos e levanta
      `InvalidManifestError` nomeando cada um com o motivo
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 11.2 Implementar o `Manifest_Parser` (qa-target.yaml → VO)
    - Criar `src/qa_platform/infrastructure/manifest/parser.py` e
      `examples/qa-target.example.yaml`: lê o YAML e produz o `QATargetManifest` puro; o
      tipo do parser YAML não vaza para fora da infra
    - _Requirements: 8.1, 8.2, 12.1_

  - [x] 11.3 Implementar o `Target_Discovery` (mínimo/determinístico)
    - Criar `src/qa_platform/infrastructure/manifest/target_discovery.py`: produz um
      rascunho de manifest conforme o schema marcando campos obrigatórios não derivados
      como **pendentes**; determinístico, sem LLM/rede; referência irresolvível →
      `TargetResolutionError` nomeando a referência
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x]* 11.4 Escrever teste de propriedade da validação de schema (Property 9)
    - `tests/infrastructure/manifest/test_schema.py`
    - **Property 9: Validação de schema nomeia todos os campos inválidos** — manifest com
      subconjunto não-vazio de campos ausentes/tipo inválido/valor fora dos limites é
      rejeitado nomeando **cada** campo problemático com o motivo
    - Gerador de manifests com subconjunto de campos inválidos; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 9`
    - **Validates: Requirements 8.3; Property 9**

  - [x]* 11.5 Escrever teste de propriedade do determinismo do Target_Discovery (Property 11)
    - `tests/infrastructure/manifest/test_target_discovery.py`
    - **Property 11: Determinismo do Target_Discovery** — a mesma referência resolvível
      produz o mesmo rascunho (iguais em valor), conforme o schema; inclui exemplos de
      pendência e de referência irresolvível → erro
    - Gerador de referências de alvo resolvíveis; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 11`
    - **Validates: Requirements 9.4; Property 11**

  - [x]* 11.6 Escrever teste por exemplo do parser (round-trip)
    - `tests/infrastructure/manifest/test_parser.py`: `qa-target.example.yaml` faz parse
      para o VO; round-trip parse→VO estável sobre exemplos fixos
    - _Requirements: 8.1, 8.2_

- [x] 12. Implementar o LayerRegistry e o AI_Layer_Stub (infrastructure)
  - [x] 12.1 Implementar o `LayerRegistry`
    - Criar `src/qa_platform/infrastructure/orchestration/registry.py` + o `__init__.py`
      do pacote `orchestration`: mapeia `LayerId → QA_Layer`; expõe `is_registered`,
      `get` e valida ids do manifest contra as identidades registradas nomeando cada id
      não correspondido (`UnknownLayerError`)
    - _Requirements: 3.5, 8.4, 8.5_

  - [x] 12.2 Implementar o `AILayerStub`
    - Criar `src/qa_platform/infrastructure/layers/__init__.py` e
      `src/qa_platform/infrastructure/layers/ai_layer_stub.py`: implementa o
      `QALayerContract` com identidade única/imutável; retorna `LayerEvidence`
      determinística derivada do plano/manifest sem chamar ferramentas externas;
      entrada inválida/falha interna → erro sem evidência; provider resolvido por env
      (reusa `SecretResolver`/config do bootstrap, `MODEL_PROVIDER`, fail-fast). Tipos de
      framework de agentes confinados aqui
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 12.5, 12.6_

  - [x]* 12.3 Escrever teste de propriedade do determinismo da AI_Layer_Stub (Property 8)
    - `tests/infrastructure/layers/test_ai_layer_stub.py`
    - **Property 8: Determinismo da AI_Layer_Stub** — o mesmo `(plan, manifest)` produz
      `LayerEvidence` com campos iguais em valor
    - Gerador de pares `(plan, manifest)` válidos; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 8`
    - **Validates: Requirements 7.4; Property 8**

  - [x]* 12.4 Escrever testes por exemplo da AI_Layer_Stub e do registry
    - No `tests/infrastructure/layers/test_ai_layer_stub.py`: evidência contém identidade
      + referência ao plano, sem ferramentas externas (7.2); entrada malformada → erro
      sem evidência (7.5); falha interna → erro sem evidência parcial (7.6);
      `MODEL_PROVIDER` ausente → fail-fast nomeando a env (12.6)
    - `tests/infrastructure/manifest/test_registry_match.py`
    - **Property 10: Correspondência de ids nomeia cada id não correspondido** — manifest
      com subconjunto não-vazio de ids desconhecidos encerra com `UnknownLayerError`
      nomeando **cada** id, sem executar camadas; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 10`
    - Teste de extensibilidade: registrar uma `QA_Layer` de teste nova torna-a elegível
      sem alterar Executor_Functions/Workflow (3.5)
    - **Validates: Requirements 7.2, 7.5, 7.6, 12.6, 8.5, 3.5; Property 10**

- [x] 13. Implementar os primitivos de orquestração (Router, Cost_Condition, Parallel)
  - [x] 13.1 Implementar o `Layer_Router` (seleção determinística + Agno Router)
    - Criar `src/qa_platform/infrastructure/orchestration/router.py` com `select_layers`
      (seleção exata do plano, dedupe, ordem estável, plano vazio → vazio, camada não
      registrada → `UnknownLayerError` sem selecionar nada) e `build_router` (mapeia a
      seleção para o `Router` da Agno). Sem LLM. Tipos da Agno confinados aqui
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7, 3.8_

  - [x] 13.2 Implementar o `Cost_Condition` (decisão determinística + Agno Condition)
    - Criar `src/qa_platform/infrastructure/orchestration/cost_condition.py` com
      `should_skip_expensive(manifest, layer_id) -> (skip, motivo)`: decide só com base
      no manifest; ausência de parâmetros → pular com motivo não-vazio. Sem LLM/fonte
      externa
    - _Requirements: 5.1, 5.3, 5.4, 5.5_

  - [x] 13.3 Implementar o `Parallel_Runner` (Agno Parallel, máx 8, timeout 300s)
    - Criar `src/qa_platform/infrastructure/orchestration/parallel.py` com `run_layers`:
      executa camadas concorrentemente (limite 8), coleta todas as evidências antes de
      retornar, trata erro/timeout (300s) por camada nomeando a afetada e retornando o
      parcial
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x]* 13.4 Escrever teste de propriedade da seleção do Layer_Router (Property 5)
    - `tests/infrastructure/orchestration/test_router.py`
    - **Property 5: Seleção exata, deduplicada, ordenada e determinística** — plano com
      refs registradas seleciona exatamente o conjunto, cada camada uma vez, ordem
      estável a cada invocação; plano vazio → seleção vazia
    - Gerador de planos com refs registradas (incl. vazio e duplicadas); comentário
      `# Feature: workflow-orchestrator-skeleton, Property 5`
    - **Validates: Requirements 3.1, 3.2, 3.6, 3.7, 3.8; Property 5**

  - [x]* 13.5 Escrever teste de propriedade do erro do Layer_Router (Property 6)
    - No mesmo arquivo `tests/infrastructure/orchestration/test_router.py`
    - **Property 6: Erro para camada não registrada** — plano com ≥1 ref não registrada
      levanta `UnknownLayerError` nomeando cada não registrada, sem selecionar nada,
      registry inalterado
    - Gerador de planos com ≥1 ref não registrada; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 6`
    - **Validates: Requirements 3.3; Property 6**

  - [x]* 13.6 Escrever teste de propriedade da Cost_Condition (Property 7)
    - `tests/infrastructure/orchestration/test_cost_condition.py`
    - **Property 7: Decisão determinística baseada só no manifest** — parâmetros idênticos
      produzem a mesma decisão `(skip, motivo)`; sem justificativa ou sem parâmetros →
      pular com motivo não-vazio
    - Gerador de manifests com/sem parâmetros de custo; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 7`
    - **Validates: Requirements 5.1, 5.4, 5.5; Property 7**

  - [x]* 13.7 Escrever teste de integração do Parallel_Runner (concorrência real)
    - `tests/infrastructure/orchestration/test_parallel.py`: camadas fake registram
      concorrência e respeitam o limite de 8 (4.1); todas as evidências coletadas antes
      do retorno (4.2); camada que falha é nomeada e as demais concluem (4.3); camada
      lenta com clock/timeout controlado → timeout nomeado (4.4)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 14. Implementar o InMemoryRunStateStore (infrastructure)
  - [x] 14.1 Implementar `InMemoryRunStateStore`
    - Criar `src/qa_platform/infrastructure/persistence/__init__.py` e
      `in_memory_run_store.py`: implementa `RunStateStore` (`start`, `record_failure`,
      `save_result` com conflito, `get` com ausência) sem persistência externa
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [x]* 14.2 Escrever teste de propriedade do round-trip do store (Property 13)
    - `tests/infrastructure/persistence/test_in_memory_run_store.py`
    - **Property 13: Round-trip persistir → recuperar** — após `save_result(run_id, r)`,
      `get(run_id)` retorna `RunResult` igual em valor
    - Gerador de `(RunId, RunResult)`; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 13`
    - **Validates: Requirements 11.2, 11.4, 11.7; Property 13**

  - [x]* 14.3 Escrever teste de propriedade do conflito de Run_Id (Property 14)
    - No mesmo arquivo `test_in_memory_run_store.py`
    - **Property 14: Run_Id duplicado não sobrescreve e sinaliza conflito** — segundo
      `save_result` com o mesmo id levanta `RunIdConflictError`; `get` posterior retorna
      o resultado original inalterado
    - Gerador de `RunId` + dois `RunResult` distintos; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 14`
    - **Validates: Requirements 11.3; Property 14**

  - [x]* 14.4 Escrever teste de propriedade da ausência de Run_Id (Property 15)
    - No mesmo arquivo `test_in_memory_run_store.py`
    - **Property 15: Run_Id inexistente sinaliza ausência** — `get(run_id)` de id nunca
      persistido levanta `RunNotFoundError` nomeando o id, sem retornar outro resultado
    - Gerador de `RunId` nunca persistido; comentário
      `# Feature: workflow-orchestrator-skeleton, Property 15`
    - **Validates: Requirements 11.5; Property 15**

- [x] 15. Checkpoint - Garantir que a infraestrutura passa
  - Garantir que os componentes de infraestrutura (manifest, registry, stub, primitivos
    de orquestração, persistência) e os testes associados (Properties 5–11, 13–15 e
    integração do Parallel_Runner) passam. Se surgirem dúvidas, pergunte ao usuário.

- [x] 16. Implementar e integrar o Orchestrator_Workflow (Agno Workflow)
  - [ ] 16.1 Implementar `build_orchestrator` **(PARCIAL — requer reescrita, ver 16.4)**
    - Criado `src/qa_platform/infrastructure/orchestration/workflow.py`, porém a
      implementação atual **não executa pela engine da Agno**: os 7 `Step` usam um
      executor `_noop` (repassam o conteúdo anterior) e a orquestração real é um runner
      sequencial Python (`run_orchestration`) que roda ao lado do `Workflow` decorativo.
      Isso diverge do ADR-001/da seção 10 do design (engine real). Mantém-se o controle
      de `Run_Id`/`store` e o isolamento de falha corretos, mas o núcleo precisa ser
      reescrito na tarefa 16.4.
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 6.3, 6.4, 8.2, 11.2_

  - [x] 16.4 Reescrever `build_orchestrator`/`run_orchestration` para executar pela engine da Agno
    - Reescrever `src/qa_platform/infrastructure/orchestration/workflow.py` conforme a
      seção 10 revisada do design: `Step`s com **executores reais** (não `_noop`) que
      chamam `plan_by_risk`, o executor único de camadas (`_run_layers` → `select_layers`
      + `should_skip_expensive` + `run_layers`, caminho B do ADR-002), `consolidate`,
      `prioritize` e `dispatch`, trafegando VOs de domínio via `StepOutput.content`; a
      **engine da Agno conduz a ordem**. O `manifest` é fixado por closure. `run_orchestration`
      vira um wrapper fino que valida o manifest antes do 1º step (8.2), atribui `Run_Id`
      e chama `store.start` (aborta sem steps se falhar — 1.3/1.4), aciona `workflow.run`,
      isola falha de step com `record_failure` (1.5) e persiste com `save_result` (11.2).
      Sem LLM no controle de fluxo (1.6). Tipos da Agno confinados aqui. **Não** usar `db=`
      da Agno — `RunStateStore` é a fonte de verdade.
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 6.3, 6.4, 8.2, 11.2_

  - [x] 16.2 Estender o composition_root (wiring do orquestrador)
    - `src/qa_platform/composition_root.py`: monta o `InMemoryRunStateStore`, o
      `LayerRegistry` (com o `AILayerStub` registrado) e o `FeedbackSink` default
      (in-memory/log), reusando `SecretResolver`/config, logging e tracing do bootstrap.
      **Atualizado na 16.4:** como `build_orchestrator` monta o `Workflow` por execução
      (manifest/RunId só existem em run), a função foi renomeada para
      `build_orchestrator_runner` e devolve um runner `(manifest, raw_manifest) ->
      RunResult` que aciona `run_orchestration` com as dependências cabeadas.
    - _Requirements: 1.1, 6.3, 12.5_

  - [x] 16.3 Escrever teste de integração do Orchestrator_Workflow **(obrigatória: prova da engine real)**
    - `tests/infrastructure/orchestration/test_workflow.py`: executa os steps na ordem do
      ADR-001 (1.1); atribui `Run_Id` e registra estado inicial antes do 1º step (1.3);
      falha de store inicial aborta sem steps (1.4); step com erro interrompe subsequentes
      e registra (1.5); camada não conforme ao contrato é marcada como falha preservando
      as demais (6.4); um cliente LLM proibido não é invocado no controle de fluxo (1.6);
      validação do manifest ocorre antes do 1º step (8.2)
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 6.4, 8.2_

- [x] 17. Estender o teste de fronteiras de arquitetura
  - Estender `tests/architecture/test_layer_boundaries.py`: via import-linter, garantir
    que `agno` e o parser YAML (`yaml`/`ruamel`) **não** são importados por `domain` nem
    `interface`, que os value objects/ports do domínio permanecem puros, e incluir um
    cenário negativo que confirma que a verificação **falha** nomeando o módulo/import
    proibido
  - _Requirements: 6.2, 7.3, 11.1, 12.1, 12.2, 12.3, 12.4_

- [x] 18. Checkpoint final - Garantir que tudo passa
  - Executado: `112 passed` na suíte completa (incl. testes de propriedade Hypothesis) e
    import-linter com **4 contratos KEPT** (incl. `agno` confinado). Ver o checkpoint
    revisado (21) para o estado final consolidado.

## Tarefas de correção (revisão do orquestrador — pós-descoberta da divergência Workflow)

> Estas tarefas foram adicionadas após constatar que o `workflow.py` não executava pela
> engine da Agno (Steps `_noop` + runner sequencial paralelo). Decisões: caminho B de
> concorrência (ADR-002) e `RunStateStore` como fonte de verdade (sem `db=`).

- [x] 19. Sincronizar o ambiente com o `pyproject`/lock e limpar config órfã
  - [x] 19.1 Confirmar dependências do ambiente do projeto (`.venv`)
    - Constatado que o `.venv` do projeto já está sincronizado com o `uv.lock`
      (`uv sync` → nada a instalar) e tem as versões fixadas: `agno==2.9.0`, `mangum`,
      `import-linter`, `pyyaml`. A aparente divergência anterior era execução com o
      Python **global** do sistema (sem as libs), não com o `.venv`. Correção operacional:
      rodar sempre pelo interpretador do `.venv` (`.venv/Scripts/python.exe -m pytest`
      e `... -m importlinter.cli`), pois os wrappers `.exe` do venv falham com
      "uv trampoline failed to canonicalize script path".
    - _Requirements: 12.2_
  - [x] 19.2 Remover o `.importlinter` órfão (template não configurado)
    - Removido `code/.importlinter` (template genérico `root_package = "suporte"` que
      **não** validava este projeto). A config real e correta é `code/importlinter.ini`
      (root `qa_platform`, `agno`/`yaml` confinados), invocada explicitamente por scripts
      e pre-commit via `lint-imports --config importlinter.ini`. Import-linter verde:
      4 contratos KEPT (incl. "agno confinado").
    - _Requirements: 12.3, 12.4_

- [x] 20. Checkpoint - Engine real da Agno comprovada
  - Comprovado: `workflow.py` executa **pela engine da Agno** (Steps com executores reais,
    ordem conduzida pela Agno via `workflow.run`). O teste de integração
    `tests/infrastructure/orchestration/test_workflow.py` (8 casos) passa: ordem/persistência
    (1.1/11.2), estado inicial (1.3), aborto por falha de store (1.4), falha de camada
    isolada (1.5/4.3), camada não conforme nomeada (6.4), manifesto inválido antes do 1º
    step (8.2), controle sem LLM (1.6). Correção adicional: `run_layers` (parallel.py)
    passou a registrar retorno não-`LayerEvidence` como falha nomeando a camada (Req 6.4).

- [x] 21. Checkpoint final revisado - Suíte + fronteiras + engine verdes
  - Executado pelo `.venv` do projeto: **112 testes passam** (0 falhas), incluindo os
    testes de propriedade (Hypothesis, Properties 1–15), a integração do workflow (engine
    real da Agno) e do Parallel_Runner. Import-linter: **4 contratos KEPT** (incl. `agno`
    e `yaml` confinados fora de `domain`/`interface`). `CHANGELOG` atualizado.

## Notes

- Legenda de checkbox: `[x]` concluída e verificada; `[ ]` pendente; `[~]` parcial/
  incorreta (requer retrabalho — ver tarefa de correção referenciada).
- A tarefa 16.1 está `[~]`: o `workflow.py` foi criado mas não executa pela engine da
  Agno; a reescrita correta é a tarefa **16.4**, e a prova é o teste **16.3** (agora
  obrigatório, não mais `*`).
- Tarefas marcadas com `*` são opcionais (testes) e podem ser puladas para um MVP mais
  rápido; as tarefas de implementação de núcleo nunca são opcionais.
- Cada tarefa referencia requisitos específicos para rastreabilidade; as tarefas de teste
  de propriedade referenciam também a Correctness Property correspondente.
- Os checkpoints garantem validação incremental em quebras razoáveis.
- Os testes de propriedade (Hypothesis, mín. 100 iterações, uma propriedade por teste)
  validam as 15 propriedades universais de correção sobre a **lógica pura determinística**.
- Conforme a Testing Strategy do design, PBT **não** se aplica a: concorrência real
  (Parallel_Runner), o `Workflow` da Agno, o parser YAML, as fronteiras de arquitetura
  (import-linter) e os requisitos de "ausência de LLM/rede" — todos cobertos por testes
  por exemplo/integração.
- Esta feature reusa integralmente a infraestrutura do bootstrap (SecretResolver/config,
  observabilidade, segurança de borda, import-linter, Hypothesis); nenhum artefato do
  bootstrap é recriado.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "3.1", "3.2", "3.3", "3.4", "4"] },
    { "id": 3, "tasks": ["3.5", "5.1", "5.2"] },
    { "id": 4, "tasks": ["5.3", "6.1", "7.1", "8.1", "9.1"] },
    { "id": 5, "tasks": ["6.2", "6.3", "6.4", "7.2", "8.2", "9.2", "11.1", "11.3", "14.1"] },
    { "id": 6, "tasks": ["11.2", "11.4", "11.5", "11.6", "12.1", "14.2", "14.3", "14.4"] },
    { "id": 7, "tasks": ["12.2", "13.1", "13.2", "13.3"] },
    { "id": 8, "tasks": ["12.3", "12.4", "13.4", "13.5", "13.6", "13.7"] },
    { "id": 9, "tasks": ["16.1"] },
    { "id": 10, "tasks": ["16.2"] },
    { "id": 11, "tasks": ["16.3", "17"] }
  ]
}
```
