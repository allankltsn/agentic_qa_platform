# ADR-002 — Concorrência das camadas: executor próprio (caminho B)

- **Status:** Aceita (Sprint 1 — feature `workflow-orchestrator-skeleton`)
- **Data:** 2026-09-11
- **Contexto do projeto:** QA Platform (`qa-platform/PROJECT.md`, seção 8.1; ADR-001)
- **Decisores:** autor (Product Owner / Tech Lead), Kiro (assistente)

## Contexto

O ADR-001 adotou **Workflow-first**: o orquestrador raiz é um `Workflow` da Agno v2 e
mapeia os primitivos `Router`/`Parallel`/`Condition` para roteamento, execução
concorrente e condição de custo. Ao implementar o esqueleto, dois requisitos de
correção do orquestrador impõem restrições específicas sobre a execução concorrente das
camadas de QA:

- **Req 4.1** — no máximo **8 camadas** em execução simultânea.
- **Req 4.4** — cada camada que ultrapassar **300 segundos** é tratada como falha por
  tempo excedido, nomeada, e o parcial das demais é retornado.

A questão: a execução concorrente das camadas deve usar o **`Parallel` nativo** da Agno
ou um **executor próprio** dentro de um `Step`?

Investigação da Agno instalada (v2.5.15): o `Parallel(*steps)` roda os steps
concorrentemente, mas **não expõe diretamente** um limite de grau de concorrência (máx
8) nem um timeout por ramo em segundos (300s) no nível do primitivo. Expressar Req 4.1
e Req 4.4 via `Parallel` nativo exigiria contornos frágeis e difíceis de verificar.

## Decisão

Adotar o **caminho B**: a execução concorrente das camadas é um **único `Step`** cujo
`executor` é o `run_layers` (infra), que já implementa a concorrência com
`ThreadPoolExecutor` limitado a 8 workers e um timeout monotônico de 300s por camada,
retornando o parcial (evidências concluídas + falhas nomeadas).

O `Workflow` continua **Workflow-first**: a **engine da Agno conduz a ordem** dos steps
(Target_Discovery → Risk_Planner → camadas → Consolidação → Advisory_Judge → Feedback);
apenas a **política de concorrência entre camadas** fica encapsulada no executor do
projeto, e não no primitivo `Parallel`.

Princípio-guia (coerente com o ADR-001): **determinístico e auditável por fora; a
concorrência das camadas é um detalhe de infraestrutura testável, com limites
explícitos (8 / 300s) exigidos pelos requisitos.**

## Justificativa

- **Requisitos verificáveis:** Req 4.1 (máx 8) e Req 4.4 (timeout 300s) ficam expressos
  de forma direta e testável (clock monotônico injetável), sem depender de detalhes
  internos do `Parallel`.
- **Isolamento de falha:** o `run_layers` já garante coletar todas as evidências antes
  de retornar e nomear cada camada que falhou/expirou, preservando as concluídas
  (Req 4.2, 4.3).
- **Fronteiras limpas:** os tipos da Agno continuam confinados à infraestrutura; o
  domínio e a application não mudam.
- **Reversibilidade:** `build_parallel` (Parallel nativo), `build_router` (Router com
  `selector=select_layers`) e `build_cost_condition` (Condition determinística)
  permanecem no código como adapters válidos e testáveis — a migração é local.

## Alternativas consideradas

1. **`Parallel` nativo da Agno (não adotada nesta fase).** Prós: mais idiomático, usa o
   primitivo diretamente. Contras: não expõe limite de concorrência (8) nem timeout por
   ramo (300s) de forma direta; expressar Req 4.1/4.4 exigiria contornos frágeis e de
   difícil verificação.
2. **Executor próprio em um `Step` (adotada — caminho B).** Prós: atende Req 4.1/4.4 de
   forma direta e testável; isola a política de concorrência na infra. Contras: o
   `Parallel` nativo não é o executor das camadas nesta fase (fica disponível, porém não
   acionado no fluxo principal).

## Consequências

- Positivas: requisitos de concorrência atendidos e testáveis; fronteiras de arquitetura
  preservadas; mudança confinada a um único `Step`.
- Negativas / trade-offs: divergência pontual do "mapeamento 1:1" do ADR-001 (o
  `Parallel` nativo deixa de ser o executor das camadas nesta fase); duas formas de
  concorrência coexistem no código (uma ativa, uma disponível).
- Follow-up: reavaliar a migração para `Parallel` nativo caso versões futuras da Agno
  passem a expressar limite de concorrência e timeout por ramo no nível do primitivo.

## Referências

- `ADR-001-orquestracao-workflow-first.md` (padrão Workflow-first).
- `.kiro/specs/workflow-orchestrator-skeleton/{requirements,design}.md`
  (Req 4.1–4.5; seção 10 do design — engine real da Agno e caminho B).
- Skill Agno `agno-workflows-advanced` (Router/Parallel/Condition/Loop).
- Contrato confirmado da Agno v2.5.15 (`Step.executor(StepInput) -> StepOutput`;
  `StepOutput.content` trafega objetos de domínio).
