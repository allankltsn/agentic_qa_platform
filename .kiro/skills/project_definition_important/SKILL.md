---
name: project_definition_important
description: Fonte de verdade do escopo, visao, arquitetura e decisoes da QA Platform (QA senior autonomo orientado por IA). SEMPRE ative e consulte esta skill com PRIORIDADE MAXIMA antes de planejar, projetar, decidir ou implementar QUALQUER coisa no projeto — para alinhar escopo, objetivos, nao-objetivos, camadas, tecnologias e padroes arquiteturais. Use ao criar ou revisar codigo, docs, agentes, modulos, orquestracao ou infraestrutura deste workspace.
---

# Project Definition (IMPORTANTE) — QA Platform

Esta skill reune os documentos que **definem e detalham o projeto QA Platform**. Todos
os arquivos listados abaixo sao **cruciais** e formam a **fonte de verdade** de escopo,
visao, arquitetura e decisoes.

As **decisoes de arquitetura (ADRs)** vivem aqui como parte integrante desta fonte de
verdade: `ADR-001` (orquestracao Workflow-first), `ADR-002` (concorrencia das camadas
com executor proprio), `ADR-003` (persistencia durable em DynamoDB) e `ADR-004`
(descoberta hibrida de alvo). Cada nova ADR aceita deve ser adicionada a esta skill e
listada na tabela abaixo — a skill deve sempre refletir o conjunto completo de decisoes.

## Regra de uso (prioridade maxima)

1. **Antes de qualquer implementacao, decisao de design, plano ou refatoracao**, esta
   skill DEVE ser consultada primeiro. Ela tem prioridade de escopo e definicao sobre
   qualquer outra fonte.
2. Nao invente escopo. Se algo nao estiver coberto por estes documentos, trate como
   **em aberto** e alinhe com o autor antes de implementar — nao presuma.
3. Em conflito entre uma ideia de implementacao e o que esta aqui, **estes documentos
   prevalecem**. Se o conflito for legitimo, proponha atualizar o documento primeiro.
4. Ao concluir uma mudanca que altere escopo, arquitetura ou decisoes, **atualize o
   documento correspondente** (PROJECT.md e/ou um novo ADR) para manter a fonte de
   verdade fiel.
5. Fase atual do projeto: **Idealizacao** (versao < 1.0.0). Priorize alinhamento de
   visao e arquitetura sobre codigo de producao.

## Arquivos cruciais desta skill

| Arquivo | Papel | Consulte quando |
|---------|-------|-----------------|
| `PROJECT.md` | Documento mestre de escopo e projeto: visao, problema, objetivos, nao-objetivos, os dois modos do agente (Advisory/Report), as 5 camadas de QA, tecnologias, servicos/modulos plugaveis, descoberta de alvo (`qa-target.yaml`) e arquitetura (ports & adapters + SOLID). | Qualquer definicao de escopo, o que esta dentro/fora, quais camadas e ferramentas usar, contratos de modulo. |
| `ADR-001-orquestracao-workflow-first.md` | Decisao de arquitetura: orquestrador raiz e um **`Workflow` (Agno v2)**, deterministico por fora e inteligente por dentro (Agents/Teams nos steps). Mapeia `Router`/`Parallel`/`Condition`/`Loop`. | Qualquer decisao de orquestracao, coordenacao de agentes, previsibilidade/reprodutibilidade de runs. |
| `ADR-002-concorrencia-camadas-executor-proprio.md` | Decisao de arquitetura: a concorrencia das camadas usa um **executor proprio** (`run_layers`, max 8 / timeout 300s) em vez do `Parallel` nativo da Agno, mantendo o Workflow-first. | Qualquer decisao sobre execucao concorrente de camadas, limites de concorrencia/timeout, uso do `Parallel`. |
| `ADR-003-persistencia-durable-dynamodb.md` | Decisao de arquitetura: historico de runs em **DynamoDB** (+ fallback in-memory), selecao por env com fail-fast; o dominio define o port `RunStateStore` e a infra o realiza. | Qualquer decisao sobre persistencia de estado/resultado de run, historico, backend de armazenamento. |
| `ADR-004-descoberta-hibrida.md` | Decisao de arquitetura: **descoberta hibrida** em duas fases — inspecao estatica deterministica dentro do fluxo + enriquecimento por LLM advisory/opt-in **fora** do `Workflow`; contrato de alvo (`qa-target.yaml`) expandido de forma opcional e retrocompativel. | Qualquer decisao sobre descoberta de alvo, geracao/expansao do `qa-target.yaml`, uso de LLM na descoberta, fronteira deterministico vs advisory. |
| `STUDY.md` | Documento de estudo/idealizacao original: motivacao, o conceito de "QA Agent autonomo", o diagrama das 5 camadas e as ferramentas de referencia por camada. | Entender a origem/racional das decisoes e a visao completa das 5 camadas. |

## Pilares que nao podem ser violados (resumo)

- **QA senior autonomo orientado por IA**: recebe um repo/alvo, detecta stack, planeja
  por **risco**, orquestra camadas de validacao, correlaciona evidencias e centraliza
  numa UI React. Nao e um "AI Code Reviewer" nem chatbot de codigo.
- **Camada nucleo = IA/Agentes** (DeepEval + Promptfoo). As demais (Seguranca,
  Funcional, UX, Codigo) entram progressivamente como **modulos plugaveis**, sem alterar
  o core.
- **Dois modos de saida**: **Advisory** (dados/graficos, o desenvolvedor decide) vs
  **Report** (defeito objetivo, reportado via motor de feedback plugavel).
- **Extensibilidade e nao-objetivos**: novos targets e integracoes de feedback entram
  como plugins; nao e gate automatico de merge; nao substitui revisao humana critica.
- **Padroes de producao do portfolio Agno**: guardrails obrigatorios, providers por env,
  observabilidade (OTel), secrets com fallback, arquitetura em camadas + SOLID. O
  dominio nunca depende de framework.
- **Orquestracao Workflow-first** (ADR-001): deterministico por fora, inteligente por
  dentro. Concorrencia das camadas via executor proprio (ADR-002); historico de runs
  em DynamoDB (ADR-003); descoberta hibrida com LLM advisory fora do fluxo (ADR-004).

Sempre leia o documento relevante por inteiro antes de agir; este SKILL.md e um indice
e um contrato de uso, nao um substituto do conteudo detalhado.
