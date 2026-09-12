---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Backend Serverless — AWS SAM com Python

Padrões para desenvolvimento de funções Lambda com AWS SAM e Python. Para convenções gerais de código, consulte #[[file:.kiro/steering/01-padroes-gerais.md]]. Para configuração de infraestrutura SAM, consulte #[[file:.kiro/steering/05-sam-templates.md]].

## Estrutura de Handler Lambda

- Assinatura padrão: `def handler(event: dict, context: LambdaContext) -> dict`
- Inicializar clientes SDK e recursos **fora** do handler (connection reuse)
- Separar lógica de negócio do handler — handler apenas orquestra
- Retornar resposta no formato API Gateway quando aplicável:

```python
from aws_lambda_powertools.utilities.typing import LambdaContext

# Clientes fora do handler (connection reuse)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def handler(event: dict, context: LambdaContext) -> dict:
    try:
        result = process_business_logic(event)
        return {"statusCode": 200, "body": json.dumps(result)}
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
    except Exception:
        logger.exception("Erro inesperado")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
```

- Usar variáveis de ambiente para configuração (nomes de tabelas, filas, buckets)
- Nunca retornar stack traces ou detalhes internos em respostas de erro

## AWS Lambda Powertools

- Usar `Logger` para logging estruturado JSON com correlation_id automático
- Usar `Tracer` para instrumentação X-Ray automática
- Usar `Metrics` para métricas customizadas via CloudWatch EMF
- Usar `event_handler` para roteamento de APIs (REST e GraphQL)

```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Processando requisição", extra={"order_id": event.get("order_id")})
    metrics.add_metric(name="OrdersProcessed", unit=MetricUnit.Count, value=1)
    return process(event)
```

- Usar `@tracer.capture_method` em funções auxiliares para traces granulares
- Usar `Validator` com JSON Schema ou `Parser` com Pydantic para validação de eventos

## Padrões SDK boto3

- Preferir `boto3.resource` para operações de alto nível (DynamoDB, S3)
- Usar `boto3.client` para operações de baixo nível ou serviços sem resource
- Sempre tratar exceções específicas do serviço:

```python
from botocore.exceptions import ClientError

try:
    table.put_item(Item=item)
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        logger.warning("Item já existe", extra={"item_id": item["id"]})
    else:
        raise
```

- Usar paginadores para listagens: `paginator = client.get_paginator("list_objects_v2")`
- Configurar timeouts explícitos via `Config`:

```python
from botocore.config import Config

config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 3, "mode": "adaptive"})
client = boto3.client("sqs", config=config)
```

## Serviços AWS — Padrões de Uso

### DynamoDB
- Usar `Table.put_item`, `get_item`, `query`, `update_item` via resource
- Usar `ConditionExpression` para operações idempotentes
- Usar `BatchWriteItem` para operações em lote (máximo 25 itens)
- Projetar chaves de acesso (PK/SK) com base nos padrões de consulta

### SQS
- Usar `send_message` com `MessageGroupId` para FIFO
- Configurar `VisibilityTimeout` adequado ao tempo de processamento
- Sempre configurar DLQ para mensagens que falham repetidamente
- Usar `send_message_batch` para envio em lote (máximo 10 mensagens)

### SNS
- Usar `publish` com `MessageAttributes` para filtragem por assinatura
- Preferir `MessageStructure: "json"` para payloads multi-protocolo

### EventBridge
- Usar `put_events` com `Source`, `DetailType` e `Detail` bem definidos
- Definir schemas de eventos para documentação e validação
- Usar `EventPattern` específicos para filtragem eficiente

### Step Functions
- Usar SDK para `start_execution` e `send_task_success`/`send_task_failure`
- Passar payloads mínimos entre estados — referenciar dados via chave
- Usar callbacks (task tokens) para integrações assíncronas

### S3
- Usar `upload_fileobj`/`download_fileobj` para streaming de arquivos grandes
- Gerar presigned URLs para acesso temporário: `client.generate_presigned_url`
- Configurar lifecycle rules para dados temporários

### API Gateway
- Validar entrada com JSON Schema no API Gateway ou Powertools Validator
- Usar `event_handler` do Powertools para roteamento de rotas REST
- Retornar headers CORS quando necessário

## Type Hints e Modelos de Dados

- Type hints obrigatórios em todas as funções públicas
- Usar `dataclasses` para modelos simples de dados internos
- Usar `Pydantic` (BaseModel) para validação de entrada/saída com parsing automático
- Usar `TypedDict` para tipagem de dicionários complexos (ex: eventos Lambda)

```python
from pydantic import BaseModel, Field

class OrderRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    items: list[str]
    total: float = Field(..., gt=0)

def process_order(request: OrderRequest) -> dict:
    # Lógica de negócio com dados validados
    ...
```

- Usar `Optional[T]` para campos que podem ser `None`
- Usar `Literal` para valores enumerados restritos

## Padrões de Testes — pytest

- Organizar testes em `tests/` espelhando a estrutura de `src/`
- Usar `conftest.py` para fixtures compartilhadas (ex: tabela DynamoDB mock)
- Usar `@pytest.fixture` para setup/teardown de recursos
- Usar `@pytest.mark.parametrize` para testar múltiplos cenários
- Nomenclatura: `test_<funcionalidade>_<cenario>_<resultado_esperado>`
- Padrão Arrange-Act-Assert em cada teste
- Usar `moto` para mock de serviços AWS:

```python
import pytest
from moto import mock_aws

@pytest.fixture
def dynamodb_table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="orders",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table
```

- Usar `unittest.mock.patch` para isolar dependências externas
- Testar cenários de erro (exceções, timeouts, respostas inválidas)
- Manter testes rápidos — evitar chamadas reais a serviços AWS
