# Requirements Document

## Introduction

Este documento especifica os requisitos da feature **Descoberta Híbrida de Alvo**
da QA Platform, que materializa o **ADR-004 — "Descoberta híbrida de alvo:
determinístico no fluxo, LLM advisory fora dele"** (Sprint 2 — Camada IA parte 1),
apoiada nas seções 7 (descoberta híbrida) e 8.1 (Workflow-first) do `PROJECT.md`.

O objetivo é substituir o `Target_Discovery` mínimo/stub da Sprint 1 por uma
descoberta híbrida **real em duas fases, com fronteira dura entre elas**:

- **Fase 1 — Inspeção estática (`Static_Inspector`)**: determinística, dentro do
  fluxo de execução, sem LLM e sem rede. Passa a detectar o framework de agente
  (Agno/LangGraph por heurísticas de import/arquivo) e a extrair ferramentas,
  prompts e RAG declarados, enriquecendo o rascunho do manifesto. Preserva a
  interface pública, a sentinela `PENDING` e o `TargetResolutionError` da Sprint 1.
- **Fase 2 — Enriquecimento (`LLM_Enricher`)**: não-determinística, **fora** do
  `Workflow` de execução, opt-in e advisory, acionada pela CLI `suggest-manifest`.
  Recebe o rascunho determinístico e **sugere** os campos de julgamento
  (`expected_domain`, `golden_set` candidato) como um **rascunho anotado** —
  sugestões marcadas como sugestão, que o desenvolvedor aceita, edita ou descarta.

O princípio-guia (estende o ADR-001) é **determinístico por dentro do fluxo,
inteligente e advisory por fora dele — e o desenvolvedor é quem promove sugestão
a contrato**.

### Fora de escopo desta spec

- Consumo de `expected_domain` e `golden_set` pela camada de IA de avaliação
  (Sprints 3+).
- Heurísticas de detecção além de Agno e LangGraph e golden set estruturado
  (consolidação prevista para a Sprint 7 — YAGNI).
- Provider de LLM dedicado à descoberta (`DISCOVERY_MODEL_PROVIDER`); esta feature
  reusa `MODEL_PROVIDER` (decisão adiada no ADR-004).
- Frontend e edição interativa do manifesto na CLI (a edição é feita pelo
  desenvolvedor no arquivo).

## Glossary

- **Static_Inspector**: O adapter de infraestrutura determinístico que inspeciona
  o repositório-alvo (sem LLM e sem rede) e produz o rascunho enriquecido do
  QA_Target_Manifest. É o novo corpo do Target_Discovery e permanece um passo
  válido do Orchestrator_Workflow.
- **Target_Discovery**: O passo do Orchestrator_Workflow que produz o rascunho do
  QA_Target_Manifest. Nesta feature sua implementação passa a ser o Static_Inspector.
- **LLM_Enricher**: O adapter de infraestrutura não-determinístico, opt-in e
  advisory, executado **fora** do Orchestrator_Workflow, que recebe o rascunho
  determinístico e sugere campos de julgamento por meio de um LLM.
- **Orchestrator_Workflow**: O fluxo orquestrador raiz determinístico e repetível
  (ADR-001), que executa os passos de QA em ordem definida e nunca invoca LLM na
  descoberta.
- **Suggest_Manifest_Command**: O subcomando de CLI `suggest-manifest` que aciona
  o LLM_Enricher sobre um rascunho e emite o rascunho anotado.
- **Draft**: O rascunho do QA_Target_Manifest produzido pela Fase 1, conforme a
  forma do schema, com campos obrigatórios não deriváveis marcados como PENDING.
- **Annotated_Draft**: O rascunho de saída da Fase 2, contendo o rascunho
  determinístico acrescido de campos sugeridos, cada sugestão marcada como sugestão.
- **QA_Target_Manifest**: O manifesto `qa-target.yaml` que descreve o alvo, as
  camadas aplicáveis e os parâmetros de risco/custo; contrato de teste que alimenta
  o Risk_Planner e o Layer_Router.
- **Manifest_Parser**: O adapter de infraestrutura que lê `qa-target.yaml`, valida
  contra o schema e retorna o QA_Target_Manifest como value object puro do domínio.
- **Framework_Detection**: A identificação determinística do framework de agente
  do alvo (Agno ou LangGraph) por heurísticas de import/arquivo.
- **DiscoveryInfo**: O value object puro do domínio que representa o que a inspeção
  estática detectou (framework, ferramentas, prompts, RAG). Documental/derivado.
- **GoldenCase**: O value object puro do domínio que representa um caso candidato
  do golden set.
- **PENDING**: A sentinela que marca um campo obrigatório do schema ainda não
  derivado, tornando um Draft distinguível de um manifesto completo.
- **TargetResolutionError**: A exceção levantada quando a referência de alvo é
  ausente ou irresolvível na Fase 1.
- **SecretResolver**: O resolvedor de configuração/segredos por pipe de fallback
  (env → Secrets Manager) com falha rápida, entregue no bootstrap.
- **MODEL_PROVIDER**: A variável de ambiente que identifica o provider de LLM
  usado pelo LLM_Enricher.
- **Import_Linter_Boundary**: O contrato de import-linter que garante fisicamente
  que o caminho do Orchestrator_Workflow não importa o LLM_Enricher nem tipos de
  framework de agente/LLM, e que tipos de framework/LLM não vazam para
  `domain`/`interface`.
- **CI_Pipeline**: O pipeline de integração contínua que executa a verificação de
  arquitetura (import-linter) e bloqueia a integração quando um contrato de
  fronteira falha.
- **Developer**: A pessoa que revisa o rascunho anotado e promove sugestões a
  contrato antes da execução.

## Requirements

### Requirement 1: Preservação da interface, da sentinela e do erro do Target_Discovery

**User Story:** Como mantenedor da plataforma, quero que a Fase 1 preserve a interface pública, a sentinela `PENDING` e o `TargetResolutionError` da Sprint 1, para que a descoberta híbrida seja adotada sem quebrar o Orchestrator_Workflow nem os consumidores existentes.

#### Acceptance Criteria

1. THE Static_Inspector SHALL expor a interface pública do Target_Discovery da Sprint 1, incluindo os símbolos `discover_target`, `is_pending`, `has_pending_fields` e a sentinela `PENDING`, todos importáveis com os mesmos nomes e assinaturas definidos na Sprint 1.
2. WHEN a Fase 1 produz um Draft, THE Static_Inspector SHALL atribuir a sentinela `PENDING` a cada campo obrigatório do schema cujo valor não puder ser derivado do repositório-alvo, deixando inalterados os campos cujo valor foi derivado.
3. WHEN a Fase 1 produz um Draft, THE Static_Inspector SHALL garantir que `is_pending` retorne verdadeiro para cada campo marcado com `PENDING` e falso para os demais, e que `has_pending_fields` retorne verdadeiro se e somente se ao menos um campo obrigatório estiver marcado com `PENDING`.
4. IF a referência de alvo é ausente, vazia (string sem caracteres não-brancos) ou irresolvível, THEN THE Static_Inspector SHALL levantar `TargetResolutionError` cuja indicação de erro nomeia a referência de alvo afetada, sem produzir um Draft.
5. THE Static_Inspector SHALL permanecer um passo válido do Orchestrator_Workflow, aceitando a mesma assinatura de entrada e produzindo o mesmo formato de saída consumidos pelo fluxo na Sprint 1.

### Requirement 2: Inspeção estática determinística, sem LLM e sem rede

**User Story:** Como responsável pela reprodutibilidade do fluxo, quero que a Fase 1 seja determinística e livre de LLM e de rede, para que o mesmo repositório na mesma versão produza sempre o mesmo rascunho e o histórico de runs permaneça comparável.

#### Acceptance Criteria

1. WHEN o Static_Inspector inspeciona o mesmo repositório-alvo na mesma versão (mesmo identificador de commit), THE Static_Inspector SHALL produzir Drafts byte-a-byte idênticos em todas as execuções repetidas.
2. THE Static_Inspector SHALL produzir o Draft sem invocar qualquer modelo de linguagem.
3. THE Static_Inspector SHALL produzir o Draft sem realizar chamadas de rede.
4. WHERE elementos do Draft têm ordem (por exemplo, ferramentas detectadas), THE Static_Inspector SHALL emitir esses elementos em uma ordem total, estável e determinística (segundo critério de ordenação explícito e independente da ordem de leitura do sistema de arquivos) idêntica entre execuções sobre a mesma entrada.
5. IF o Static_Inspector tenta invocar um modelo de linguagem ou iniciar qualquer chamada de rede durante a produção do Draft, THEN THE Static_Inspector SHALL abortar a produção do Draft, não emitir Draft parcial e sinalizar uma falha indicando violação da restrição de determinismo (sem LLM e sem rede).
6. IF o repositório-alvo na mesma versão não pode ser lido de forma completa (por exemplo, arquivo ou conteúdo inacessível), THEN THE Static_Inspector SHALL abortar a produção do Draft, não emitir Draft parcial e sinalizar uma falha indicando que a entrada não pôde ser inspecionada integralmente.

### Requirement 3: Detecção de framework de agente

**User Story:** Como desenvolvedor de agente, quero que a inspeção estática detecte o framework do meu agente, para que o rascunho já registre se o alvo usa Agno ou LangGraph.

#### Acceptance Criteria

1. WHEN o Static_Inspector identifica no repositório-alvo pelo menos uma ocorrência de heurística de import de Agno ou de arquivo indicativo de Agno, THE Static_Inspector SHALL registrar `agno` como framework detectado no bloco `discovery` do Draft.
2. WHEN o Static_Inspector identifica no repositório-alvo pelo menos uma ocorrência de heurística de import de LangGraph ou de arquivo indicativo de LangGraph, THE Static_Inspector SHALL registrar `langgraph` como framework detectado no bloco `discovery` do Draft.
3. IF o Static_Inspector identifica ocorrências de heurística de mais de um framework suportado no mesmo repositório-alvo, THEN THE Static_Inspector SHALL registrar no bloco `discovery` do Draft cada framework detectado e marcar a detecção como ambígua, exigindo revisão do Developer.
4. IF o Static_Inspector não identifica nenhuma ocorrência de heurística de framework suportado, THEN THE Static_Inspector SHALL registrar no bloco `discovery` do Draft o framework como não detectado e SHALL prosseguir com a produção do Draft até sua conclusão.
5. THE Static_Inspector SHALL registrar no bloco `discovery` do Draft uma indicação de que as heurísticas de detecção são frágeis e podem produzir falso positivo ou falso negativo, com marcação de que o resultado exige revisão do Developer.

### Requirement 4: Extração de ferramentas, prompts e RAG declarados

**User Story:** Como desenvolvedor de agente, quero que a inspeção estática extraia as ferramentas, os prompts e o RAG declarados no alvo, para que o rascunho descreva a superfície do agente sem que eu preencha manualmente esses dados.

#### Acceptance Criteria

1. WHEN o repositório-alvo declara uma ou mais ferramentas identificáveis por heurística, THE Static_Inspector SHALL registrar cada ferramenta detectada no bloco `discovery` do Draft, incluindo o identificador da ferramenta e a localização de origem (caminho de arquivo) que fundamentou a detecção.
2. WHEN o repositório-alvo declara um ou mais prompts identificáveis por heurística, THE Static_Inspector SHALL registrar cada prompt detectado no bloco `discovery` do Draft, incluindo o identificador do prompt e a localização de origem (caminho de arquivo) que fundamentou a detecção.
3. WHEN o repositório-alvo declara uso de RAG identificável por heurística, THE Static_Inspector SHALL registrar cada indício de RAG detectado no bloco `discovery` do Draft, incluindo o identificador do indício e a localização de origem (caminho de arquivo) que fundamentou a detecção.
4. IF nenhuma ferramenta, prompt ou uso de RAG identificável por heurística é encontrado no repositório-alvo, THEN THE Static_Inspector SHALL registrar o bloco `discovery` do Draft com coleções vazias para ferramentas, prompts e RAG, sem interromper a inspeção nem gerar erro.
5. THE Static_Inspector SHALL representar as informações detectadas por meio do value object `DiscoveryInfo`.
6. THE bloco `discovery` SHALL ser documental e derivado e SHALL NOT alterar o roteamento produzido pelo Layer_Router.

### Requirement 5: Extensão retrocompatível do schema com campos opcionais

**User Story:** Como mantenedor do contrato de alvo, quero que os novos campos do manifesto sejam opcionais, para que todo manifesto atual e a suíte existente permaneçam válidos, caracterizando uma evolução MINOR sem breaking change.

#### Acceptance Criteria

1. THE QA_Target_Manifest schema SHALL definir `discovery` como campo opcional, ausente da lista `required`, contendo os subcampos framework, ferramentas, prompts e RAG detectados na Fase 1.
2. THE QA_Target_Manifest schema SHALL definir `expected_domain` como campo opcional do tipo string, ausente da lista `required`.
3. THE QA_Target_Manifest schema SHALL definir `golden_set` como campo opcional do tipo lista de casos candidatos, ausente da lista `required`.
4. WHEN um manifesto válido segundo o schema anterior a esta feature (sem os campos `discovery`, `expected_domain` e `golden_set`) é validado contra o schema estendido, THE Manifest_Parser SHALL considerá-lo válido, sem exigir a presença de nenhum dos três campos opcionais.
5. WHEN um manifesto contendo `discovery`, `expected_domain` ou `golden_set` é mapeado, THE Manifest_Parser SHALL produzir os value objects puros do domínio (`DiscoveryInfo`, `GoldenCase`) sem expor tipos do parser YAML fora da camada de infraestrutura.
6. WHEN um manifesto no qual `discovery`, `expected_domain` ou `golden_set` está ausente é mapeado, THE Manifest_Parser SHALL construir os value objects correspondentes com valor vazio ou default e concluir o mapeamento com sucesso.
7. IF um campo opcional (`discovery`, `expected_domain` ou `golden_set`) está presente porém malformado segundo o schema, THEN THE Manifest_Parser SHALL rejeitar o manifesto com um erro de validação que nomeia o campo problemático, sem produzir um value object parcial.

### Requirement 6: Enriquecimento opt-in via CLI `suggest-manifest`

**User Story:** Como desenvolvedor, quero acionar o enriquecimento por LLM explicitamente pela CLI `suggest-manifest`, para que o gasto de tokens e a variância ocorram somente quando eu pedir, mantendo a inspeção estática como caminho padrão gratuito.

#### Acceptance Criteria

1. WHEN o Developer executa o Suggest_Manifest_Command sobre um Draft válido, THE LLM_Enricher SHALL receber o Draft determinístico como entrada e produzir um Annotated_Draft.
2. THE Static_Inspector SHALL produzir o Draft sem exigir a execução do Suggest_Manifest_Command e sem invocar o LLM_Enricher, consumindo zero tokens.
3. WHILE o Suggest_Manifest_Command não é executado, THE plataforma SHALL NOT invocar o LLM_Enricher.
4. WHEN o Suggest_Manifest_Command conclui com sucesso, THE Suggest_Manifest_Command SHALL emitir o Annotated_Draft e retornar exit code `0`.
5. IF o Draft fornecido ao Suggest_Manifest_Command é ausente, ilegível ou não corresponde à estrutura esperada de um Draft determinístico, THEN THE Suggest_Manifest_Command SHALL rejeitar a execução sem invocar o LLM_Enricher, emitir uma mensagem de erro indicando a natureza da invalidez do Draft, preservar o Draft de entrada inalterado e retornar exit code diferente de `0`.
6. IF o LLM_Enricher falha ou não retorna o Annotated_Draft dentro de 120 segundos após ser invocado, THEN THE Suggest_Manifest_Command SHALL abortar o enriquecimento, emitir uma mensagem de erro indicando a falha ou expiração do tempo limite, preservar o Draft determinístico de entrada inalterado e retornar exit code diferente de `0`.

### Requirement 7: Sugestões marcadas, nunca sobrescritas silenciosamente

**User Story:** Como desenvolvedor, quero que as sugestões do LLM venham marcadas como sugestão e nunca sobrescrevam valores do rascunho silenciosamente, para que eu decida conscientemente o que aceitar, editar ou descartar.

#### Acceptance Criteria

1. WHEN o LLM_Enricher sugere `expected_domain`, THE LLM_Enricher SHALL registrar a sugestão no Annotated_Draft com um marcador de origem igual a "sugestão" e um estado inicial igual a "pendente".
2. WHEN o LLM_Enricher sugere um `golden_set` candidato, THE LLM_Enricher SHALL registrar cada `GoldenCase` no Annotated_Draft com um marcador de origem igual a "candidato" e um estado inicial igual a "pendente".
3. THE LLM_Enricher SHALL preservar no Annotated_Draft todos os campos do Draft determinístico de entrada com valores idênticos aos recebidos, sem remover, alterar ou reordenar qualquer campo.
4. IF o Draft de entrada já contém um valor não vazio para um campo que o LLM_Enricher sugeriria, THEN THE LLM_Enricher SHALL manter o valor existente inalterado e registrar a sugestão como uma entrada separada marcada com origem "sugestão" e estado "pendente".
5. WHEN o desenvolvedor resolve uma sugestão ou candidato, THE LLM_Enricher SHALL aceitar exatamente uma das três ações — aceitar, editar ou descartar — e atualizar o estado da entrada de "pendente" para o estado correspondente à ação escolhida.
6. IF o desenvolvedor não resolve uma sugestão ou candidato, THEN THE LLM_Enricher SHALL manter a entrada com estado "pendente" e não aplicar seu valor ao campo correspondente do Annotated_Draft.

### Requirement 8: Revisão do desenvolvedor antes de rascunho virar contrato

**User Story:** Como responsável pela qualidade do contrato de teste, quero que nenhum rascunho — determinístico ou anotado — entre no fluxo de execução sem revisão humana, para que sugestões candidatas não sejam tratadas como verdade.

#### Acceptance Criteria

1. WHILE um Draft (determinístico ou anotado) contém um ou mais campos com valor `PENDING`, THE Manifest_Parser SHALL rejeitar o manifesto correspondente e retornar uma indicação de erro que nomeie explicitamente cada campo pendente, sem promover o manifesto ao Orchestrator_Workflow.
2. IF um Draft submetido ao Manifest_Parser não contém nenhum campo `PENDING` mas falha na validação de esquema, THEN THE Manifest_Parser SHALL rejeitar o manifesto e retornar uma indicação de erro que identifique cada campo inválido, preservando o Draft original sem alteração.
3. WHEN um manifesto é submetido ao Orchestrator_Workflow, THE plataforma SHALL verificar que o Annotated_Draft foi promovido a `qa-target.yaml` pelo Developer e, caso a promoção não tenha ocorrido, SHALL impedir a entrada no fluxo de execução e retornar uma indicação de erro informando que a revisão humana é obrigatória.
4. THE plataforma SHALL tratar os valores sugeridos de `expected_domain` e `golden_set` como candidatos não confirmados até que o Developer os confirme explicitamente no `qa-target.yaml`, e SHALL impedir o uso desses valores no fluxo de execução enquanto permanecerem não confirmados.

### Requirement 9: Resolução fail-fast do provider de LLM

**User Story:** Como operador da plataforma, quero que o enriquecimento falhe rápido quando acionado sem provider de LLM configurado, para que nenhuma execução prossiga meio-configurada e a mensagem identifique a variável ausente.

#### Acceptance Criteria

1. WHEN o Suggest_Manifest_Command é acionado com `MODEL_PROVIDER` presente e não vazio, THE LLM_Enricher SHALL resolver o valor do provider de LLM a partir de `MODEL_PROVIDER` por meio do SecretResolver antes de qualquer invocação do provider de LLM.
2. IF `MODEL_PROVIDER` está ausente ou consiste apenas de espaços em branco no momento do acionamento do Suggest_Manifest_Command, THEN THE LLM_Enricher SHALL encerrar a execução em até 5 segundos com um erro que identifica o nome da variável ausente e não inclui o valor de qualquer segredo, deixando o Draft produzido pelo Static_Inspector inalterado.
3. IF a resolução de `MODEL_PROVIDER` pelo SecretResolver falha por indisponibilidade da fonte de segredos, THEN THE LLM_Enricher SHALL encerrar a execução em até 5 segundos com um erro que indica a falha de resolução do provider e não inclui o valor de qualquer segredo.
4. THE Static_Inspector SHALL produzir o Draft sem ler `MODEL_PROVIDER` nem invocar o SecretResolver.
5. WHEN o LLM_Enricher invoca o provider de LLM, THE LLM_Enricher SHALL aplicar à chamada um guardrail de escopo mínimo conforme o baseline do portfólio, rejeitando a chamada cujo conteúdo esteja fora do escopo definido nesse baseline.

### Requirement 10: Fronteira determinístico/advisory garantida por ferramenta

**User Story:** Como guardião da arquitetura, quero que a fronteira entre o fluxo determinístico e o enriquecimento advisory seja garantida fisicamente por import-linter, para que o Orchestrator_Workflow nunca alcance um LLM na descoberta e o domínio permaneça puro.

#### Acceptance Criteria

1. WHEN o import-linter é executado sobre o pacote `qa_platform`, THE Import_Linter_Boundary SHALL reportar PASS para o contrato que proíbe o caminho do Orchestrator_Workflow importar o LLM_Enricher e reportar FAIL caso tal import direto exista.
2. WHEN o import-linter é executado, THE Import_Linter_Boundary SHALL reportar PASS para o contrato que proíbe `qa_platform.domain` e `qa_platform.interface` importarem diretamente o módulo `agno` (framework de agente/LLM da Fase 2) e reportar FAIL caso qualquer import direto de `agno` exista nessas origens.
3. WHEN o import-linter é executado, THE Import_Linter_Boundary SHALL reportar PASS para o contrato de camadas em que `qa_platform.domain` não importa `qa_platform.application`, `qa_platform.infrastructure` nem `qa_platform.interface`, e reportar FAIL caso qualquer dessas dependências exista.
4. THE Static_Inspector e o LLM_Enricher SHALL residir sob `qa_platform.infrastructure` como adapters, e WHEN o import-linter é executado, THE Import_Linter_Boundary SHALL reportar PASS para o contrato que os confina a essa camada.
5. THE value objects `DiscoveryInfo` e `GoldenCase` SHALL residir em `qa_platform.domain.value_objects` sem importar `qa_platform.infrastructure`, `qa_platform.interface` nem o módulo `agno`, e WHEN o import-linter é executado, THE Import_Linter_Boundary SHALL reportar PASS para o contrato `domain-puro` que verifica essa pureza.
6. IF qualquer contrato de fronteira reporta FAIL, THEN THE Import_Linter_Boundary SHALL identificar na saída o import ofensor (módulo de origem e módulo de destino) e encerrar com código de saída diferente de zero.
7. WHEN o pipeline de CI executa a verificação de arquitetura, THE CI_Pipeline SHALL executar o import-linter e, IF qualquer contrato reporta FAIL, THEN bloquear a integração (merge/deploy) da mudança.

## Correctness Properties (para Property-Based Testing)

As propriedades abaixo cobrem a lógica pura e as invariantes estruturais desta
feature; a análise de aplicabilidade (property vs. exemplo/integração) será
consolidada no design.

1. **Determinismo da Fase 1 (idempotência de saída):** para toda entrada de
   repositório-alvo/versão, executar o Static_Inspector duas vezes produz Drafts
   iguais — `discover(x) == discover(x)` (Req 2.1, 2.4). Property-based sobre
   estruturas de repositório sintéticas em memória.
2. **Retrocompatibilidade do schema:** para todo manifesto válido segundo o schema
   anterior, a validação contra o schema estendido também é válida — quantificação
   universal sobre manifestos válidos gerados (Req 5.4).
3. **Round-trip do parser do manifesto:** para todo QA_Target_Manifest válido
   contendo os novos campos opcionais, `parse(serialize(m))` produz um manifesto
   equivalente, incluindo `discovery`, `expected_domain` e `golden_set` (Req 5.5).
   Round-trip essencial para parser/serializer.
4. **Sugestões nunca sobrescrevem silenciosamente (invariante):** para todo par
   (Draft, sugestões), todo campo presente no Draft de entrada mantém o mesmo
   valor no Annotated_Draft, e cada sugestão aparece marcada como sugestão —
   `enrich(draft, s).base_fields == draft.fields` (Req 7.3, 7.4). Property-based
   com o provider de LLM mockado.
5. **Preservação da sentinela PENDING:** para todo Draft com pelo menos um campo
   não derivável, `has_pending_fields(draft)` é verdadeiro e o Manifest_Parser
   rejeita o manifesto (Req 1.2, 8.1).
6. **Fronteira Workflow-nunca-importa-LLM:** o grafo de imports do caminho do
   Orchestrator_Workflow não contém o LLM_Enricher nem tipos de framework/LLM —
   invariante verificada pelo import-linter como teste determinístico (Req 10.1,
   10.2, 10.3).
7. **Erro em condições ruins:** para toda referência de alvo ausente, vazia ou
   só-espaços, o Static_Inspector levanta `TargetResolutionError` nomeando a
   referência (Req 1.3). Geração de entradas inválidas.
