# ADR-001 — Padrão de orquestração: Workflow-first

- **Status:** Aceita (confirmada no fechamento da Sprint 1 — Arquitetura)
- **Data:** 2026-09-10 (aceita em 2026-09-12)
- **Contexto do projeto:** QA Platform (`qa-platform/PROJECT.md`, seção 8.1)
- **Decisores:** autor (Product Owner / Tech Lead), Kiro (assistente)

## Contexto

O orquestrador da plataforma recebe um repositório/alvo, monta um plano de teste
baseado em risco e coordena múltiplas camadas de QA (IA/Agentes como núcleo; Segurança,
Funcional, UX e Código no futuro), consolidando evidências para o "advisory judge" e
para o motor de feedback.

A Agno v2 oferece dois padrões de coordenação de múltiplos agentes:

- **`Team`** — um líder (LLM) decide em runtime para quem delegar cada parte. Flexível,
  bom para tarefas abertas/criativas, porém **menos previsível**.
- **`Workflow`** — a ordem dos passos é definida pelo desenvolvedor, com primitivos de
  controle (`Router`, `Parallel`, `Condition`, `Loop`). **Previsível e repetível.**

A questão: o orquestrador raiz deve ser um `Team` gerenciando subagentes, ou um
`Workflow`?

## Decisão

Adotar **Workflow-first**: o orquestrador raiz é um `Workflow`. `Team`/`Agent` são
usados **dentro** dos steps, onde julgamento dinâmico agrega valor.

Princípio-guia: **determinístico por fora (Workflow), inteligente por dentro
(Agents/Teams nos steps).**

### Mapeamento dos primitivos

| Primitivo | Uso na plataforma |
|-----------|-------------------|
| `Workflow` | Orquestrador raiz — ordem definida, repetível, auditável |
| `Router` | Escolhe quais camadas rodar conforme `qa-target.yaml` (teste baseado em risco); ponto de extensão para novas camadas |
| `Parallel` | Executa camadas independentes concorrentemente (ganho de tempo) |
| `Condition` | Pula trabalho caro (ex: red teaming pesado só com tools sensíveis) — economia de custo |
| `Team` | Apenas dentro de uma camada aberta (ex: camada de IA decide entre RAG / tool use / red team) |
| `executor` (função) | Passos determinísticos (planejamento, consolidação, disparo de feedback) — sem token, testáveis sem rede |
| `Loop` | Exploração adaptativa dentro de uma camada, com `end_condition` clara |

### Esboço conceitual

```text
Workflow (raiz — determinístico)
├─ Step: Descoberta de alvo (agent)            # inspeciona repo -> rascunho qa-target.yaml
├─ Step: Planejamento por risco (executor fn)  # gera plano
├─ Router(selector por qa-target.yaml)         # escolhe QUAIS camadas rodar
│   └─ Parallel(
│         Step(team=ai_layer_team),            # IA/Agentes (DeepEval + Promptfoo)
│         Step(team=security_team),            # futuro
│         Step(team=functional_team),          # futuro
│         Step(team=ux_team),                  # futuro
│         Step(team=code_team),                # futuro
│      )
├─ Step: Consolidação de evidências (executor fn)
├─ Step: Advisory Judge (agent)                # correlaciona/prioriza/explica (não sentencia)
└─ Step: Motor de Feedback (executor fn)        # advisory -> UI; defeito -> report plugável
```

## Justificativa

- **Reprodutibilidade:** o mesmo repo no mesmo commit deve gerar o mesmo plano de
  execução e evidências comparáveis, sustentando histórico e comparação entre runs.
- **Custo:** roteamento por LLM (líder de `Team`) gasta tokens e adiciona variância;
  `Router`/`Condition` decidem o fluxo de forma determinística e barata.
- **Auditabilidade:** um fluxo explícito é mais fácil de rastrear e explicar do que a
  delegação livre de um líder LLM.
- **Coerência com o "advisory judge":** queremos controle sobre o *fluxo*, deixando a IA
  restrita às etapas de *interpretação* (não à decisão de o que rodar nem ao veredito).
- **Extensibilidade:** uma camada nova é um `Step` adicionado ao choice do `Router`, sem
  reescrever o núcleo.
- **Arquitetura limpa:** o `Workflow` orquestra; adapters de infra encapsulam
  DeepEval/Promptfoo; tipos da Agno não vazam do domínio (ports & adapters + SOLID).

## Alternativas consideradas

1. **Team-first (rejeitada como raiz).** Um líder LLM decide dinamicamente quais camadas
   rodar. Prós: flexível, permite exploração emergente. Contras: não-reprodutível, mais
   caro, difícil de auditar — conflita com os requisitos de histórico/comparação e com o
   papel advisory.
2. **Híbrido com exploração global via Loop na raiz (parcialmente adotada).** A ideia de
   "gerar novos testes quando encontra área suspeita" (do `STUDY.md`) é atraente, mas
   perigosa como padrão global (custo, loops). Adotada apenas como **`Loop` controlado
   dentro de uma camada**, com `end_condition` explícita.

## Consequências

- Positivas: runs comparáveis, custo previsível, fluxo auditável, extensão por Router.
- Negativas / trade-offs: menos "autonomia emergente" no nível global; exploração
  adaptativa fica confinada a loops locais com limites claros.
- Follow-ups para a Sprint 1: definir o contrato de `Step` de cada camada, o schema do
  `qa-target.yaml` que alimenta o `Router`, e onde o estado de run é persistido.

## Referências

- `qa-platform/PROJECT.md` (seções 8 e 8.1).
- `ADR-002-concorrencia-camadas-executor-proprio.md` — decisão sobre a concorrência das
  camadas (caminho B): executor próprio (`run_layers`, máx 8 / timeout 300s) em vez do
  `Parallel` nativo nesta fase.
- Skills Agno: `agno-workflows-advanced` (Router/Parallel/Condition/Loop; Team vs
  Workflow), `agno-teams` (Team, reasoning no líder, times de times).
- `STUDY.md` — visão original (inclui a ideia de exploração adaptativa).
