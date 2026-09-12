# Sprint 0 — Fundação da Idealização & Visão de Produto

- **Sprint:** 0 (Idealização)
- **Tema:** Fundação da idealização e visão de produto
- **Status:** Fechada
- **Fonte de verdade da visão:** `qa-platform/PROJECT.md` (documento mestre)

> Este documento é o **entregável formal da Sprint 0**. Ele não duplica o
> `PROJECT.md` — consolida a visão de produto no vocabulário de idealização,
> fixa o problema, os objetivos, o escopo e as fronteiras que orientam todas as
> sprints seguintes, e registra as decisões abertas herdadas para a Sprint 1.
> Quando houver conflito de detalhe, o `PROJECT.md` prevalece como fonte de
> verdade da visão.

## 1. Problema

Projetos heterogêneos (APIs, frontends, agentes de IA, infraestrutura) não têm
hoje um QA que valide de ponta a ponta **funcionalidade, usabilidade,
vulnerabilidade e segurança**, incluindo o comportamento de agentes de IA
(hallucination, tool use, prompt injection, RAG). Ferramentas isoladas não
cobrem tudo nem centralizam evidências.

## 2. Visão de Produto

A QA Platform é uma **plataforma de QA orientada por IA** — um "QA sênior
autônomo": recebe um repositório/alvo, detecta a stack, monta um plano de testes
baseado em risco, executa camadas de validação orquestrando ferramentas
especializadas, correlaciona e prioriza evidências, e centraliza tudo numa
interface para o desenvolvedor **decidir**.

Não é um "AI Code Reviewer" nem um chatbot que olha código. É uma plataforma que
executa a aplicação, gera e roda testes, ataca superfícies (API/UI/agentes) e
produz **evidências acionáveis**.

Princípio de produto central — **advisory judge**: a IA correlaciona sinais das
ferramentas determinísticas, prioriza e explica, mas **o veredito não é
automático**. Quem decide é o desenvolvedor.

## 3. Objetivos

### Primário
Ser uma **ferramenta real de trabalho** para validar os projetos do autor.
Utilidade prática é o foco; o aprendizado (Agno, evals, orquestração) é
consequência.

### Específicos
- Avaliar agentes de IA/LLM como capacidade **núcleo** (primeira camada).
- Nascer **extensível**: novas camadas de teste e novas integrações de feedback
  entram como módulos/plugins, sem alterar o core.
- Centralizar execução, evidências, histórico e configuração numa interface React.
- Separar **otimização** (advisory) de **defeito** (report acionável).
- Reusar os padrões de produção do portfólio Agno (guardrails, providers por env,
  observabilidade, secrets com fallback, arquitetura em camadas + SOLID).

## 4. Dois Modos de Saída

| Modo | Quando | Comportamento |
|------|--------|---------------|
| **Advisory** | Otimização de agente, prompts, qualidade, melhoria contínua | Apresenta dados, gráficos e números. O desenvolvedor decide. Sem report automático. |
| **Report** | Defeito objetivo (frontend, backend, API, etc.) | Deve ser reportado. Modelo e forma do report são dinâmicos, resolvidos pelo motor de Feedbacks Programáveis. |

Ambos desembocam no mesmo **motor de feedback plugável** — muda o payload e o
gatilho, não a mecânica.

## 5. Escopo por Camadas (visão-alvo)

| Camada | O que testa | Ferramentas de referência | Prioridade |
|--------|-------------|---------------------------|------------|
| 🤖 IA/Agentes | hallucination, tool use, RAG, comportamento, segurança do agente | DeepEval + Promptfoo | **Núcleo (1ª)** |
| 🔐 Segurança | vulnerabilidades, ataques, dependências, segredos | Semgrep + OWASP ZAP + scanners | Futuro |
| 🧪 Funcional | APIs, fluxos, regras de negócio | Playwright + API tests | Futuro |
| 👁️ UX | interface, comportamento, visual, acessibilidade | Playwright + Visual AI | Futuro |
| 🧠 Código | bugs, arquitetura, lógica, qualidade | SAST/AST/lint + IA própria | Futuro |

Princípio transversal: **teste baseado em risco** — a plataforma analisa o alvo,
atribui severidade às superfícies e concentra esforço onde importa, em vez de
"testar tudo" cegamente.

## 6. Fronteiras (Não-objetivos desta fase)

- Não é um gate automático de merge no CI. A decisão de "otimização" é do
  desenvolvedor (a plataforma apresenta dados; não sentencia pass/fail).
- Não substitui revisão humana de segurança crítica; reduz falso positivo, não
  elimina.
- Não implementa as 5 camadas de uma vez; começa pela camada de IA/Agentes.

## 7. Premissas e Restrições Herdadas

- **Layout inviolável:** toda implementação vive em `code/`; a raiz guarda apenas
  documentação/metadados e o portfólio de estudo isolado em `agents/`.
- Backend em Python/Agno v2; frontend em React. Projeto separado do portfólio de
  estudo dos 8 agentes.
- Segredos fora do repositório (`.env` + `.env.example`); PII protegida em logs e
  evidências.
- Extensibilidade é requisito arquitetural de primeira classe (plugins de teste e
  de feedback).

## 8. Critérios de Aceite da Sprint 0

- [x] Problema, visão e objetivos declarados e estáveis (`PROJECT.md`).
- [x] Escopo por camadas e priorização da camada de IA como núcleo.
- [x] Fronteiras (não-objetivos) explícitas.
- [x] Premissas e restrições de layout/segurança registradas.
- [x] Modos de saída (advisory/report) definidos como princípio de produto.

## 9. Decisões Abertas Herdadas para a Sprint 1

Registradas aqui na Sprint 0 e resolvidas na Sprint 1 (ver `01-architecture.md`):

1. **Padrão de orquestração** — `Team` (líder LLM) vs `Workflow` (determinístico).
   → Resolvido: ADR-001 (Workflow-first).
2. **Concorrência das camadas** — `Parallel` nativo da Agno vs executor próprio.
   → Resolvido: ADR-002 (executor próprio, caminho B).
3. **Persistência do histórico de runs** — qual backend durável.
   → Resolvido: ADR-003 (DynamoDB + fallback in-memory).

## 10. Nota de Processo (retroativa)

Este artefato foi formalizado após a execução da Sprint 1, para fechar o rito de
idealização (um documento por sprint em `docs/ideation/`). A substância da visão
sempre existiu no `PROJECT.md`; este documento a expressa no formato de
entregável de sprint. A partir da Sprint 2, o artefato de idealização é produzido
junto com a sprint, não retroativamente.

## Referências

- `qa-platform/PROJECT.md` — documento mestre (fonte de verdade da visão).
- `qa-platform/docs/ideation/01-architecture.md` — arquitetura (Sprint 1).
- `qa-platform/docs/ideation/decisions/ADR-00{1,2,3}` — decisões de arquitetura.
- `STUDY.md` — estudo original da ideia e stack de referência.
