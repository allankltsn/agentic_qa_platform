---
inclusion: manual
---

# Agentes de IA — LangChain e LangGraph

Padrões para desenvolvimento de agentes de IA com LangChain e LangGraph. Para padrões de Bedrock, consulte #[[file:.kiro/steering/06-bedrock-genai.md]]. Para padrões gerais de Python, consulte #[[file:.kiro/steering/03-sam-python.md]].

## LangChain — Chains e LCEL

- Usar LCEL (LangChain Expression Language) para compor chains via operador `|`:

```python
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatBedrock(model_id="anthropic.claude-3-sonnet-20240229-v1:0", region_name="us-east-1")
prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente especializado em {dominio}."), ("human", "{pergunta}"),
])
chain = prompt | llm | StrOutputParser()
```

- Preferir `ChatPromptTemplate` sobre strings brutas para prompts tipados
- Usar `StrOutputParser` ou `JsonOutputParser` para parsing estruturado

## LangChain — Agents e Tools

- Usar `create_tool_calling_agent` para agentes com tool calling nativo:

```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool

@tool
def buscar_cliente(cliente_id: str) -> str:
    """Busca informações de um cliente pelo ID no sistema CRM."""
    return json.dumps(get_cliente(cliente_id))

agent = create_tool_calling_agent(llm, tools=[buscar_cliente], prompt=prompt)
executor = AgentExecutor(agent=agent, tools=[buscar_cliente], verbose=False)
```

- Docstrings obrigatórias em tools — o modelo usa para decidir quando invocar
- Validar entrada/saída das tools — nunca confiar em dados brutos do modelo
- Limitar tools por agente (máximo 10-15); usar `verbose=False` em produção

## LangChain — Retrievers e RAG

- Usar `AmazonKnowledgeBasesRetriever` para RAG com Bedrock Knowledge Bases:

```python
from langchain_aws import AmazonKnowledgeBasesRetriever
retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=kb_id, retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 5}},
)
```

- Sempre retornar `source_documents` para rastreabilidade das fontes
- Configurar `numberOfResults`: 3-5 para respostas focadas, 5-10 para análises amplas

## LangGraph — StateGraph, Nodes e Edges

- `StateGraph` define fluxos como grafos de estado tipados:

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    messages: Annotated[list, add]
    next_step: str

def analisar(state: AgentState) -> dict:
    return {"messages": [llm.invoke(state["messages"])], "next_step": "revisar"}

graph = StateGraph(AgentState)
graph.add_node("analisar", analisar)
```

- Definir estado com `TypedDict` — usar `Annotated` com `add` para campos acumuláveis
- Cada node retorna apenas os campos que deseja atualizar
- Manter nodes com responsabilidade única — um node, uma ação

## LangGraph — Conditional Routing

- Usar `add_conditional_edges` para roteamento dinâmico:

```python
def decidir_proximo(state: AgentState) -> str:
    return "revisar" if state["next_step"] == "revisar" else END

graph.add_edge(START, "analisar")
graph.add_conditional_edges("analisar", decidir_proximo, {"revisar": "revisar", END: END})
graph.add_edge("revisar", END)
app = graph.compile()  # Compilar antes de invocar
```

- Funções de roteamento retornam o nome do próximo node ou `END`

## Integração com Bedrock via ChatBedrock

```python
llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0", region_name="us-east-1",
    model_kwargs={"temperature": 0.3, "max_tokens": 1024},
)
```

- Especificar `region_name` explicitamente — não depender de variável de ambiente
- Usar `model_kwargs` para parâmetros de inferência (temperature, max_tokens, top_p)
- Para streaming, usar `llm.stream(messages)` — retorna chunks iteráveis

## Gerenciamento de Memória de Conversação

- Usar `ConversationBufferWindowMemory` para limitar histórico por janela
- Para persistência entre sessões, usar `DynamoDBChatMessageHistory`:

```python
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
history = DynamoDBChatMessageHistory(table_name="chat_sessions", session_id="user-123")
```

- Limitar janela de histórico (`k=5-10`) para controlar consumo de tokens
- Implementar TTL na tabela DynamoDB para limpeza automática de sessões antigas
- Nunca armazenar dados sensíveis (PII, credenciais) no histórico sem criptografia
- Em LangGraph, gerenciar memória via estado do grafo (`messages` no `AgentState`)

## Tratamento de Erros de LLM

- Capturar exceções do Bedrock ao invocar chains e agentes:

```python
from botocore.exceptions import ClientError
try:
    resultado = chain.invoke({"pergunta": user_input})
except ClientError as e:
    error_code = e.response["Error"]["Code"]
    if error_code == "ThrottlingException":
        logger.warning("Throttling na chain", extra={"model": model_id})
    elif error_code == "ModelTimeoutException":
        logger.error("Timeout na chain", extra={"input_len": len(user_input)})
    raise
```

- Não propagar mensagens de erro do LLM ao usuário final — retornar mensagem genérica
- Logar contexto relevante: model_id, tamanho do prompt, chain name, session_id
- Usar `chain.with_fallbacks([chain_alternativa])` para fallback automático

## Estratégias de Retry

- Configurar retry no `ChatBedrock` via `config` do boto3:

```python
from botocore.config import Config
llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    config=Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120),
)
```

- LangChain usa `mode: "adaptive"` no boto3 para backoff com jitter automático
- Definir `max_attempts` entre 3-5 — equilibra resiliência e tempo de resposta da chain
- Usar `chain.with_retry(stop_after_attempt=3)` para retry em nível de chain
- Em chains LangChain, não aplicar retry em erros 4xx — limitar a falhas transitórias (5xx, throttling)
- Rastrear taxa de retries com callbacks customizados do LangChain para detectar degradação
