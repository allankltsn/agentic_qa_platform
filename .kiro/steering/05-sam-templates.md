---
inclusion: fileMatch
fileMatchPattern: "**/template.{yaml,yml}"
---

# Templates AWS SAM

Padrões para definição de infraestrutura serverless com AWS SAM. Para padrões de código Python, consulte #[[file:.kiro/steering/03-sam-python.md]]. Para Node.js, consulte #[[file:.kiro/steering/04-sam-nodejs.md]].

## Estrutura do Template

- Sempre incluir `AWSTemplateFormatVersion`, `Transform` e `Description`
- Organizar seções na ordem: Globals, Parameters, Mappings, Conditions, Resources, Outputs

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: >
  Descrição concisa do serviço e seu propósito
```

- Usar `Description` para documentar o propósito do stack
- Agrupar recursos relacionados com comentários de seção

## Globals

- Usar `Globals` para evitar repetição de configurações comuns entre funções
- Definir runtime, timeout, memory, tracing e variáveis de ambiente globais

```yaml
Globals:
  Function:
    Runtime: python3.12
    MemorySize: 256
    Timeout: 30
    Tracing: Active
    Environment:
      Variables:
        LOG_LEVEL: INFO
        POWERTOOLS_SERVICE_NAME: !Ref AWS::StackName
  Api: { TracingEnabled: true }
```

- Sobrescrever valores globais no recurso individual quando necessário
- Definir `Tracing: Active` globalmente para habilitar X-Ray em todas as funções

## Parâmetros e Outputs

- Usar `Parameters` para valores que variam entre ambientes (stage, região, nomes de recursos)
- Definir `Type`, `Default` e `AllowedValues` quando aplicável
- Usar `Conditions` para lógica condicional (ex: recursos apenas em produção)

```yaml
Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
Conditions:
  IsProd: !Equals [!Ref Environment, prod]
Outputs:
  ApiUrl:
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
```

- Exportar outputs relevantes para uso em outros stacks via `Export`
- Usar `!Sub` e `!Ref` para referências dinâmicas — evitar hardcode de ARNs

## Configuração de Funções Lambda

- `MemorySize` com base em profiling (Lambda Power Tuning) — padrão mínimo 256 MB
- `Timeout` adequado ao workload — nunca usar o máximo (900s) sem justificativa
- `Tracing: Active` para X-Ray (definir em Globals)
- `Layers` para dependências compartilhadas (Powertools, SDKs)

```yaml
  ProcessOrderFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/handlers/process_order.handler
      CodeUri: .
      Description: Processa pedidos recebidos via API
      MemorySize: 512
      Timeout: 30
      Layers:
        - !Sub arn:aws:lambda:${AWS::Region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:7
      Environment:
        Variables:
          TABLE_NAME: !Ref OrdersTable
```

- `ReservedConcurrentExecutions` para limitar concorrência quando necessário
- `ProvisionedConcurrencyConfig` para funções com requisitos de latência baixa
- `DeadLetterQueue` em funções assíncronas

## Políticas IAM — Menor Privilégio

- Preferir SAM Policy Templates em vez de políticas IAM inline genéricas
- Restringir acesso ao recurso específico — nunca usar `Resource: "*"` sem justificativa

```yaml
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref OrdersTable
        - SQSSendMessagePolicy:
            QueueName: !GetAtt NotificationQueue.QueueName
        - S3ReadPolicy:
            BucketName: !Ref DataBucket
```

- SAM Policy Templates disponíveis: `DynamoDBCrudPolicy`, `SQSSendMessagePolicy`, `SQSPollerPolicy`, `S3ReadPolicy`, `S3CrudPolicy`, `SNSPublishMessagePolicy`, `StepFunctionsExecutionPolicy`, `KMSDecryptPolicy`
- Para políticas customizadas, usar `Statement` com `Action` e `Resource` específicos
- Nunca conceder `*` em `Action` — listar apenas as ações necessárias

## API Gateway e HttpApi

- Preferir `HttpApi` (API Gateway v2) para APIs REST simples — menor custo e latência
- Usar `Api` (API Gateway v1) quando precisar de features avançadas (WAF, request validation, usage plans)
- Configurar autorização em todas as rotas públicas

```yaml
  ApiGateway:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Environment
      CorsConfiguration:
        AllowOrigins: ["https://app.example.com"]
        AllowMethods: [GET, POST, PUT, DELETE]
        AllowHeaders: [Content-Type, Authorization]
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            AuthorizationScopes: [email]
            IdentitySource: $request.header.Authorization
            JwtConfiguration:
              issuer: !Sub "https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}"
              audience: [!Ref UserPoolClient]
```

- Configurar CORS com origens específicas — nunca usar `"*"` em produção
- Definir `ThrottlingBurstLimit` e `ThrottlingRateLimit` para proteção contra abuso
- Usar Lambda Authorizer para lógica de autorização customizada

## Criptografia

- Habilitar criptografia em repouso para todos os recursos de armazenamento
- Usar chaves gerenciadas pela AWS ou KMS customizadas para dados sensíveis

```yaml
  OrdersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      SSESpecification: { SSEEnabled: true }

  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault: { SSEAlgorithm: aws:kms }

  NotificationQueue:
    Type: AWS::SQS::Queue
    Properties: { SqsManagedSseEnabled: true }
```

- APIs sempre via HTTPS (padrão no API Gateway)
- Usar `KMSDecryptPolicy` no SAM para conceder acesso a chaves KMS

## VPC Configuration

- Configurar VPC apenas quando a função precisa acessar recursos em rede privada (RDS, ElastiCache)
- Usar pelo menos 2 subnets em AZs diferentes para alta disponibilidade

```yaml
      VpcConfig:
        SecurityGroupIds: [!Ref LambdaSecurityGroup]
        SubnetIds: [!Ref PrivateSubnet1, !Ref PrivateSubnet2]
```

- Funções em VPC precisam de NAT Gateway para acessar internet e serviços AWS
- Usar VPC Endpoints para serviços AWS (DynamoDB, S3, SQS) — evita tráfego via internet
- Não colocar funções em VPC desnecessariamente — aumenta cold start e custo
