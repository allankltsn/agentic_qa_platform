---
inclusion: manual
---

# Agentes de IA — Framework Strands Agents

Padrões para desenvolvimento de agentes de IA com o framework Strands Agents da AWS. Para padrões de Bedrock, consulte #[[file:.kiro/steering/06-bedrock-genai.md]]. Para padrões gerais de Python, consulte #[[file:.kiro/steering/03-sam-python.md]].

## Arquitetura Strands (Agent, Tool, Model)

- `Agent` é o componente central — combina modelo, ferramentas e system prompt em um loop autônomo
- `Model` abstrai o provedor de LLM — usar `BedrockModel` para integração nativa com AWS
- `Tool` define capacidades que o agente pode invocar durante o raciocínio

```python
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
agent = Agent(
    model=model,
    system_prompt="Você é um assistente de análise de dados. Responda com base em fatos.",
    tools=[buscar_dados, gerar_relatorio],
)
response = agent("Analise as vendas do último trimestre")
```

- O agent loop executa: raciocínio → chamada de tool → resposta (automático)
- Preferir system prompts curtos e objetivos

## Definição de Ferramentas Python

- Usar decorator `@tool` para transformar funções Python em ferramentas do agente
- Docstrings são obrigatórias — o modelo usa a descrição para decidir quando invocar

```python
from strands.types.tools import tool

@tool
def consultar_pedido(pedido_id: str) -> str:
    """Consulta detalhes de um pedido pelo ID no banco de dados."""
    item = table.get_item(Key={"id": pedido_id}).get("Item")
    return json.dumps(item) if item else "Pedido não encontrado"
```

- Type hints obrigatórios nos parâmetros — Strands usa para gerar o schema da tool
- Retornar sempre `str` — serializar objetos complexos com `json.dumps`
- Validar entrada dentro da ferramenta — nunca confiar em dados brutos do modelo
- Limitar ferramentas por agente (máximo 10-15) para evitar confusão do modelo

## Integração Nativa com AWS Bedrock

- Usar `BedrockModel` como provider padrão — integração nativa sem configuração extra:

```python
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region_name="us-east-1", max_tokens=1024, temperature=0.3,
)
```

- Especificar `region_name` explicitamente — não depender de variável de ambiente
- Strands usa streaming por padrão via Bedrock Converse API
- Para modelos cross-region, usar o ARN completo do modelo em `model_id`

## Orquestração de Agentes

- Compor agentes encadeando chamadas ou usando um agente orquestrador:

```python
agente_pesquisa = Agent(model=model, tools=[buscar_web], system_prompt="Pesquise informações.")
agente_redator = Agent(model=model, tools=[formatar_texto], system_prompt="Redija relatórios.")

dados = agente_pesquisa("Pesquise tendências de mercado em 2024")
relatorio = agente_redator(f"Redija um relatório com base em: {dados}")
```

- Para fluxos complexos, usar tools que delegam a sub-agentes:

```python
@tool
def delegar_pesquisa(query: str) -> str:
    """Delega pesquisa ao agente especializado."""
    return str(agente_pesquisa(query))
```

- Usar modelos menores (Haiku) para tarefas simples; maiores (Sonnet) para raciocínio
- Passar contexto mínimo entre agentes — evitar payloads grandes

## Gerenciamento de Memória de Conversação

- Strands mantém histórico de mensagens automaticamente no objeto `Agent`
- Para persistência entre sessões, salvar e restaurar `agent.messages`:

```python
# Salvar conversa em DynamoDB
table.put_item(Item={"session_id": sid, "messages": json.dumps(agent.messages), "ttl": ttl})

# Restaurar em nova sessão
data = table.get_item(Key={"session_id": sid}).get("Item", {})
agent = Agent(model=model, tools=tools, messages=json.loads(data.get("messages", "[]")))
```

- Limitar histórico (últimas 10-20 mensagens) para controlar consumo de tokens
- Implementar TTL no storage para limpeza automática de sessões antigas
- Nunca armazenar dados sensíveis (PII, credenciais) no histórico sem criptografia

## Tratamento de Erros de LLM

- Capturar exceções do Bedrock ao executar o agente:

```python
from botocore.exceptions import ClientError

try:
    response = agent(user_input)
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code in ("ThrottlingException", "ModelTimeoutException"):
        logger.warning("Erro transitório", extra={"code": code})
    elif code == "ValidationException":
        logger.error("Payload inválido", extra={"input": user_input[:100]})
    raise
```

- Nunca expor mensagens de erro do modelo ao usuário final
- Logar contexto: model_id, tamanho do input, session_id
- Implementar fallback para modelo alternativo em caso de indisponibilidade

## Estratégias de Retry

- Configurar retry no `BedrockModel` via `boto_client_config`:

```python
from botocore.config import Config

model = BedrockModel(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    boto_client_config=Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120),
)
```

- Strands usa `mode: "adaptive"` para backoff exponencial com jitter automático no boto3
- Configurar `max_attempts` entre 3-5 — equilibra resiliência e latência do agente
- Para ferramentas com APIs externas, usar `tenacity`:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import ConnectionError, Timeout

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception_type((ConnectionError, Timeout)),
)
def chamar_servico_externo(payload: dict) -> dict:
    """Chama serviço externo usado como tool do Strands Agent."""
    return requests.post(SERVICE_URL, json=payload, timeout=15).json()
```

- Em tools do Strands, restringir retry a erros de rede e timeout — nunca em 4xx de validação
- Emitir métricas de retry por tool para visibilidade de degradação em serviços downstream
