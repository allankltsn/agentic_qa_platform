# Requirements Document

## Introduction

Este documento especifica os requisitos para a **persistência durável do resultado de
run** da QA Platform — um adapter concreto do contrato `RunStateStore` (port já existente
no domínio) que sobrevive ao encerramento do processo, sustentando o **histórico de runs**
exigido pelo `PROJECT.md` (seções 8 e 10).

**Objetivo de negócio.** Cada execução (run) da plataforma produz um `RunResult`: o
laudo da avaliação de QA sobre um alvo naquela execução (plano de teste, evidências,
métricas, achados priorizados, trabalho pulado e falhas). Hoje esse laudo é efêmero
(some ao encerrar o processo). O objetivo é torná-lo **durável e recuperável** para
sustentar três capacidades centrais do produto: **histórico** (ver runs anteriores de um
alvo), **comparação entre runs** (o alvo melhorou/piorou entre versões?) e
**rastreabilidade** (recuperar um laudo por `run_id` para relatório/feedback sem
re-executar). O que se persiste é o **laudo da avaliação**, não a memória interna do
agente alvo; a configuração do alvo em si vive no `qa-target.yaml` (entrada), não no
registro. Para que os laudos sejam comparáveis por alvo, o registro carrega a
**identidade do alvo** avaliado (referência + versão), não os detalhes internos dele.

O esqueleto do orquestrador (feature `workflow-orchestrator-skeleton`) entregou o port
`RunStateStore` e um adapter **in-memory** que satisfaz o contrato mas perde tudo quando o
processo encerra. Esta feature adiciona um adapter **durável**, mantendo:

- o **port de domínio intacto** (nenhuma mudança de assinatura; o domínio permanece puro,
  sem tipos de infraestrutura/SDK);
- o `RunResult` como **fonte de verdade** do histórico (sem delegar a persistência ao
  `db=` da Agno — coerente com o ADR-001);
- a seleção do adapter (durável vs in-memory) **por variável de ambiente**, com fail-fast
  quando o backend durável é pedido sem os parâmetros obrigatórios (padrão do portfólio:
  serviço serverless preferencial, fallback local).

O backend durável escolhido é **DynamoDB** (decisão registrada no
`ADR-003-persistencia-durable-dynamodb.md`): serverless, já habilitado no LocalStack
núcleo do ambiente local, e alinhado ao bootstrap AWS existente (Secrets Manager, SAM). O
adapter **in-memory** permanece como fallback local.

### Escopo desta spec (enxuto)

Cobre exclusivamente:

- Persistir e recuperar o **`RunResult` final** de forma durável (`save_result` / `get`),
  preservando as semânticas de conflito e ausência do port.
- Incluir a **identidade do alvo avaliado** (`target_ref` + `target_version`) no
  `RunResult`, para que os laudos sejam atribuíveis e comparáveis por alvo. Isso toca o
  domínio (`RunResult` ganha dois campos) e o consolidador/orquestrador que os preenche.
- O **mapeamento serialização ↔ domínio** confinado à infraestrutura, com um **model de
  registro em Pydantic `BaseModel`** (fronteira externa com validação/serialização) e
  `schema_version`.
- A **seleção de adapter por env** (durável vs in-memory) com fail-fast.
- O **provisionamento da tabela** DynamoDB (SAM para AWS + init do LocalStack para dev).

### Fora de escopo desta spec

- **Listagem/histórico consultável de runs** (paginação, ordenação por data): entra numa
  spec futura, junto do frontend que consome o histórico.
- **Persistência durável do estado intermediário** (`start` / `record_failure`): nesta
  fase o `RunResult` final é a fonte de verdade; o estado intermediário permanece
  in-memory. O adapter durável ainda **implementa** esses métodos do port de forma
  compatível (sem quebrar o contrato), mas não é requisito que sejam duráveis agora.
- Métricas de negócio, agregações e comparação analítica entre runs.
- Retenção/TTL automatizado como política de produto.
- Frontend, motor de feedback e a camada de IA real.

## Glossary

- **Run_State_Store**: O contrato (port) de persistência de estado/resultado de run,
  definido no domínio. Já existe; esta feature não altera sua assinatura.
- **Durable_Run_State_Store**: O adapter concreto que persiste o `Run_Result` de cada run
  em um armazenamento durável (DynamoDB), sobrevivendo ao encerramento do processo.
- **In_Memory_Run_State_Store**: O adapter existente que mantém os dados apenas em
  memória; permanece como fallback local.
- **Run_Record_Model**: O model de registro persistido, um Pydantic `BaseModel` na camada
  de infraestrutura, que valida e (de)serializa o `Run_Result` para o item de
  armazenamento.
- **Run_Record_Serializer**: O componente de infraestrutura que converte o `Run_Result`
  de domínio no `Run_Record_Model` e de volta, confinando validação/serialização à
  infraestrutura.
- **Run_Store_Factory**: O componente que seleciona qual adapter do `Run_State_Store`
  instanciar (durável ou in-memory) com base em configuração por variável de ambiente.
- **Run_Result / Run_State / Run_Id**: Value objects de domínio já definidos (resultado
  consolidado, estado em andamento e identidade da run).
- **Schema_Version**: Um identificador de versão do formato do registro persistido,
  incluído em cada registro para permitir evolução futura do esquema.

## Requirements

### Requirement 1: Persistência Durável do Resultado de Run

**User Story:** Como desenvolvedor da plataforma, quero que o resultado de cada run seja
persistido de forma durável, para que o histórico sobreviva ao encerramento do processo.

#### Acceptance Criteria

1. WHEN o Durable_Run_State_Store recebe `save_result(run_id, result)` para um `Run_Id`
   ainda não persistido, THE Durable_Run_State_Store SHALL persistir o `Run_Result` em um
   armazenamento durável de modo que uma leitura subsequente por esse `Run_Id`, mesmo após
   o reinício do processo, retorne o mesmo `Run_Result`.
2. WHEN o Durable_Run_State_Store recebe `get(run_id)` para um `Run_Id` previamente
   persistido, THE Durable_Run_State_Store SHALL retornar um `Run_Result` igual em valor
   ao que foi persistido, com todos os seus campos preservados (plano, evidências,
   priorização, trabalho pulado e falhas).
3. THE Durable_Run_State_Store SHALL preservar a semântica do `Run_State_Store` sem
   alterar a assinatura do port nem introduzir dependências de infraestrutura no domínio.

### Requirement 2: Conflito e Ausência de Run_Id (Preservação da Semântica do Port)

**User Story:** Como desenvolvedor da plataforma, quero que o adapter durável respeite as
mesmas semânticas de conflito e ausência do contrato, para que a troca de adapter não mude
o comportamento observável.

#### Acceptance Criteria

1. IF o Durable_Run_State_Store recebe `save_result` para um `Run_Id` que já possui um
   `Run_Result` persistido, THEN THE Durable_Run_State_Store SHALL sinalizar conflito com
   `RunIdConflictError` identificando o `Run_Id`, sem sobrescrever o `Run_Result`
   previamente persistido.
2. IF o Durable_Run_State_Store recebe `get` para um `Run_Id` nunca persistido, THEN THE
   Durable_Run_State_Store SHALL sinalizar ausência com `RunNotFoundError` identificando o
   `Run_Id`, sem retornar o `Run_Result` de outra execução.
3. IF o Durable_Run_State_Store recebe `save_result` ou `get` com um `Run_Id` ausente,
   nulo ou vazio, THEN THE Durable_Run_State_Store SHALL rejeitar a operação sinalizando
   um erro de `Run_Id` inválido, sem persistir nem retornar qualquer `Run_Result`.
4. THE Durable_Run_State_Store SHALL garantir a ausência de sobrescrita concorrente por
   meio de uma escrita condicionada à inexistência do `Run_Id`, de modo que duas escritas
   concorrentes do mesmo `Run_Id` resultem em exatamente uma persistida e a outra
   sinalizada como conflito.

### Requirement 3: Model de Registro e Mapeamento Serialização ↔ Domínio

**User Story:** Como desenvolvedor da plataforma, quero um model de registro explícito e um
mapeamento entre os value objects de domínio e a representação persistida, para que o
domínio permaneça puro e o formato de armazenamento possa evoluir sem afetá-lo.

#### Acceptance Criteria

1. THE Run_Record_Model SHALL ser um Pydantic `BaseModel` residente na camada de
   infraestrutura (`infrastructure/persistence`), representando o registro persistido do
   `Run_Result`, sem que tipos de SDK de nuvem ou desse model vazem para o domínio.
2. THE Run_Record_Serializer SHALL converter `Run_Result` no Run_Record_Model e
   reconstruir o `Run_Result` de volta, produzindo um value object de domínio igual em
   valor ao original (round-trip sem perda).
3. WHEN o Run_Record_Serializer reconstrói o `Run_Result`, THE Run_Record_Serializer SHALL
   reconstruir integralmente as coleções aninhadas (plano de execução, evidências, achados
   com severidade, trabalho pulado e falhas), preservando ordem e identidade de origem.
4. IF o Run_Record_Serializer encontra um registro persistido malformado ou incompatível
   com o formato esperado, THEN THE Run_Record_Serializer SHALL sinalizar um erro de
   desserialização identificando o `Run_Id` e o motivo, sem retornar um `Run_Result`
   parcial ou silenciosamente incorreto.
5. THE Run_Record_Model SHALL incluir um `Schema_Version` em cada registro persistido, e o
   Run_Record_Serializer SHALL recusar, com erro explícito, um registro cujo
   `Schema_Version` não seja suportado pela implementação corrente.

### Requirement 4: Seleção de Adapter por Configuração (Durável vs In-Memory)

**User Story:** Como desenvolvedor da plataforma, quero selecionar o adapter de
persistência por configuração, para usar o armazenamento durável em ambientes reais e o
in-memory em testes/execução local, sem alterar o código do orquestrador.

#### Acceptance Criteria

1. WHERE a configuração indica o backend durável, THE Run_Store_Factory SHALL instanciar o
   Durable_Run_State_Store; WHERE a configuração indica o backend in-memory ou não indica
   um backend durável, THE Run_Store_Factory SHALL instanciar o In_Memory_Run_State_Store.
2. THE Run_Store_Factory SHALL resolver a seleção do backend por variável de ambiente, sem
   valor de backend fixado no código, com um default explícito e documentado
   (`in_memory`) quando a variável estiver ausente.
3. IF a configuração seleciona o backend durável mas os parâmetros obrigatórios de conexão
   (nome da tabela) estiverem ausentes, THEN THE Run_Store_Factory SHALL interromper a
   inicialização sinalizando um erro que nomeia cada parâmetro ausente, sem cair
   silenciosamente no backend in-memory.
4. THE orquestrador e o composition root SHALL consumir o `Run_State_Store` exclusivamente
   pelo contrato (port), sem referenciar a implementação concreta selecionada pela
   Run_Store_Factory.

### Requirement 5: Provisionamento da Tabela de Armazenamento

**User Story:** Como desenvolvedor da plataforma, quero que a tabela de armazenamento seja
provisionada como código, para que o backend durável funcione em produção (AWS) e no
ambiente local (LocalStack) sem passos manuais.

#### Acceptance Criteria

1. THE definição de infraestrutura serverless (SAM) SHALL declarar a tabela DynamoDB do
   histórico de runs com a chave de partição pelo `Run_Id`, criptografia em repouso
   habilitada e cobrança sob demanda, e SHALL expor o nome da tabela ao serviço por
   variável de ambiente.
2. THE bootstrap do ambiente local (LocalStack) SHALL criar a mesma tabela de forma
   idempotente, de modo que a execução local com o backend durável funcione sem passos
   manuais.
3. THE provisionamento SHALL aplicar o princípio do menor privilégio, concedendo ao
   serviço apenas as permissões necessárias de leitura e escrita na tabela do histórico de
   runs.

### Requirement 6: Confinamento de Infraestrutura e Fronteiras de Arquitetura

**User Story:** Como desenvolvedor da plataforma, quero que o SDK de nuvem e os detalhes de
persistência fiquem confinados à infraestrutura, para preservar a independência do domínio
verificada automaticamente.

#### Acceptance Criteria

1. THE Durable_Run_State_Store, o Run_Record_Model e o Run_Record_Serializer SHALL residir
   na camada de infraestrutura, e o domínio SHALL permanecer sem qualquer importação do
   SDK de nuvem ou desse model de persistência.
2. THE SDK de nuvem (`boto3`) SHALL ser confinado ao adapter durável e aos adapters de
   infraestrutura existentes, sem ser importado por `domain` nem por `interface`, com a
   restrição verificada pela verificação de dependências (import-linter).
3. WHEN a verificação de dependências for executada e detectar no `domain` ou na
   `interface` uma importação do SDK de nuvem ou do model de persistência, THE verificação
   de dependências SHALL falhar identificando o módulo de origem e a importação proibida.
4. THE Durable_Run_State_Store SHALL importar o SDK de nuvem de forma tardia (no ponto de
   uso), de modo que o pacote permaneça importável em ambientes sem o SDK instalado quando
   apenas o backend in-memory é usado.

### Requirement 7: Resiliência e Timeouts de Acesso ao Armazenamento

**User Story:** Como desenvolvedor da plataforma, quero timeouts e tratamento de erro
explícitos no acesso ao armazenamento durável, para que falhas de infraestrutura sejam
sinalizadas de forma clara e não travem a execução.

#### Acceptance Criteria

1. THE Durable_Run_State_Store SHALL configurar timeouts explícitos de conexão e de leitura
   nas chamadas ao armazenamento durável, sem depender de valores padrão implícitos do SDK.
2. IF uma operação de persistência ou de leitura falha por erro de infraestrutura (ex.:
   indisponibilidade, timeout), THEN THE Durable_Run_State_Store SHALL sinalizar um erro de
   armazenamento que identifica a operação e o `Run_Id` afetado, sem expor detalhes
   internos de credenciais ou valores de segredo.
3. THE Durable_Run_State_Store SHALL distinguir um erro de infraestrutura de um conflito de
   `Run_Id` e de uma ausência de `Run_Id`, sinalizando cada caso com o erro apropriado.

### Requirement 8: Identidade do Alvo no Resultado de Run

**User Story:** Como desenvolvedor da plataforma, quero que cada `Run_Result` carregue a
identidade do alvo avaliado, para que os laudos persistidos sejam atribuíveis e
comparáveis por alvo ao longo do tempo.

#### Acceptance Criteria

1. THE Run_Result SHALL incluir a referência do alvo (`target_ref`) e a versão do alvo
   (`target_version`) que a execução avaliou, como campos do value object de domínio, sem
   introduzir dependência de infraestrutura no domínio.
2. WHEN o Evidence_Consolidator produz o `Run_Result` de uma execução, THE
   Evidence_Consolidator SHALL preencher `target_ref` e `target_version` a partir do
   `QA_Target_Manifest` da execução, de modo que o laudo identifique o alvo avaliado.
3. THE identidade do alvo persistida no `Run_Result` SHALL limitar-se à referência e à
   versão do alvo, sem incluir os detalhes internos do agente alvo (ex.: prompts, tools,
   system prompt), que permanecem no `qa-target.yaml` de entrada.
4. THE Run_Record_Serializer SHALL persistir e reconstruir `target_ref` e
   `target_version` no round-trip, preservando-os iguais em valor (parte da Property 1).
5. IF um `Run_Result` é construído sem `target_ref` ou `target_version`, THEN o domínio
   SHALL rejeitar a construção sinalizando um erro de campo obrigatório ausente, de modo
   que nenhum laudo órfão (sem alvo atribuível) seja consolidado ou persistido.
