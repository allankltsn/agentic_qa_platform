# Requirements Document

## Introduction

Este documento especifica os requisitos para o **esqueleto do orquestrador Workflow-first**
da QA Platform — a primeira feature da Sprint 1 que constrói o núcleo de orquestração
sobre a fundação já entregue pelo bootstrap do ambiente executável.

O objetivo é entregar o **esqueleto** do orquestrador raiz como um fluxo determinístico e
repetível, conforme o ADR-001 (Workflow-first), provando a extensibilidade da plataforma
por meio de um contrato de camada e de uma camada de IA mínima/stub. O princípio-guia é
**determinístico por fora (o fluxo orquestra passos em ordem definida), inteligente por
dentro (agentes/times ficam confinados aos passos que exigem julgamento)**.

O escopo cobre exclusivamente:

- O **fluxo orquestrador raiz** que executa os passos na ordem definida do esboço
  conceitual do ADR-001.
- Os primitivos de controle determinísticos: **roteamento** (escolhe quais camadas rodar
  conforme o manifesto de alvo), **execução concorrente** (roda camadas independentes em
  paralelo) e **condição** (pula trabalho caro).
- Os **passos determinísticos como funções executoras** (sem consumo de tokens, testáveis
  sem rede): descoberta de alvo (stub/mínimo nesta fase), planejamento por risco,
  consolidação de evidências e disparo de feedback.
- O **contrato de camada de QA** (o "port" que qualquer camada futura implementa) como
  ponto de extensão do roteamento.
- **Uma camada de IA mínima/stub** que implementa esse contrato, sem integrar ferramentas
  reais de avaliação, apenas provando a extensibilidade.
- O **schema do manifesto de alvo** (`qa-target.yaml`) que alimenta o roteamento (teste
  baseado em risco).
- O **contrato de persistência de estado de run** (mínimo; adapter concreto pode ser
  in-memory nesta fase).

### Fora de escopo desta spec

- Integração real de ferramentas de avaliação e red teaming de IA.
- Advisory judge com LLM real (stub/mínimo apenas).
- Motor de feedback com integrações externas reais (apenas o contrato e o disparo).
- Frontend.
- Implementação das demais camadas (Segurança, Funcional, UX, Código) — apenas o ponto de
  extensão do roteamento deve suportá-las.

## Glossary

- **Orchestrator_Workflow**: O fluxo orquestrador raiz da plataforma, determinístico e
  repetível, que executa os passos de QA em uma ordem definida. É o "sistema" central
  desta feature.
- **Orchestration_Step**: Um passo individual executado pelo Orchestrator_Workflow, que
  pode ser uma função executora determinística ou a invocação de uma camada de QA.
- **Executor_Function**: Um passo determinístico implementado como função pura em relação
  a rede e tokens (planejamento, consolidação, disparo de feedback), testável sem serviços
  externos.
- **Target_Discovery**: O passo que inspeciona o alvo e produz um rascunho do
  QA_Target_Manifest. Nesta fase é uma implementação mínima/stub.
- **Risk_Planner**: O Executor_Function que, a partir do QA_Target_Manifest, produz o
  Execution_Plan indicando quais camadas devem rodar e com qual severidade/prioridade.
- **Execution_Plan**: O artefato determinístico produzido pelo Risk_Planner que descreve
  quais QA_Layers executar e em qual configuração, para uma dada entrada.
- **Layer_Router**: O componente determinístico que seleciona quais QA_Layers executar com
  base no Execution_Plan derivado do QA_Target_Manifest.
- **Parallel_Runner**: O componente que executa QA_Layers independentes concorrentemente.
- **Cost_Condition**: O componente determinístico que decide pular um trabalho caro de uma
  QA_Layer quando as condições declaradas no QA_Target_Manifest não o justificam.
- **QA_Layer_Contract**: O contrato (port) que toda camada de QA deve implementar para ser
  orquestrada pelo Layer_Router, definindo entrada, saída e identidade da camada.
- **QA_Layer**: Uma camada de teste que implementa o QA_Layer_Contract (ex.: IA/Agentes,
  Segurança, Funcional, UX, Código).
- **AI_Layer_Stub**: A camada de IA mínima que implementa o QA_Layer_Contract nesta fase,
  sem integrar ferramentas reais de avaliação, produzindo Layer_Evidence estruturada.
- **Layer_Evidence**: O conjunto estruturado de evidências, métricas e achados produzido
  por uma QA_Layer ao ser executada.
- **Evidence_Consolidator**: O Executor_Function que agrega as Layer_Evidence de todas as
  QA_Layers executadas em um Run_Result consolidado.
- **Advisory_Judge**: O passo que correlaciona, prioriza e explica as evidências
  consolidadas sem sentenciar pass/fail. Nesta fase é stub/mínimo.
- **Feedback_Dispatcher**: O Executor_Function que dispara o resultado ao motor de
  feedback por meio de um contrato plugável, sem integrações externas reais nesta fase.
- **QA_Target_Manifest**: O manifesto `qa-target.yaml` que descreve o alvo, as camadas
  aplicáveis e os parâmetros de risco que alimentam o Layer_Router.
- **Run_State_Store**: O contrato de persistência que registra o estado e o resultado de
  cada execução (run) do Orchestrator_Workflow. O adapter concreto pode ser in-memory
  nesta fase.
- **Run_Result**: O artefato consolidado de uma execução, contendo o Execution_Plan, as
  Layer_Evidence e o parecer do Advisory_Judge.
- **Run_Id**: O identificador único de uma execução do Orchestrator_Workflow.
- **Domain_Layer**: A camada de domínio do backend (ports & adapters), livre de qualquer
  dependência de framework.

## Requirements

### Requirement 1: Fluxo Orquestrador Raiz Determinístico

**User Story:** Como desenvolvedor da plataforma, quero um fluxo orquestrador raiz
determinístico, para que o mesmo alvo na mesma versão produza o mesmo plano de execução e
evidências comparáveis entre runs.

#### Acceptance Criteria

1. THE Orchestrator_Workflow SHALL executar os Orchestration_Steps exatamente na seguinte ordem sequencial: (1) Target_Discovery, (2) Risk_Planner, (3) Layer_Router, (4) Evidence_Consolidator, (5) Advisory_Judge e (6) Feedback_Dispatcher, iniciando cada Orchestration_Step somente após a conclusão bem-sucedida do Orchestration_Step imediatamente anterior.
2. WHEN o Orchestrator_Workflow é executado duas vezes com o mesmo QA_Target_Manifest e a mesma versão de alvo, THE Orchestrator_Workflow SHALL produzir Execution_Plans byte-a-byte idênticos em ambas as execuções.
3. WHEN o Orchestrator_Workflow inicia uma execução, THE Orchestrator_Workflow SHALL atribuir à execução um Run_Id único entre todas as execuções e registrar o estado inicial da execução no Run_State_Store antes de iniciar o Target_Discovery.
4. IF a persistência do estado inicial no Run_State_Store falha antes do primeiro Orchestration_Step, THEN THE Orchestrator_Workflow SHALL abortar a execução sem iniciar nenhum Orchestration_Step e propagar um erro indicando falha de registro do estado inicial.
5. IF um Orchestration_Step encerra com erro, THEN THE Orchestrator_Workflow SHALL interromper a execução de todos os Orchestration_Steps subsequentes, registrar no Run_State_Store o identificador do Orchestration_Step que falhou e a causa da falha, e propagar um erro que identifica o Orchestration_Step afetado, preservando no Run_State_Store o estado dos Orchestration_Steps já concluídos.
6. THE Orchestrator_Workflow SHALL decidir a sequência e a seleção dos Orchestration_Steps sem realizar nenhuma consulta a um modelo de linguagem, mantendo o controle de fluxo determinístico.

### Requirement 2: Passos Determinísticos como Funções Executoras

**User Story:** Como desenvolvedor da plataforma, quero que os passos determinísticos sejam
funções executoras sem consumo de tokens nem chamadas de rede, para que sejam testáveis de
forma reprodutível e sem custo.

#### Acceptance Criteria

1. THE Risk_Planner, THE Evidence_Consolidator e THE Feedback_Dispatcher SHALL ser implementados como Executor_Functions que não invocam modelos de linguagem nem realizam chamadas de rede externas, resultando em consumo de tokens igual a zero e nenhuma conexão de rede aberta durante a execução.
2. WHEN o Risk_Planner recebe um QA_Target_Manifest válido, THE Risk_Planner SHALL produzir um Execution_Plan que lista as QA_Layers a executar, cada uma com uma prioridade inteira no intervalo de 1 a 100 derivada dos parâmetros de risco do manifesto.
3. IF o Risk_Planner recebe um QA_Target_Manifest inválido ou sem parâmetros de risco, THEN THE Risk_Planner SHALL rejeitar a entrada sem produzir um Execution_Plan e retornar uma indicação de erro identificando o campo inválido ou ausente.
4. WHEN o Evidence_Consolidator recebe as Layer_Evidence das QA_Layers executadas, THE Evidence_Consolidator SHALL agregar as evidências em um único Run_Result preservando a identidade da QA_Layer de origem de cada evidência.
5. WHEN o Risk_Planner recebe o mesmo QA_Target_Manifest em duas ou mais invocações, THE Risk_Planner SHALL produzir Execution_Plans idênticos, incluindo a mesma lista de QA_Layers e as mesmas prioridades.
6. WHEN o Evidence_Consolidator recebe o mesmo conjunto de Layer_Evidence em qualquer ordem de fornecimento, THE Evidence_Consolidator SHALL produzir Run_Results idênticos.

### Requirement 3: Roteamento de Camadas por Risco

**User Story:** Como desenvolvedor da plataforma, quero um roteamento determinístico que
selecione quais camadas rodar conforme o manifesto de alvo, para concentrar esforço nas
superfícies de maior risco e manter a decisão barata e auditável.

#### Acceptance Criteria

1. WHEN o Layer_Router recebe um Execution_Plan não vazio contendo de 1 a 100 referências de QA_Layer, THE Layer_Router SHALL selecionar para execução exatamente as QA_Layers indicadas no Execution_Plan.
2. WHERE uma QA_Layer está registrada no Layer_Router mas não consta no Execution_Plan, THE Layer_Router SHALL omitir essa QA_Layer da execução.
3. IF o Layer_Router recebe um Execution_Plan que referencia uma QA_Layer não registrada, THEN THE Layer_Router SHALL encerrar retornando um erro que identifica pelo nome a QA_Layer não registrada, sem selecionar nem executar nenhuma QA_Layer, preservando o estado anterior do Layer_Router inalterado.
4. THE Layer_Router SHALL selecionar as QA_Layers com base apenas no Execution_Plan, sem consultar um modelo de linguagem.
5. WHEN uma nova QA_Layer que implementa o QA_Layer_Contract é registrada no Layer_Router, THE Layer_Router SHALL torná-la elegível para seleção sem alteração no código dos Executor_Functions nem do Orchestrator_Workflow.
6. WHEN o Layer_Router recebe duas ou mais vezes o mesmo Execution_Plan com o mesmo conjunto de QA_Layers registradas, THE Layer_Router SHALL produzir a cada vez a mesma seleção de QA_Layers, na mesma ordem.
7. IF o Layer_Router recebe um Execution_Plan vazio, sem nenhuma referência de QA_Layer, THEN THE Layer_Router SHALL encerrar sem selecionar nem executar nenhuma QA_Layer, retornando um resultado de seleção vazio, preservando o estado anterior do Layer_Router inalterado.
8. IF o Layer_Router recebe um Execution_Plan que contém a mesma referência de QA_Layer mais de uma vez, THEN THE Layer_Router SHALL selecionar essa QA_Layer uma única vez para execução, sem executá-la em duplicidade.

### Requirement 4: Execução Concorrente de Camadas Independentes

**User Story:** Como desenvolvedor da plataforma, quero executar camadas independentes de
forma concorrente, para reduzir o tempo total de uma execução.

#### Acceptance Criteria

1. WHEN o Layer_Router seleciona mais de uma QA_Layer sem dependência declarada entre elas, THE Parallel_Runner SHALL iniciar a execução dessas QA_Layers concorrentemente, com no máximo 8 QA_Layers em execução simultânea.
2. WHEN todas as QA_Layers executadas concorrentemente encerram, THE Parallel_Runner SHALL coletar a Layer_Evidence de cada QA_Layer antes de retornar o controle ao Orchestrator_Workflow.
3. IF uma QA_Layer executada pelo Parallel_Runner encerra com erro, THEN THE Parallel_Runner SHALL registrar a falha identificando pelo nome a QA_Layer afetada, aguardar o encerramento das demais QA_Layers em execução e retornar a Layer_Evidence das QA_Layers concluídas junto com a indicação de falha da QA_Layer afetada.
4. IF uma QA_Layer executada pelo Parallel_Runner não encerra dentro de 300 segundos, THEN THE Parallel_Runner SHALL tratar essa QA_Layer como falha por tempo excedido, identificá-la pelo nome e retornar a Layer_Evidence das QA_Layers concluídas junto com a indicação de falha por tempo excedido.
5. THE Parallel_Runner SHALL produzir o mesmo conjunto de Layer_Evidence para o mesmo conjunto de QA_Layers selecionadas, independentemente da ordem de conclusão das QA_Layers.

### Requirement 5: Condição de Custo para Trabalho Caro

**User Story:** Como desenvolvedor da plataforma, quero uma condição determinística que
pule trabalho caro quando não justificado, para controlar o custo de execução.

#### Acceptance Criteria

1. WHEN o Cost_Condition avalia uma QA_Layer cujo trabalho caro não é justificado pelos parâmetros declarados no QA_Target_Manifest, THE Cost_Condition SHALL sinalizar, em até 1 segundo, que esse trabalho caro deve ser pulado.
2. WHERE o trabalho caro de uma QA_Layer é pulado pelo Cost_Condition, THE Orchestrator_Workflow SHALL registrar no Run_Result que a QA_Layer foi executada em modo reduzido, incluindo o identificador da QA_Layer e o motivo do salto.
3. THE Cost_Condition SHALL decidir pular ou executar o trabalho caro com base exclusivamente nos parâmetros declarados no QA_Target_Manifest, sem consultar um modelo de linguagem ou qualquer fonte externa ao QA_Target_Manifest.
4. WHEN o Cost_Condition recebe dois QA_Target_Manifest com parâmetros idênticos, THE Cost_Condition SHALL produzir a mesma decisão de pular ou executar em todas as avaliações.
5. IF o QA_Target_Manifest não contém os parâmetros necessários para avaliar a justificativa do trabalho caro, THEN THE Cost_Condition SHALL sinalizar que o trabalho caro deve ser pulado e registrar no Run_Result um motivo indicando parâmetros ausentes.

### Requirement 6: Contrato de Camada de QA (Ponto de Extensão)

**User Story:** Como desenvolvedor da plataforma, quero um contrato de camada de QA estável,
para que uma camada nova entre como um módulo plugável sem reescrever o núcleo de
orquestração.

#### Acceptance Criteria

1. THE QA_Layer_Contract SHALL definir uma identidade de camada única e não vazia, uma operação de execução que recebe como entrada o Execution_Plan aplicável e o QA_Target_Manifest, e produz como saída um único retorno do tipo Layer_Evidence.
2. THE QA_Layer_Contract SHALL ser definido na Domain_Layer sem qualquer importação de framework de orquestração, de ferramentas de avaliação ou de bibliotecas de infraestrutura.
3. WHEN uma QA_Layer que implementa o QA_Layer_Contract é registrada no Layer_Router, THE Orchestrator_Workflow SHALL executar essa QA_Layer exclusivamente por meio da operação de execução do QA_Layer_Contract, sem referenciar a implementação concreta da camada.
4. IF uma QA_Layer registrada retorna um valor que não é do tipo Layer_Evidence ou que omite a identidade de camada, evidências, métricas ou achados exigidos pelo QA_Layer_Contract, THEN THE Orchestrator_Workflow SHALL registrar a não conformidade indicando a identidade da QA_Layer e a razão da não conformidade, marcar essa QA_Layer como falha, preservar as Layer_Evidence já produzidas pelas demais QA_Layers e prosseguir com a execução das QA_Layers restantes.
5. THE Layer_Evidence SHALL representar evidências, métricas e achados como dados estruturados.
6. THE QA_Layer_Contract SHALL impedir que a Layer_Evidence contenha qualquer veredito pass/fail no nível da camada.

### Requirement 7: Camada de IA Mínima (Stub)

**User Story:** Como desenvolvedor da plataforma, quero uma camada de IA mínima que
implemente o contrato de camada, para provar a extensibilidade do roteamento antes de
integrar ferramentas reais de avaliação.

#### Acceptance Criteria

1. THE AI_Layer_Stub SHALL implementar o QA_Layer_Contract expondo uma identidade de camada única e imutável, distinta da identidade de qualquer outra QA_Layer registrada no Orchestrator_Workflow.
2. WHEN o AI_Layer_Stub é executado pelo Orchestrator_Workflow, THE AI_Layer_Stub SHALL retornar uma Layer_Evidence que contém a identidade da camada, o resultado da execução e a referência ao Execution_Plan recebido, sem invocar ferramentas externas de avaliação ou red teaming.
3. THE AI_Layer_Stub SHALL confinar qualquer tipo de framework de agentes à camada de infraestrutura, sem expor tipos de framework na Domain_Layer.
4. WHEN o AI_Layer_Stub recebe o mesmo Execution_Plan e o mesmo QA_Target_Manifest em execuções distintas, THE AI_Layer_Stub SHALL produzir uma Layer_Evidence cujos campos são iguais em valor à Layer_Evidence produzida na execução anterior.
5. IF o AI_Layer_Stub recebe um Execution_Plan ou um QA_Target_Manifest ausente ou malformado, THEN THE AI_Layer_Stub SHALL abster-se de retornar Layer_Evidence e SHALL sinalizar ao Orchestrator_Workflow um erro indicando entrada inválida.
6. IF ocorre uma falha durante a execução do AI_Layer_Stub, THEN THE AI_Layer_Stub SHALL sinalizar ao Orchestrator_Workflow um erro indicando falha de execução, sem retornar Layer_Evidence parcial.

### Requirement 8: Schema do Manifesto de Alvo

**User Story:** Como desenvolvedor da plataforma, quero um schema explícito do manifesto de
alvo, para que o manifesto seja validável e alimente o roteamento por risco de forma
previsível.

#### Acceptance Criteria

1. THE QA_Target_Manifest SHALL definir os campos que identificam o alvo, as QA_Layers aplicáveis e os parâmetros de risco usados pelo Risk_Planner e pelo Layer_Router, marcando cada campo como obrigatório ou opcional e especificando para cada campo o seu tipo e o conjunto de valores válidos ou os limites de valor aplicáveis.
2. WHEN um QA_Target_Manifest é fornecido ao Orchestrator_Workflow, THE Orchestrator_Workflow SHALL validar o manifesto completo contra o schema antes de executar o primeiro Orchestration_Step, verificando a presença de todos os campos obrigatórios, a conformidade de tipo de cada campo e a aderência de cada valor ao conjunto de valores válidos ou aos limites definidos no schema.
3. IF um QA_Target_Manifest não está em conformidade com o schema, THEN THE Orchestrator_Workflow SHALL encerrar a execução sem executar nenhuma QA_Layer e retornar um erro que identifica pelo nome cada campo ausente, com tipo inválido ou com valor fora dos valores válidos ou limites definidos, indicando para cada um deles o motivo da não conformidade.
4. THE QA_Target_Manifest SHALL representar cada QA_Layer aplicável por um identificador de camada que corresponde exatamente a uma identidade definida por um QA_Layer_Contract existente.
5. IF um QA_Target_Manifest contém um identificador de camada que não corresponde à identidade de nenhum QA_Layer_Contract existente, THEN THE Orchestrator_Workflow SHALL encerrar a execução sem executar nenhuma QA_Layer e retornar um erro que identifica pelo nome cada identificador de camada não correspondido.
6. WHEN o Risk_Planner analisa dois QA_Target_Manifests com valores idênticos em todos os campos, THE Risk_Planner SHALL derivar dos parâmetros de risco o mesmo conjunto de QA_Layers e a mesma ordenação de prioridades em ambas as análises.

### Requirement 9: Descoberta de Alvo (Mínima)

**User Story:** Como desenvolvedor da plataforma, quero um passo de descoberta de alvo
mínimo, para produzir um rascunho de manifesto que o desenvolvedor completa antes da
execução.

#### Acceptance Criteria

1. WHEN o Target_Discovery é executado com uma referência de alvo resolvível, THE Target_Discovery SHALL produzir um rascunho de QA_Target_Manifest em conformidade com o schema do manifesto, no qual cada QA_Layer aplicável é representada por um identificador de camada correspondente à identidade definida pelo QA_Layer_Contract.
2. WHEN o Target_Discovery produz um rascunho de QA_Target_Manifest, THE Target_Discovery SHALL marcar como pendente de preenchimento cada campo obrigatório do schema que não pôde ser derivado da referência de alvo, de modo que o rascunho seja distinguível de um manifesto completo.
3. THE Target_Discovery SHALL produzir o rascunho de QA_Target_Manifest sem invocar um modelo de linguagem e sem realizar chamadas de rede externas nesta fase.
4. WHEN o Target_Discovery recebe a mesma referência de alvo, THE Target_Discovery SHALL produzir o mesmo rascunho de QA_Target_Manifest de forma determinística.
5. IF a referência de alvo fornecida ao Target_Discovery é ausente ou não pode ser resolvida, THEN THE Target_Discovery SHALL encerrar sem produzir um rascunho de QA_Target_Manifest e propagar um erro que identifica a referência de alvo afetada.

### Requirement 10: Advisory Judge (Mínimo) e Restrição Advisory

**User Story:** Como desenvolvedor da plataforma, quero um advisory judge mínimo que
correlacione e explique evidências sem sentenciar, para preservar o princípio advisory em
que o desenvolvedor decide.

#### Acceptance Criteria

1. WHEN o Advisory_Judge recebe um Run_Result consolidado, THE Advisory_Judge SHALL produzir uma correlação e uma priorização que ordena as Layer_Evidence por severidade sem emitir um veredito de pass ou fail.
2. THE Advisory_Judge SHALL preservar no Run_Result todas as Layer_Evidence recebidas, com a mesma contagem e a mesma identidade de origem, adicionando a priorização sem descartar evidência de origem.
3. WHERE um modelo de linguagem não está configurado nesta fase, THE Advisory_Judge SHALL produzir a correlação por meio de uma implementação determinística mínima.
4. WHEN o Advisory_Judge recebe o mesmo Run_Result consolidado em execuções distintas, THE Advisory_Judge SHALL produzir a mesma priorização de forma determinística.
5. IF o Advisory_Judge recebe um Run_Result sem nenhuma Layer_Evidence, THEN THE Advisory_Judge SHALL retornar uma priorização vazia sem emitir veredito e sem sinalizar erro.

### Requirement 11: Contrato de Persistência de Estado de Run

**User Story:** Como desenvolvedor da plataforma, quero um contrato de persistência de
estado de run, para registrar e recuperar o resultado de cada execução e sustentar o
histórico e a comparação entre runs.

#### Acceptance Criteria

1. THE Run_State_Store SHALL ser definido como um contrato (port) na Domain_Layer, sem qualquer importação de framework de orquestração ou de bibliotecas de infraestrutura.
2. WHEN o Orchestrator_Workflow conclui uma execução, THE Run_State_Store SHALL persistir o Run_Result associado ao Run_Id da execução, de modo que uma solicitação subsequente por esse Run_Id retorne o mesmo Run_Result persistido.
3. IF o Orchestrator_Workflow conclui uma execução cujo Run_Id já possui um Run_Result persistido, THEN THE Run_State_Store SHALL sinalizar o conflito de Run_Id duplicado identificando o Run_Id, sem sobrescrever o Run_Result previamente persistido.
4. WHEN um Run_Result é solicitado ao Run_State_Store por um Run_Id existente, THE Run_State_Store SHALL retornar o Run_Result previamente persistido para esse Run_Id, com todos os seus campos idênticos aos que foram persistidos.
5. IF um Run_Result é solicitado ao Run_State_Store por um Run_Id inexistente, THEN THE Run_State_Store SHALL sinalizar a ausência identificando o Run_Id solicitado, sem retornar um Run_Result de outra execução.
6. IF um Run_Result é solicitado ou persistido no Run_State_Store com um Run_Id ausente, nulo ou vazio, THEN THE Run_State_Store SHALL rejeitar a operação sinalizando um erro de Run_Id inválido, sem persistir nem retornar qualquer Run_Result.
7. WHERE nenhum adapter de persistência externo está configurado nesta fase, THE Run_State_Store SHALL operar por meio de um adapter em memória que satisfaz o contrato, retornando os mesmos Run_Result persistidos enquanto o processo permanecer em execução.

### Requirement 12: Fronteiras de Arquitetura (Ports & Adapters)

**User Story:** Como desenvolvedor da plataforma, quero que os tipos de framework fiquem
confinados à infraestrutura, para que o domínio permaneça independente de framework e as
camadas futuras entrem sem violar a separação de responsabilidades.

#### Acceptance Criteria

1. THE Domain_Layer SHALL conter o QA_Layer_Contract, o Run_State_Store, a Layer_Evidence, o Execution_Plan e o Run_Result sem qualquer importação de framework de orquestração, de ferramentas de avaliação ou de bibliotecas de infraestrutura.
2. THE Orchestrator_Workflow e seus adapters de orquestração SHALL residir fora da Domain_Layer, confinando os tipos do framework de orquestração à camada de infraestrutura.
3. WHEN a verificação de dependências for executada e detectar na Domain_Layer uma importação que referencie um framework de orquestração, uma ferramenta de avaliação ou uma biblioteca de infraestrutura, THE verificação de dependências SHALL falhar com status de erro e emitir uma indicação de erro que identifica o módulo de origem e o nome da importação proibida.
4. WHEN a verificação de dependências for executada e a Domain_Layer não contiver nenhuma importação proibida, THE verificação de dependências SHALL concluir com status de sucesso sem reportar violações.
5. THE seleção de provider de modelo de qualquer QA_Layer que use um modelo de linguagem SHALL ser resolvida por variável de ambiente, sem valor de provider fixado no código.
6. IF a variável de ambiente que define o provider de modelo estiver ausente ou vazia no momento da resolução de qualquer QA_Layer que use um modelo de linguagem, THEN THE QA_Layer SHALL interromper sua inicialização e emitir uma indicação de erro que identifica a variável de ambiente ausente, sem selecionar um provider padrão fixado no código.
