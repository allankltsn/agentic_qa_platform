# ADR-004 — Descoberta híbrida de alvo: determinístico no fluxo, LLM advisory fora dele

- **Status:** Aceita (Sprint 2 — Camada IA parte 1: descoberta híbrida & contrato de alvo)
- **Data:** 2026-09-24
- **Contexto do projeto:** QA Platform (`qa-platform/PROJECT.md`, seções 7 e 8.1)
- **Decisores:** autor (Product Owner / Tech Lead), Kiro (assistente)

## Contexto

O `PROJECT.md` (seção 7) prevê **descoberta de alvo híbrida**: a plataforma
inspeciona o repositório-alvo (detecta Agno/LangGraph, extrai tools, prompts e
RAG), **gera um rascunho de `qa-target.yaml`** e o **desenvolvedor revisa e
completa** o manifesto antes da execução. Esse manifesto é o contrato de teste
que alimenta o `Risk_Planner` e o `Layer_Router`.

Hoje o `Target_Discovery` (entregue no esqueleto da Sprint 1) é um **stub
determinístico mínimo**: deriva apenas `target.ref`, fixa
`applicable_layers=["ai"]` e marca todo o restante como `PENDING`. Não inspeciona
o repositório de fato, não detecta framework, não extrai tools/prompts/RAG e não
modela os campos que a camada de IA vai consumir nas Sprints 3+ (domínio esperado
do agente, golden set candidato).

A Sprint 2 precisa tornar a descoberta **real** e híbrida. Isso levanta uma
tensão arquitetural direta com o **ADR-001 (Workflow-first, determinístico)**:

- A parte **"híbrida" plena** implica usar um **LLM** para sugerir campos que
  exigem julgamento (ex.: qual é o domínio esperado do agente, quais casos
  compõem um golden set inicial). Um LLM é, por natureza, **não-determinístico** e
  tem **custo/variância**.
- O ADR-001 exige que o **fluxo de execução** (o `Workflow` raiz) seja
  determinístico e repetível — mesmo alvo na mesma versão → mesmo plano e
  evidências comparáveis, sustentando histórico e comparação entre runs.

A questão: **onde** o não-determinismo do LLM pode existir sem contaminar a
reprodutibilidade do fluxo de execução? E **como** o contrato de alvo cresce para
carregar os novos campos sem quebrar o manifesto atual nem antecipar complexidade
que só a Sprint 7 vai consolidar?

## Decisão

Adotar **descoberta híbrida em duas fases com fronteira dura entre elas**:
o esqueleto do manifesto é produzido por **inspeção estática determinística**
dentro do fluxo; o enriquecimento por **LLM é advisory, opt-in e fica FORA do
`Workflow` de execução**, sempre com o desenvolvedor revisando antes de o
manifesto virar contrato de teste.

Princípio-guia (estende o do ADR-001): **determinístico por dentro do fluxo,
inteligente (e advisory) por fora dele — e o dev é quem promove sugestão a
contrato.**

### As duas fases

| Fase | Componente | Determinismo | LLM/Rede | Onde vive |
|------|-----------|--------------|----------|-----------|
| **1. Inspeção estática** | `Static_Inspector` | Determinístico (mesmo repo → mesmo rascunho) | Não | Dentro do fluxo; é o novo corpo do `Target_Discovery` |
| **2. Enriquecimento** | `LLM_Enricher` | Não-determinístico | Sim (opt-in) | **Fora** do `Workflow`; passo separado acionável pela CLI (`suggest-manifest`) |

- A **Fase 1** substitui o corpo do stub atual preservando sua interface pública,
  a sentinela `PENDING` e o `TargetResolutionError`. Passa a detectar framework
  (Agno/LangGraph por heurísticas de import/arquivo) e a extrair tools/prompts/RAG
  declarados, enriquecendo o rascunho — **sem** LLM e **sem** rede. Continua
  válida como `Step` do `Workflow` (Req 9.x da Sprint 1 preservados).
- A **Fase 2** recebe o rascunho determinístico e **sugere** os campos de
  julgamento (`expected_domain`, `golden_set` candidato). A saída é um **rascunho
  anotado** — as sugestões vêm **marcadas como sugestão**, nunca sobrescrevem
  silenciosamente, e o desenvolvedor as aceita/edita/descarta. Só então o
  manifesto vira `qa-target.yaml` e entra no fluxo de execução.
- O **`Workflow` de execução nunca invoca LLM na descoberta.** A fronteira é
  garantida fisicamente pelo import-linter: o caminho do `Workflow` não pode
  importar o `LLM_Enricher` nem tipos de framework de agentes/LLM.

### Contrato de alvo: expansão simples e retrocompatível

O `qa-target.yaml` ganha campos **opcionais** (fora de `required`), preservando a
validade de todo manifesto atual:

- `discovery` — bloco opcional com o que a inspeção estática detectou
  (framework, tools, prompts/RAG). Documental/derivado; não altera o roteamento.
- `expected_domain` — string opcional (sugerida na Fase 2, confirmada pelo dev)
  descrevendo o domínio esperado do agente.
- `golden_set` — lista opcional de casos candidatos (sugerida na Fase 2). É
  **candidato**, não verdade — insumo para a camada de IA das Sprints 3+.

A modelagem é intencionalmente **mínima e extensível**: campos abertos o
suficiente para a **Sprint 7 crescer por cima** (mais frameworks, extração mais
rica, golden set estruturado), sem antecipar complexidade agora.

### Provider do LLM (Fase 2)

Reusa o padrão do bootstrap: provider resolvido por `MODEL_PROVIDER` via
`SecretResolver`, **fail-fast** quando o enriquecimento é acionado sem provider
configurado (Req 12.5/12.6). A Fase 1 nunca depende de provider. Guardrail mínimo
de escopo na chamada, conforme o baseline do portfólio.

## Justificativa

- **Preserva o ADR-001 integralmente:** o fluxo de execução permanece
  determinístico e reprodutível; o não-determinismo do LLM fica confinado a um
  passo advisory fora do fluxo, então o histórico e a comparação entre runs não
  são contaminados.
- **Custo previsível:** a inspeção estática (grátis, sem token) é o caminho
  padrão; o LLM só roda quando o dev explicitamente pede (opt-in), controlando
  gasto e variância.
- **Fidelidade ao papel advisory do produto:** assim como o "advisory judge" não
  sentencia pass/fail, o enriquecedor **não decide** o contrato — ele sugere, e o
  desenvolvedor promove sugestão a manifesto. Coerência conceitual ponta a ponta.
- **Retrocompatibilidade:** campos novos são opcionais; o manifesto atual e a
  suíte existente continuam válidos — evolução sem breaking change (MINOR no
  SemVer pré-1.0).
- **Extensibilidade para a Sprint 7:** a fronteira em duas fases e o contrato
  aberto permitem enriquecer heurísticas e estruturas depois sem reescrever o
  núcleo nem mexer no fluxo determinístico.
- **Arquitetura limpa:** `Static_Inspector` e `LLM_Enricher` são adapters de
  infraestrutura; VOs novos (`DiscoveryInfo`, `GoldenCase`) são puros no domínio;
  tipos de framework/LLM não vazam para `domain`/`interface` — verificado por
  import-linter.

## Alternativas consideradas

1. **LLM dentro do `Workflow`, como `Step` de descoberta inteligente (rejeitada).**
   Faria a descoberta ser "híbrida" no próprio fluxo. Contras: injeta
   não-determinismo e custo no caminho de execução, quebra a reprodutibilidade que
   sustenta histórico/comparação e exigiria revogar o ADR-001. Descartada por
   conflito direto com o princípio central da plataforma.
2. **Descoberta puramente estática, sem LLM (rejeitada como alvo da sprint).**
   Simples e 100% determinística, mas não entrega a parte "híbrida" pedida
   (`expected_domain`, golden set candidato exigem julgamento). Fica como o
   **fallback padrão** (Fase 1 sozinha), não como escopo completo.
3. **Provider de LLM dedicado à descoberta (`DISCOVERY_MODEL_PROVIDER`)
   (adiada).** Isolaria o modelo de descoberta do modelo das camadas de avaliação.
   Vale reconsiderar quando as camadas reais (Sprints 3+) definirem seus próprios
   modelos; por ora, reusar `MODEL_PROVIDER` evita proliferação de env sem ganho
   concreto (YAGNI).
4. **Expandir o schema de forma "completa" agora (rejeitada).** Modelar golden set
   estruturado, catálogo rico de tools etc. já nesta sprint. Contras: antecipa
   complexidade que a Sprint 7 vai consolidar melhor com mais informação;
   contraria o pedido de manter simples e crescível. Adotada a versão mínima
   extensível.

## Consequências

- **Positivas:** fluxo de execução continua determinístico e auditável; custo do
  LLM controlado por opt-in; contrato de alvo evolui sem quebrar o existente;
  fronteira determinístico/advisory verificada por ferramenta; base saudável para
  a Sprint 7 crescer.
- **Negativas / trade-offs:**
  - Duas fases e uma nova borda (CLI `suggest-manifest`) adicionam superfície a
    manter e testar.
  - Heurísticas de detecção de framework são frágeis por natureza — começam
    simples (Agno/LangGraph) e podem gerar falso negativo/positivo; os limites
    devem ser documentados e o dev sempre revisa.
  - Sugestões do LLM (`expected_domain`, `golden_set`) são não-determinísticas e
    **candidatas** — exigem revisão humana antes de virarem contrato; não devem
    ser tratadas como verdade.
- **Follow-ups para a Sprint 3+ / Sprint 7:**
  - A camada de IA (avaliação/evidências) consumirá `expected_domain` e
    `golden_set` do manifesto — definir como.
  - Reavaliar provider dedicado de descoberta quando os modelos das camadas forem
    definidos.
  - Enriquecer heurísticas de detecção e estruturar melhor o golden set na
    consolidação da Sprint 7.

## Referências

- `qa-platform/PROJECT.md` (seções 7 — descoberta híbrida — e 8.1 — Workflow-first).
- `ADR-001-orquestracao-workflow-first.md` — princípio determinístico do fluxo,
  que este ADR preserva ao confinar o LLM fora dele.
- `ADR-003-persistencia-durable-dynamodb.md` — histórico de runs que depende da
  reprodutibilidade aqui preservada.
- Spec `.kiro/specs/hybrid-target-discovery/` — requirements/design/tasks que
  materializam esta decisão.
- `code/schemas/qa-target.schema.json` — contrato de alvo estendido
  (campos opcionais `discovery`, `expected_domain`, `golden_set`).
- Skills Agno: `agno-basic-agents`, `agno-prompt-system`, `agno-guardrails`
  (chamada de LLM da Fase 2), `agno-secrets` (provider por env com fail-fast),
  `agno-project-architecture-solid` (fronteiras ports & adapters).
