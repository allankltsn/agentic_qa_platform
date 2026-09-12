---
inclusion: fileMatch
fileMatchPattern: "**/test_*.py,**/*_test.py,**/*.test.{ts,js},**/*.spec.{ts,js}"
---

# Testes e Qualidade

Padrões avançados de testes para projetos serverless. Para padrões básicos de testes Python (pytest, moto, fixtures), consulte #[[file:.kiro/steering/03-sam-python.md]]. Para padrões básicos de testes Node.js (Jest/Vitest, aws-sdk-client-mock), consulte #[[file:.kiro/steering/04-sam-nodejs.md]].

## Filosofia de Testes

- Nomenclatura descritiva que expressa o comportamento esperado:
  - Python: `test_<funcionalidade>_when_<cenario>_then_<resultado>`
  - Node.js: `describe("<Módulo>") > it("should <comportamento> when <condição>")`
- Padrão **Arrange-Act-Assert** (AAA) em todos os testes:
  - Arrange: preparar dados e dependências
  - Act: executar a ação sendo testada
  - Assert: verificar o resultado esperado
- Alternativa **Given-When-Then** para testes de comportamento:
  - Given: estado inicial / pré-condições
  - When: ação executada
  - Then: resultado esperado
- Um assert lógico por teste — testar uma única responsabilidade
- Testes devem ser independentes — nunca depender da ordem de execução
- Testes devem ser determinísticos — mesmo resultado em qualquer execução

## Cobertura e Priorização

- Cobertura mínima recomendada: 80% para lógica de negócio
- Priorizar testes por impacto:
  1. Lógica de negócio crítica (cálculos, validações, transformações)
  2. Integrações com serviços AWS (DynamoDB, SQS, S3)
  3. Tratamento de erros e edge cases
  4. Handlers Lambda (orquestração)
- Não perseguir 100% de cobertura — focar em código com lógica condicional
- Usar `pytest-cov` (Python) ou `--coverage` (Vitest/Jest) para relatórios
- Configurar thresholds de cobertura no CI para evitar regressão

## Pytest — Padrões Avançados

- Organizar `conftest.py` por escopo:
  - `tests/conftest.py` — fixtures globais (AWS mocks, configuração)
  - `tests/<módulo>/conftest.py` — fixtures específicas do módulo
- Usar escopos de fixture adequados:
  - `scope="function"` (padrão) — isolamento total entre testes
  - `scope="module"` — recursos caros compartilhados no módulo
  - `scope="session"` — recursos compartilhados na sessão (ex: conexão DB)
- Usar `@pytest.mark.parametrize` para cobrir múltiplos cenários sem duplicação:

```python
@pytest.mark.parametrize("status_code,expected", [
    (200, "success"),
    (400, "bad_request"),
    (500, "internal_error"),
])
def test_handle_response_maps_status_correctly(status_code, expected):
    assert map_status(status_code) == expected
```

- Usar markers para categorizar testes:
  - `@pytest.mark.unit` — testes unitários rápidos
  - `@pytest.mark.integration` — testes de integração (mais lentos)
  - `@pytest.mark.slow` — testes que demoram mais de 5s
- Executar por categoria: `pytest -m "unit and not slow"`
- Usar `unittest.mock.patch` como context manager para escopo controlado:

```python
from unittest.mock import patch, MagicMock

def test_handler_calls_service_with_correct_params():
    with patch("src.handlers.process.business_service") as mock_service:
        mock_service.return_value = {"status": "ok"}
        result = handler(mock_event, mock_context)
        mock_service.assert_called_once_with(expected_params)
```

- Preferir `patch.object` sobre `patch` com string para refatoração segura
- Usar `freezegun` ou `time_machine` para testes que dependem de tempo

## Jest/Vitest — Padrões Avançados

- Estruturar testes com `describe` aninhado para contextos:

```typescript
describe("OrderService", () => {
  describe("when order is valid", () => {
    it("should save to DynamoDB", async () => { /* ... */ });
    it("should publish SNS notification", async () => { /* ... */ });
  });
  describe("when order is invalid", () => {
    it("should return 400 with validation errors", async () => { /* ... */ });
  });
});
```

- Usar `beforeEach`/`afterEach` para setup/teardown — nunca `beforeAll` para mocks
- Usar `vi.spyOn` (Vitest) para verificar chamadas sem substituir implementação
- Usar `vi.useFakeTimers()` para testes que dependem de tempo
- Criar factories para objetos de teste complexos:

```typescript
const createMockEvent = (overrides?: Partial<APIGatewayProxyEvent>): APIGatewayProxyEvent => ({
  httpMethod: "POST",
  body: JSON.stringify({ orderId: "123" }),
  ...overrides,
} as APIGatewayProxyEvent);
```

- Usar `toMatchObject` para assertions parciais em objetos grandes
- Usar `toThrow` / `rejects.toThrow` para testar erros assíncronos

## Estratégias de Teste para Serviços AWS

- **Mocking (recomendado para testes unitários)**:
  - Python: `moto` para mock completo de serviços AWS (DynamoDB, S3, SQS, SNS)
  - Node.js: `aws-sdk-client-mock` para mock de comandos SDK v3
  - Vantagens: rápido, sem dependências externas, executa offline
  - Limitação: pode não refletir comportamento real do serviço
- **LocalStack (recomendado para testes de integração)**:
  - Emula serviços AWS localmente via Docker
  - Usar para validar fluxos completos (Lambda → DynamoDB → SQS)
  - Configurar via `docker-compose.yml` com serviços necessários
  - Usar endpoint override: `endpoint_url="http://localhost:4566"` (Python) / `endpoint: "http://localhost:4566"` (Node.js)
- **Test Doubles — quando usar cada tipo**:
  - Stub: retorna dados fixos (ex: mock de `get_item` retornando item)
  - Spy: verifica chamadas sem alterar comportamento
  - Mock: substitui implementação e verifica interações
  - Fake: implementação simplificada (ex: in-memory store)
- Nunca fazer chamadas reais a serviços AWS em testes automatizados
- Usar variáveis de ambiente de teste para configuração (`TABLE_NAME=test-table`)

## Testes de Integração

- Separar testes de integração dos unitários via markers/diretórios:
  - Python: `tests/integration/` com `@pytest.mark.integration`
  - Node.js: `tests/integration/` ou `*.integration.test.ts`
- Setup/teardown de recursos:
  - Criar recursos antes da suite (tabelas, filas, buckets)
  - Limpar dados entre testes para isolamento
  - Destruir recursos após a suite
- Usar fixtures com escopo de sessão para recursos compartilhados:

```python
@pytest.fixture(scope="session")
def localstack_dynamodb():
    client = boto3.client("dynamodb", endpoint_url="http://localhost:4566")
    client.create_table(TableName="test-orders", ...)
    yield client
    client.delete_table(TableName="test-orders")
```

- Garantir isolamento: cada teste deve funcionar independentemente
- Usar IDs únicos por teste para evitar colisão de dados (ex: `f"order-{uuid4()}"`)
- Configurar timeout adequado — testes de integração são mais lentos
- Executar testes de integração no CI com LocalStack via Docker
- Não bloquear PR por falha em testes de integração instáveis — marcar como `@pytest.mark.flaky` e investigar
