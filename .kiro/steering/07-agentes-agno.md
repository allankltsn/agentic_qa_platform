---
inclusion: manual
---

# Agentes de IA — Framework Agno

Padrões para desenvolvimento de agentes de IA com o framework Agno. Para padrões de Bedrock, consulte #[[file:.kiro/steering/06-bedrock-genai.md]]. Para padrões gerais de Python, consulte #[[file:.kiro/steering/03-sam-python.md]].

## Arquitetura de Agentes (Agent, Team, Workflow)

- `Agent` é a unidade básica — encapsula modelo, ferramentas, instruções e memória
- Criar agentes com responsabilidade única e instruções claras:

```python
from agno.agent import Agent
from agno.models.aws import BedrockChat

agent = Agent(
    name="Analista Financeiro",
    model=BedrockChat(id="anthropic.claude-3-sonnet-20240229-v1:0"),
    instructions=["Analise dados financeiros com base em fatos."],
    markdown=True,
)
```

- `Team` orquestra múltiplos agentes com estratégia: `route`, `coordinate`, `collaborate`
- `Workflow` define fluxos multi-etapa com controle explícito de estado
- Preferir `Team` para tarefas paralelas; `Workflow` para pipelines sequenciais

## Definição de Ferramentas (Tools e Toolkits)

- Usar docstrings claras — o modelo usa a descrição para decidir quando invocar

```python
from agno.tools import tool, Toolkit

@tool
def buscar_cliente(cliente_id: str) -> str:
    """Busca dados de um cliente pelo ID no banco de dados."""
    return json.dumps(cliente)

class CrmToolkit(Toolkit):  # Agrupar ferramentas com estado compartilhado
    def __init__(self, table_name: str):
        super().__init__(name="crm")
        self.register(self.buscar_cliente)
```

- Registrar via `tools=[buscar_cliente]` ou `tools=[CrmToolkit(table)]`
- Validar entrada/saída das ferramentas — nunca confiar em dados brutos do modelo
- Limitar ferramentas por agente (máximo 10-15) para evitar confusão do modelo

## Orquestração Multi-Agente

- Usar `Team` com `mode="route"` para delegar ao agente mais adequado:

```python
from agno.team import Team

team = Team(
    name="Suporte",
    mode="route",
    members=[agente_vendas, agente_suporte, agente_financeiro],
    model=BedrockChat(id="anthropic.claude-3-sonnet-20240229-v1:0"),
)
```

- `mode="coordinate"` — líder sintetiza respostas de múltiplos agentes
- `mode="collaborate"` — discussão iterativa entre agentes até consenso
- Cada membro deve ter `name` e `role` descritivos para o roteador
- Usar modelos menores (Haiku) para roteamento; maiores (Sonnet) para raciocínio

## Gerenciamento de Memória de Conversação

- Configurar `AgnoMemory` com backend persistente (DynamoDB, PostgreSQL):

```python
from agno.memory import AgnoMemory
from agno.storage.dynamodb import DynamoDbStorage

storage = DynamoDbStorage(table_name="agent_sessions", region_name="us-east-1")
agent = Agent(
    model=BedrockChat(id="anthropic.claude-3-sonnet-20240229-v1:0"),
    memory=AgnoMemory(db=storage),
    add_history_to_messages=True,
    num_history_responses=10,
)
agent.run("Olá!", session_id="user-123-session-1")
```

- Usar `session_id` para isolar conversas por usuário/sessão
- Limitar `num_history_responses` (5-10) para controlar consumo de tokens
- Implementar TTL no storage para limpeza automática de sessões antigas
- Nunca armazenar dados sensíveis (PII, credenciais) na memória sem criptografia

## Integração com AWS Bedrock

- Usar `BedrockChat` como provider de modelo:

```python
model = BedrockChat(
    id="anthropic.claude-3-sonnet-20240229-v1:0",
    aws_region="us-east-1", temperature=0.3, max_tokens=1024,
)
```

- Especificar `aws_region` explicitamente — não depender de variável de ambiente
- Configurar `temperature` e `max_tokens` para controle de custo e qualidade
- Para cross-region inference, usar profile ARN do modelo

## Tratamento de Erros de LLM

- Tratar `ThrottlingException`, `ModelTimeoutException` e `ValidationException` separadamente
- Capturar `ClientError` e inspecionar `e.response["Error"]["Code"]` para decisão de retry vs falha

```python
try:
    response = agent.run(user_input)
except ClientError as e:
    if e.response["Error"]["Code"] in ("ThrottlingException", "ModelTimeoutException"):
        logger.warning("Erro transitório", extra={"code": e.response["Error"]["Code"]})
    raise
```

- Nunca expor mensagens de erro do modelo ao usuário final
- Logar contexto: nome do agente, model_id, session_id
- Implementar circuit breaker para falhas em cascata em Teams

## Estratégias de Retry

- Configurar retry adaptativo no cliente boto3 subjacente ao `BedrockChat`:

```python
from botocore.config import Config

model = BedrockChat(
    id="anthropic.claude-3-sonnet-20240229-v1:0",
    aws_client_config=Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120),
)
```

- `mode: "adaptive"` aplica backoff exponencial com jitter automático
- `max_attempts` entre 3-5 para balancear resiliência e latência
- Para ferramentas com APIs externas, usar `tenacity` com backoff exponencial:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def chamar_api_externa(payload: dict) -> dict:
    """Chama API externa usada como tool do agente Agno."""
    resp = requests.post(API_URL, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()
```

- Em tools do Agno, não aplicar retry em erros 4xx — restringir a falhas transitórias (5xx, throttling)
- Acompanhar taxa de retries com `Metrics` do Powertools para identificar degradação em tools
