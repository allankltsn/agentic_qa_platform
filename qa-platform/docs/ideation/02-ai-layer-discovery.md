# Sprint 2 — Camada IA (parte 1): Descoberta Híbrida & Contrato de Alvo

- **Sprint:** 2 (Idealização)
- **Tema:** Camada IA (parte 1) — descoberta híbrida de alvo e expansão do contrato de alvo
- **Status:** Fechada
- **Decisão:** ADR-004 (**Aceita** e implementada)

> Entregável formal da Sprint 2. Como nas sprints anteriores, a descoberta híbrida
> não ficou apenas conceitual: foi **materializada e verificada** no código sob
> `code/` (spec `hybrid-target-discovery`, suíte verde). Este documento consolida
> a decisão de arquitetura (ADR-004), o contrato de alvo estendido e o estado de
> implementação, apontando o que já roda e o que permanece conceitual para as
> Sprints 3+.

## 1. Objetivo da Sprint

Transformar o `Target_Discovery` — que na Sprint 1 era um **stub determinístico
mínimo** (derivava só `target.ref`, fixava `applicable_layers=["ai"]` e marcava o
resto como `PENDING`) — numa **descoberta híbrida real**: inspecionar o
repositório-alvo, detectar framework de agente (Agno/LangGraph), extrair
tools/prompts/RAG declarados e, de forma opt-in, **sugerir** os campos de
julgamento que a camada de IA vai consumir (`expected_domain`, `golden_set`).

O desafio central: introduzir a inteligência da descoberta **sem** violar o
princípio do ADR-001 (fluxo de execução determinístico e reprodutível).

## 2. Princípio Arquitetural (estende o ADR-001)

**Determinístico por dentro do fluxo, inteligente (e advisory) por fora dele — e o
desenvolvedor é quem promove sugestão a contrato.**

O não-determinismo de um LLM é incompatível com a reprodutibilidade que sustenta
histórico e comparação entre runs. A solução é uma **fronteira dura** entre uma
fase estática (dentro do fluxo) e uma fase de enriquecimento (fora do fluxo, opt-in).

## 3. Descoberta Híbrida em Duas Fases

| Fase | Componente | Determinismo | LLM/Rede | Onde vive |
|------|-----------|--------------|----------|-----------|
| **1. Inspeção estática** | `Static_Inspector` | Determinístico (mesmo repo → mesmo rascunho) | Não | Dentro do fluxo; novo corpo do `Target_Discovery` |
| **2. Enriquecimento** | `LLM_Enricher` | Não-determinístico | Sim (opt-in) | **Fora** do `Workflow`; passo acionável pela CLI (`suggest-manifest`) |

### 3.1 Fase 1 — Inspeção estática (dentro do fluxo)

- Substitui o corpo do stub **preservando a interface pública** do
  `Static_Inspector`: assinatura `(target_ref: str | None) -> dict`, a sentinela
  `PENDING`, `is_pending`/`has_pending_fields` e `TargetResolutionError` seguem
  idênticos à Sprint 1. Continua sendo um `Step` válido do `Workflow`.
- **Leitura estática total** do artefato resolvido (`repo_reader`), produzindo uma
  visão imutável e ordenada dos arquivos. Sem rede, sem LLM, sem `boto3`.
- **Heurísticas de detecção** (`discovery_heuristics`): framework por
  import/arquivo (Agno/LangGraph); tools/prompts/RAG declarados, cada um virando um
  `DetectedItem(identifier, source)`.
- **Determinismo por design:** ordenação total e estável (`DetectedItem` por
  `(source, identifier)`, `frameworks_detected` alfabético). `discover(x)` é
  byte-a-byte idêntico entre execuções e independente da ordem de leitura.
- Ambiguidade explícita: dois frameworks → `ambiguous=True` com ambos em
  `frameworks_detected`; nenhum → `Framework.NOT_DETECTED` (sem erro).
- **`fragility_note`** sempre presente: heurísticas são frágeis por natureza e o
  desenvolvedor deve revisar.
- Campos de julgamento permanecem `PENDING`; leitura incompleta ou tentativa de
  rede/LLM abortam **sem** rascunho parcial.

### 3.2 Fase 2 — Enriquecimento advisory (fora do fluxo, opt-in)

- Recebe o rascunho determinístico e **sugere** os campos que exigem julgamento:
  `expected_domain` e um `golden_set` candidato.
- Produz um **rascunho anotado** (`AnnotatedDraft`): cada saída do LLM vira uma
  `Suggestion` marcada (`origin`, `state="pendente"`). As sugestões **nunca
  sobrescrevem** valores existentes — entram como entradas separadas.
- **Máquina de estados de resolução:** cada sugestão parte de `pendente` e o
  desenvolvedor aplica exatamente uma ação — `aceito`, `editado` ou `descartado`.
  Só depois de promovido pelo humano o manifesto vira contrato de teste.
- **Provider por env com fail-fast:** `MODEL_PROVIDER` resolvido via
  `SecretResolver` **antes** de qualquer chamada; ausente/blank → falha rápida
  (~5s) com `MissingSecretError` nomeando apenas a env (sem vazar valor). Guardrail
  mínimo de escopo rejeita conteúdo fora do domínio. Timeout duro de 120s.
- Acionada explicitamente pela CLI `suggest-manifest` — o caminho padrão (Fase 1)
  **consome zero tokens**.

## 4. Fronteira Determinístico ↔ Advisory (garantida por ferramenta)

O `Workflow` de execução **nunca** invoca LLM na descoberta. A fronteira é
verificada fisicamente pelo import-linter (contratos ADR-004):

- `workflow-nao-importa-enricher` — `infrastructure.orchestration` não importa
  `infrastructure.enrichment`.
- `fase1-sem-llm` — `target_discovery`/`discovery_heuristics`/`repo_reader` não
  importam `agno` nem o módulo de enrichment.
- `agno-confinado` — tipos de `agno` só existem em adapters (agora incluindo
  `infrastructure.enrichment.*` como fonte legítima).
- `domain-puro` — os novos VOs não importam framework/infra.

## 5. Contrato de Alvo Estendido (retrocompatível)

O `qa-target.yaml` ganha três campos **opcionais** (fora de `required`),
preservando a validade de todo manifesto anterior — evolução sem breaking change
(MINOR no SemVer pré-1.0):

| Campo | Tipo | Origem | Papel |
|-------|------|--------|-------|
| `discovery` | objeto opcional | Fase 1 (derivado) | Documental: framework, tools, prompts, RAG detectados. **Não altera o roteamento.** |
| `expected_domain` | string opcional | Fase 2 (sugerido) → dev confirma | Domínio esperado do agente; insumo da camada de IA (Sprints 3+). |
| `golden_set` | lista opcional | Fase 2 (sugerido) → dev confirma | Casos **candidatos**; insumo, não verdade. |

O bloco `discovery` é **documental**: `select_layers(plan_by_risk(M))` é idêntico
com `discovery` vazio ou arbitrário — a descoberta descreve, não decide.

A modelagem é intencionalmente **mínima e extensível**: aberta o suficiente para a
Sprint 7 crescer por cima (mais frameworks, extração mais rica, golden set
estruturado) sem antecipar complexidade agora (YAGNI).

Exemplo completo em `code/examples/qa-target.example.yaml`; schema em
`code/schemas/qa-target.schema.json`.

## 6. Value Objects e Modelos Novos

- **`DiscoveryInfo`** (domain, puro/frozen) — `framework`, `frameworks_detected`,
  `ambiguous`, `tools`/`prompts`/`rag` (tuplas de `DetectedItem`), `fragility_note`
  e `empty()`.
- **`Framework`** (enum) — `AGNO` / `LANGGRAPH` / `NOT_DETECTED`.
- **`DetectedItem`** (frozen) — `identifier` + `source`.
- **`GoldenCase`** (domain, puro/frozen) — `input`, `expected`, `note`.
- **`AnnotatedDraft` / `Suggestion`** (infra, Pydantic na borda) — carregam as
  sugestões marcadas e a máquina de estados de resolução.
- **`EnricherPort`** (application, Protocol estrutural) — desacopla o caso de uso
  `suggest_manifest` do adapter Agno.

## 7. Onde o Código Vive (camadas)

| Componente | Camada | Observação |
|-----------|--------|------------|
| `DiscoveryInfo`, `GoldenCase`, `Framework` | domain | VOs puros, sem framework |
| `EnricherPort`, `suggest_manifest` | application | sem `agno`, sem rede |
| `repo_reader`, `discovery_heuristics`, `target_discovery` | infrastructure | Fase 1, determinística, sem LLM |
| `llm_enricher`, `annotated_draft` | infrastructure | Fase 2, único ponto novo de `agno` |
| subcomando `suggest-manifest` + `build_enricher` | interface | única cola CLI ↔ adapter |

## 8. Estado de Implementação (verificado)

Materializado na spec `hybrid-target-discovery`, com a suíte de qualidade completa
executada no checkpoint final (Ruff, mypy, import-linter e pytest, incluindo os
testes de propriedade com Hypothesis ≥ 100 iterações):

- Fase 1 determinística: leitura estática, heurísticas, `Static_Inspector`
  reescrito com interface preservada e integrado como `Step` do Workflow.
- Fase 2 advisory: `LLMEnricher` (Agno), rascunho anotado com máquina de estados,
  caso de uso `suggest_manifest`, CLI `suggest-manifest` e wiring no
  `composition_root`.
- Fronteiras ADR-004 verificadas por import-linter como teste determinístico.
- Schema e exemplo de manifesto estendidos, retrocompatíveis.

**Conceitual / próximas sprints:** consumo real de `expected_domain` e
`golden_set` pela camada de IA (Sprints 3+); heurísticas de detecção mais ricas e
golden set estruturado (consolidação na Sprint 7); reavaliar um provider dedicado
de descoberta quando as camadas de avaliação definirem seus modelos.

## 9. Critérios de Aceite da Sprint 2

- [x] Descoberta de alvo real (não-stub) decidida e justificada (ADR-004).
- [x] Fronteira determinístico (fluxo) ↔ advisory (LLM fora do fluxo) definida e
      garantida por ferramenta (import-linter).
- [x] Fase 1 determinística: detecção de framework e extração de
      tools/prompts/RAG, sem LLM e sem rede.
- [x] Fase 2 advisory opt-in: sugestões marcadas, sem sobrescrita silenciosa, com
      promoção humana obrigatória.
- [x] Contrato de alvo estendido de forma opcional e retrocompatível
      (`discovery`, `expected_domain`, `golden_set`).
- [x] Provider por env com fail-fast; guardrail de escopo na chamada de LLM.
- [x] Descoberta materializada e verificada no código (`hybrid-target-discovery`).

## 10. Trade-offs Registrados (ADR-004)

- Duas fases e a nova borda CLI adicionam superfície a manter e testar.
- Heurísticas de detecção são frágeis — começam simples (Agno/LangGraph), podem
  gerar falso negativo/positivo; limites documentados e revisão humana sempre.
- Sugestões do LLM são não-determinísticas e **candidatas** — nunca tratadas como
  verdade antes da promoção humana.

## Referências

- `qa-platform/PROJECT.md` — seções 7 (descoberta híbrida) e 8.1 (Workflow-first).
- `qa-platform/docs/ideation/01-architecture.md` — arquitetura da Sprint 1.
- `.kiro/skills/project_definition_important/ADR-004-descoberta-hibrida.md` —
  decisão de arquitetura consolidada.
- `.kiro/specs/hybrid-target-discovery/` — requirements/design/tasks.
- `code/schemas/qa-target.schema.json` e `code/examples/qa-target.example.yaml` —
  contrato de alvo estendido e exemplo válido.
