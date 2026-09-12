---
inclusion: fileMatch
fileMatchPattern: "**/*.{ts,js}"
---

# Backend Serverless — AWS SAM com Node.js/TypeScript

Padrões para desenvolvimento de funções Lambda com AWS SAM e TypeScript/Node.js. Para convenções gerais de código, consulte #[[file:.kiro/steering/01-padroes-gerais.md]]. Para configuração de infraestrutura SAM, consulte #[[file:.kiro/steering/05-sam-templates.md]].

## Estrutura de Handler Lambda

- Assinatura padrão com tipos do `@types/aws-lambda`:
- Inicializar clientes SDK **fora** do handler (connection reuse)
- Separar lógica de negócio do handler — handler apenas orquestra
- Retornar resposta no formato `APIGatewayProxyResult` quando aplicável:

```typescript
import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from "aws-lambda";
import { Logger, Tracer, Metrics } from "@aws-lambda-powertools/logger";

// Clientes fora do handler (connection reuse)
const tableName = process.env.TABLE_NAME!;

export const handler = async (
  event: APIGatewayProxyEvent,
  context: Context
): Promise<APIGatewayProxyResult> => {
  try {
    const result = await processBusinessLogic(event);
    return { statusCode: 200, body: JSON.stringify(result) };
  } catch (error) {
    if (error instanceof ValidationError) {
      return { statusCode: 400, body: JSON.stringify({ error: error.message }) };
    }
    logger.error("Erro inesperado", { error });
    return { statusCode: 500, body: JSON.stringify({ error: "Internal server error" }) };
  }
};
```

- Usar variáveis de ambiente para configuração (nomes de tabelas, filas, buckets)
- Nunca retornar stack traces ou detalhes internos em respostas de erro
- Usar `export const handler` (named export) como padrão

## AWS Lambda Powertools para TypeScript

- Instalar pacotes individuais: `@aws-lambda-powertools/logger`, `@aws-lambda-powertools/tracer`, `@aws-lambda-powertools/metrics`
- `Logger` para logging estruturado JSON — instanciar com `serviceName` explícito
- `Tracer` para instrumentação X-Ray — usar `captureAWSv3Client` para clientes SDK
- `Metrics` para métricas customizadas CloudWatch EMF — usar `MetricUnit` tipado

```typescript
import { Logger } from "@aws-lambda-powertools/logger";
import { Tracer } from "@aws-lambda-powertools/tracer";
import { Metrics, MetricUnit } from "@aws-lambda-powertools/metrics";

const logger = new Logger({ serviceName: "orders-service" });
const tracer = new Tracer({ serviceName: "orders-service" });
const metrics = new Metrics({ namespace: "OrdersApp", serviceName: "orders-service" });

export const handler = async (event: APIGatewayProxyEvent, context: Context) => {
  logger.addContext(context);
  tracer.getSegment();
  metrics.addMetric("OrdersProcessed", MetricUnit.Count, 1);
  logger.info("Processando requisição", { orderId: event.pathParameters?.id });
  return processOrder(event);
};
```

- Usar `logger.addContext(context)` no início do handler para injetar request_id
- Usar `tracer.captureAWSv3Client(client)` para instrumentar clientes SDK v3
- Usar `middy` middleware para integração declarativa com Powertools

## Padrões AWS SDK v3

- Usar imports modulares — nunca importar o SDK inteiro:

```typescript
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand, GetCommand } from "@aws-sdk/lib-dynamodb";
```

- Criar clientes fora do handler e reutilizar entre invocações
- Tratar exceções específicas do serviço:

```typescript
import { ConditionalCheckFailedException } from "@aws-sdk/client-dynamodb";

try {
  await docClient.send(new PutCommand({ TableName: tableName, Item: item }));
} catch (error) {
  if (error instanceof ConditionalCheckFailedException) {
    logger.warn("Item já existe", { itemId: item.id });
  } else {
    throw error;
  }
}
```

- Configurar timeouts e retries explícitos:

```typescript
const client = new DynamoDBClient({
  requestHandler: { requestTimeout: 5000 },
  maxAttempts: 3,
});
```

- Usar paginadores para listagens: `paginateListObjectsV2(config, params)`

## Serviços AWS — Padrões de Uso

### DynamoDB
- Usar `DynamoDBDocumentClient` para marshalling automático de tipos
- Usar `PutCommand`, `GetCommand`, `QueryCommand`, `UpdateCommand`
- Usar `ConditionExpression` para operações idempotentes
- Usar `BatchWriteCommand` para operações em lote (máximo 25 itens)
- Projetar chaves de acesso (PK/SK) com base nos padrões de consulta

### SQS
- Usar `SendMessageCommand` com `MessageGroupId` para FIFO
- Configurar `VisibilityTimeout` adequado ao tempo de processamento
- Sempre configurar DLQ para mensagens que falham repetidamente
- Usar `SendMessageBatchCommand` para envio em lote (máximo 10 mensagens)

### SNS
- Usar `PublishCommand` com `MessageAttributes` para filtragem por assinatura
- Preferir `MessageStructure: "json"` para payloads multi-protocolo

### EventBridge
- Usar `PutEventsCommand` do `@aws-sdk/client-eventbridge` com `Source`, `DetailType` e `Detail`
- Tipar eventos com interfaces TypeScript para validação em compile-time
- Filtrar com `EventPattern` específicos — evitar patterns genéricos

### Step Functions
- Usar `StartExecutionCommand` do `@aws-sdk/client-sfn` para iniciar execuções
- `SendTaskSuccessCommand`/`SendTaskFailureCommand` para callbacks com task tokens
- Tipar payloads entre estados com interfaces — manter payloads mínimos

### S3
- Usar `GetObjectCommand`/`PutObjectCommand` com streams para arquivos grandes
- Gerar presigned URLs: `getSignedUrl(client, command, { expiresIn })`

### API Gateway
- Usar tipos de evento corretos: `APIGatewayProxyEvent` (REST) ou `APIGatewayProxyEventV2` (HTTP API)
- Validar entrada com Zod antes de processar
- Retornar headers CORS quando necessário

## TypeScript — Interfaces e Validação

- Interfaces obrigatórias para todos os modelos de dados
- Usar `interface` para contratos de dados e `type` para unions/intersections
- Usar `Zod` para validação runtime de entrada:

```typescript
import { z } from "zod";

const OrderRequestSchema = z.object({
  orderId: z.string().min(1),
  items: z.array(z.string()),
  total: z.number().positive(),
});

type OrderRequest = z.infer<typeof OrderRequestSchema>;

const parseOrder = (body: string): OrderRequest => {
  return OrderRequestSchema.parse(JSON.parse(body));
};
```

- Tipar retornos de funções explicitamente — evitar `any`
- Usar `unknown` em vez de `any` para dados não tipados e fazer narrowing
- Usar `as const` para objetos literais imutáveis
- Habilitar `strict: true` no `tsconfig.json`

## Padrões de Testes — Jest/Vitest

- Organizar testes em `tests/` ou co-localizados com `*.test.ts`
- Usar `describe`/`it` para agrupamento e nomenclatura descritiva
- Padrão Arrange-Act-Assert em cada teste
- Usar `aws-sdk-client-mock` para mock de serviços AWS SDK v3:

```typescript
import { mockClient } from "aws-sdk-client-mock";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";

const ddbMock = mockClient(DynamoDBDocumentClient);

beforeEach(() => { ddbMock.reset(); });

it("should return item from DynamoDB", async () => {
  ddbMock.on(GetCommand).resolves({ Item: { id: "123", name: "Test" } });
  const result = await handler(mockEvent, mockContext);
  expect(result.statusCode).toBe(200);
});
```

- Usar `vi.mock` (Vitest) ou `jest.mock` para isolar dependências
- Testar cenários de erro (exceções, timeouts, respostas inválidas)
- Manter testes rápidos — evitar chamadas reais a serviços AWS
- Usar `beforeEach` para resetar mocks entre testes
