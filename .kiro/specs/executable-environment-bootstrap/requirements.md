# Requirements Document

## Introduction

Este documento especifica os requisitos para o **bootstrap do ambiente executável** da
QA Platform — o primeiro marco de implementação do projeto. O objetivo é entregar um
esqueleto **rodável e implantável**, sem nenhuma regra de negócio de QA (sem
orquestração, sem agentes, sem avaliação). O escopo cobre exclusivamente:

- Uma única rota HTTP de saúde (`GET /health`) que confirma que o serviço está de pé.
- Um ambiente local de dependências via **Docker Compose** (simulando tecnologias de
  terceiros, no padrão do portfólio).
- O **handler de Lambda** como ponto de entrada serverless.
- Um **template AWS SAM** (`template.yaml`) para empacotar e implantar via Lambda +
  API Gateway.
- **Scripts de desenvolvedor** para build, execução local e deploy.
- Estrutura de projeto (ports & adapters), gestão de ambiente com **uv** e tratamento
  de **configuração/segredos por variável de ambiente** com falha rápida.

Este marco estabelece a fundação sobre a qual as camadas de QA serão adicionadas em
marcos futuros. Nenhuma lógica de negócio é implementada aqui.

## Glossary

- **QA_Platform_Service**: A aplicação backend em Python (FastAPI) que expõe a rota de
  saúde e será, futuramente, a plataforma de QA. É o "sistema" nesta fase.
- **Health_Endpoint**: A rota HTTP `GET /health` exposta pelo QA_Platform_Service.
- **Lambda_Handler**: O ponto de entrada serverless que adapta a aplicação FastAPI para
  execução no AWS Lambda (via adapter ASGI, ex.: Mangum).
- **SAM_Template**: O arquivo `template.yaml` (AWS Serverless Application Model) que
  descreve a função Lambda, o API Gateway e as Layers de dependências.
- **Dependency_Environment**: O conjunto de serviços de terceiros executados localmente
  via Docker Compose (ex.: LocalStack para AWS, provider LLM local, stack de
  observabilidade), simulando o ambiente de produção.
- **Developer_Script**: Um script de linha de comando fornecido no repositório para
  automatizar build, execução local ou deploy.
- **Config_Resolver**: O componente responsável por ler valores de configuração e
  segredos a partir de variáveis de ambiente, com falha rápida quando um valor
  obrigatório está ausente.
- **Project_Scaffold**: A estrutura de pastas do backend seguindo ports & adapters
  (domain, application, infrastructure, interface) e gestão de ambiente com uv.
- **API_Gateway**: O serviço AWS API Gateway que expõe as rotas HTTP da plataforma e
  encaminha as requisições para a função Lambda.
- **SAM_CLI**: A ferramenta de linha de comando do AWS SAM usada para validar, construir
  e implantar o SAM_Template.

## Requirements

### Requirement 1: Endpoint de Saúde

**User Story:** Como desenvolvedor, quero uma rota HTTP de saúde, para confirmar que o
serviço está executável e respondendo antes de qualquer regra de negócio existir.

#### Acceptance Criteria

1. WHEN uma requisição HTTP `GET /health` é recebida, THE QA_Platform_Service SHALL responder com o código de status HTTP 200 em até 1 segundo.
2. WHEN uma requisição HTTP `GET /health` é recebida, THE QA_Platform_Service SHALL retornar um corpo JSON contendo um campo de status com o valor `"ok"`.
3. WHEN uma requisição HTTP `GET /health` é recebida, THE QA_Platform_Service SHALL retornar um corpo JSON contendo um campo de versão do serviço obtido da configuração.
4. IF a versão do serviço não está disponível na configuração no momento da inicialização, THEN THE Config_Resolver SHALL encerrar a inicialização do QA_Platform_Service com um erro que identifica a variável de versão ausente.
5. THE Health_Endpoint SHALL operar sem depender de qualquer serviço externo, banco de dados ou provider de LLM.

### Requirement 2: Ambiente Local de Dependências (Docker Compose)

**User Story:** Como desenvolvedor, quero um ambiente local de dependências via Docker
Compose, para executar a plataforma localmente simulando a infraestrutura de terceiros.

#### Acceptance Criteria

1. THE Dependency_Environment SHALL ser descrito em um único arquivo Docker Compose versionado no repositório.
2. WHEN o comando de subida do Docker Compose é executado, THE Dependency_Environment SHALL iniciar todos os serviços de terceiros definidos para desenvolvimento local e considerá-los prontos quando cada serviço reportar estado saudável (healthy) em até 120 segundos.
3. IF um ou mais serviços não atingirem o estado saudável dentro de 120 segundos após o comando de subida, THEN THE Dependency_Environment SHALL encerrar o comando com falha, indicar quais serviços não iniciaram e preservar os logs de cada serviço para diagnóstico.
4. THE Dependency_Environment SHALL incluir um serviço que simula os serviços AWS localmente para dar suporte ao fluxo serverless.
5. THE Dependency_Environment SHALL expor cada serviço em uma porta configurável por variável de ambiente, com um valor padrão definido quando a variável estiver ausente.
6. IF a porta configurada para um serviço já estiver em uso no host durante a subida, THEN THE Dependency_Environment SHALL encerrar o comando com falha e indicar o serviço e a porta em conflito, sem iniciar parcialmente os demais serviços.
7. WHERE a plataforma executa localmente, THE QA_Platform_Service SHALL comunicar-se com o Dependency_Environment por meio de endpoints configurados por variável de ambiente.
8. IF uma requisição do QA_Platform_Service a um endpoint do Dependency_Environment não obtiver resposta dentro de 30 segundos ou retornar erro, THEN THE QA_Platform_Service SHALL registrar a falha indicando o endpoint afetado e retornar um erro ao chamador sem alterar o estado da requisição em andamento.

### Requirement 3: Ponto de Entrada Lambda

**User Story:** Como desenvolvedor, quero um handler de Lambda, para executar a mesma
aplicação FastAPI no ambiente serverless da AWS sem reescrever a lógica de rotas.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL adaptar a aplicação FastAPI para o modelo de invocação do AWS Lambda por meio de um adapter ASGI.
2. WHEN uma requisição do API Gateway para `GET /health` invoca o Lambda_Handler, THE QA_Platform_Service SHALL retornar o código de status HTTP 200 com o corpo de saúde em JSON.
3. IF a inicialização do Lambda_Handler falhar, THEN THE Lambda_Handler SHALL encerrar a invocação com um erro que identifica a causa da falha, sem retornar uma resposta HTTP 200.
4. THE Lambda_Handler SHALL expor a mesma definição de rotas usada na execução local.
5. WHEN uma requisição do API Gateway para um caminho ou método não definido invoca o Lambda_Handler, THE QA_Platform_Service SHALL retornar o mesmo comportamento de recurso não encontrado observado na execução local.

### Requirement 4: Empacotamento e Deploy via AWS SAM

**User Story:** Como desenvolvedor, quero um template AWS SAM, para empacotar e
implantar o serviço como Lambda + API Gateway de forma reproduzível.

#### Acceptance Criteria

1. THE SAM_Template SHALL declarar exatamente uma função Lambda cujo handler referencia o Lambda_Handler como ponto de entrada, com timeout definido em 30 segundos e memória definida em 512 MB.
2. THE SAM_Template SHALL declarar um evento de API Gateway que roteia requisições `GET /health` para a função Lambda.
3. IF uma requisição chega a um caminho ou método não declarado no SAM_Template, THEN THE API_Gateway SHALL rejeitar a requisição sem invocar a função Lambda e retornar uma resposta indicando recurso não encontrado.
4. THE SAM_Template SHALL empacotar as dependências de runtime em uma AWS Lambda Layer separada do código da aplicação, contendo o código da aplicação apenas no artefato da função e nenhuma dependência de runtime duplicada na Layer.
5. THE SAM_Template SHALL definir as configurações da aplicação por variáveis de ambiente da função Lambda, com cada variável obrigatória declarada com nome e valor não vazio.
6. WHEN o comando de build do SAM é executado, THE SAM_Template SHALL produzir um artefato implantável em até 300 segundos e encerrar com código de saída zero, sem erros de validação de template.
7. IF a validação do template falha durante o build, THEN THE SAM_CLI SHALL encerrar com código de saída diferente de zero, não produzir artefato implantável e emitir uma mensagem indicando a causa da falha de validação.

### Requirement 5: Estrutura de Projeto e Gestão de Ambiente

**User Story:** Como desenvolvedor, quero uma estrutura de projeto em ports & adapters
com ambiente gerenciado por uv, para que as camadas de QA futuras entrem como módulos
sem violar a separação de responsabilidades.

#### Acceptance Criteria

1. THE Project_Scaffold SHALL organizar o código backend em exatamente quatro camadas nomeadas domain, application, infrastructure e interface, cada uma como diretório distinto e sem sobreposição de arquivos entre camadas.
2. THE Project_Scaffold SHALL manter a camada domain sem qualquer importação de frameworks web, de bibliotecas de infraestrutura (acesso a dados, rede, sistema de arquivos ou clientes externos) ou de código das camadas application, infrastructure e interface.
3. WHEN uma importação na camada domain referenciar um framework web, uma biblioteca de infraestrutura ou outra camada, THE Project_Scaffold SHALL rejeitar a verificação de dependências com uma indicação de erro identificando o módulo e a importação proibida.
4. THE Project_Scaffold SHALL declarar todas as dependências Python do projeto e o ambiente isolado usando uv, com cada dependência fixada em uma versão exata.
5. THE Project_Scaffold SHALL definir a rota de saúde na camada interface, sem que a camada domain contenha ou dependa de qualquer definição dessa rota.

### Requirement 6: Scripts de Desenvolvedor

**User Story:** Como desenvolvedor, quero scripts de linha de comando, para executar
build, rodar localmente e implantar sem memorizar comandos longos.

#### Acceptance Criteria

1. WHEN o Developer_Script de setup é executado, THE Developer_Script SHALL instalar as dependências, preparar o ambiente local e encerrar com código de saída zero em caso de sucesso.
2. WHEN o Developer_Script de execução local é executado, THE Developer_Script SHALL iniciar o QA_Platform_Service e expor o Health_Endpoint respondendo com status positivo em até 30 segundos.
3. WHEN o Developer_Script de build serverless é executado, THE Developer_Script SHALL executar o build do artefato via SAM e encerrar com código de saída zero em caso de sucesso.
4. WHEN o Developer_Script de deploy serverless é executado, THE Developer_Script SHALL executar o deploy do artefato via SAM e encerrar com código de saída zero em caso de sucesso.
5. IF um Developer_Script requer uma dependência de sistema ausente, THEN THE Developer_Script SHALL encerrar com um código de saída diferente de zero e uma mensagem que identifica a dependência ausente, sem aplicar alterações parciais no ambiente.
6. IF a execução de um Developer_Script falha por qualquer outra causa, THEN THE Developer_Script SHALL encerrar com um código de saída diferente de zero e uma mensagem que identifica a causa da falha.

### Requirement 7: Configuração e Segredos por Ambiente

**User Story:** Como desenvolvedor, quero configuração e segredos resolvidos por
variável de ambiente com falha rápida, para que o serviço nunca inicie com uma
configuração obrigatória ausente.

#### Acceptance Criteria

1. WHEN o QA_Platform_Service é inicializado, THE Config_Resolver SHALL ler todos os valores de configuração a partir das variáveis de ambiente antes de o serviço aceitar requisições.
2. IF uma variável de ambiente obrigatória está ausente ou possui valor vazio no momento da inicialização, THEN THE Config_Resolver SHALL encerrar a inicialização do QA_Platform_Service, impedir que o serviço aceite requisições e emitir um erro que identifica pelo nome cada variável obrigatória ausente ou vazia.
3. IF uma ou mais variáveis de ambiente obrigatórias estão ausentes ou vazias, THEN THE Config_Resolver SHALL relatar todas as variáveis com problema em uma única emissão de erro, e não apenas a primeira encontrada.
4. WHERE uma variável de ambiente opcional está ausente ou possui valor vazio, THE Config_Resolver SHALL aplicar o valor padrão predefinido para essa variável e disponibilizar esse valor efetivo para inspeção durante a inicialização.
5. THE repositório SHALL fornecer um arquivo de exemplo de variáveis de ambiente que contém uma entrada para cada variável de configuração lida pelo Config_Resolver, com valores de segredos substituídos por marcadores de exemplo em vez de valores reais.
6. THE repositório SHALL excluir os arquivos de segredos locais do controle de versão, de modo que nenhum valor real de segredo seja rastreado.
