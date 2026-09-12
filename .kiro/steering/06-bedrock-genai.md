---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# IA Generativa — AWS Bedrock

Padrões para desenvolvimento de soluções de IA Generativa com AWS Bedrock. Para padrões gerais de Python/Lambda, consulte #[[file:.kiro/steering/03-sam-python.md]]. Para padrões gerais de código, consulte #[[file:.kiro/steering/01-padroes-gerais.md]].

## API Bedrock — Invocação de Modelos

- Preferir `converse` API sobre `invoke_model` — interface unificada entre modelos
- Usar `invoke_model` apenas quando precisar de parâmetros específicos do provedor
- Criar cliente `bedrock-runtime` fora do handler (connection reuse)

```python
bedrock = boto3.client("bedrock-runtime")

# Converse API (recomendado)
response = bedrock.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7, "topP": 0.9},
)
output_text = response["output"]["message"]["content"][0]["text"]
```

- Para respostas longas, usar streaming com `converse_stream`:

```python
response = bedrock.converse_stream(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    inferenceConfig={"maxTokens": 2048},
)
for event in response["stream"]:
    if "contentBlockDelta" in event:
        chunk = event["contentBlockDelta"]["delta"].get("text", "")
        yield chunk
```

- Sempre especificar `modelId` completo com versão (ex: `anthropic.claude-3-sonnet-20240229-v1:0`)

## Tratamento de Erros Bedrock

- Tratar `ThrottlingException` com retry exponencial e jitter
- Tratar `ModelTimeoutException` com timeout adequado ao modelo
- Tratar `ValidationException` para payloads inválidos
- Tratar `ModelNotReadyException` em modelos provisionados

```python
bedrock_config = Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120)
bedrock = boto3.client("bedrock-runtime", config=bedrock_config)

try:
    response = bedrock.converse(modelId=model_id, messages=messages)
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "ThrottlingException":
        logger.warning("Throttling do Bedrock")
        raise  # botocore retry cuida automaticamente
    elif code == "ModelTimeoutException":
        logger.error("Timeout do modelo", extra={"model_id": model_id})
        raise
    elif code == "ValidationException":
        raise ValueError(f"Payload inválido para o modelo: {e}")
    else:
        raise
```

- Configurar `read_timeout` adequado: 60-120s para modelos grandes, 30s para modelos leves
- Usar `mode: "adaptive"` no retry config para backoff inteligente com Bedrock

## Engenharia de Prompts

- Estruturar system prompts com papel, contexto e restrições claras
- Separar system prompt do user prompt — usar campo `system` na Converse API

```python
response = bedrock.converse(
    modelId=model_id,
    system=[{"text": "Você é um assistente especializado em análise financeira. "
                     "Responda apenas com base nos dados fornecidos. "
                     "Se não souber, diga que não tem informação suficiente."}],
    messages=[{"role": "user", "content": [{"text": user_query}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.3},
)
```

- Usar few-shot examples para tarefas de classificação ou extração:

```python
messages = [
    {"role": "user", "content": [{"text": "Classifique: 'O produto chegou quebrado'"}]},
    {"role": "assistant", "content": [{"text": "Categoria: Reclamação"}]},
    {"role": "user", "content": [{"text": "Classifique: 'Adorei a entrega rápida'"}]},
    {"role": "assistant", "content": [{"text": "Categoria: Elogio"}]},
    {"role": "user", "content": [{"text": f"Classifique: '{input_text}'"}]},
]
```

- Parâmetros de inferência recomendados:
  - `temperature`: 0.0-0.3 para tarefas factuais, 0.5-0.8 para criativas
  - `topP`: 0.9 como padrão — ajustar junto com temperature
  - `maxTokens`: definir limite explícito para controlar custo e latência
- Nunca incluir dados sensíveis (PII, credenciais) diretamente no prompt

## RAG com Bedrock Knowledge Bases

- Usar `bedrock-agent-runtime` para operações de RAG
- Preferir `retrieve_and_generate` para fluxo completo (busca + geração)
- Usar `retrieve` quando precisar controlar a geração separadamente

```python
bedrock_agent = boto3.client("bedrock-agent-runtime")

# Retrieve and Generate (fluxo completo)
response = bedrock_agent.retrieve_and_generate(
    input={"text": user_query},
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "knowledgeBaseId": kb_id,
            "modelArn": f"arn:aws:bedrock:{region}::foundation-model/{model_id}",
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {"numberOfResults": 5}
            },
        },
    },
)
answer = response["output"]["text"]
citations = response.get("citations", [])
```

- Sempre processar e exibir `citations` para rastreabilidade das fontes
- Configurar `numberOfResults` adequado: 3-5 para respostas focadas, 5-10 para análises amplas
- Usar `retrieve` + `converse` para controle fino do prompt com contexto recuperado

## Guardrails e Filtragem de Conteúdo

- Configurar Bedrock Guardrails para filtragem de conteúdo em produção
- Aplicar guardrails via `guardrailConfig` na Converse API:

```python
response = bedrock.converse(
    modelId=model_id,
    messages=messages,
    guardrailConfig={
        "guardrailIdentifier": guardrail_id,
        "guardrailVersion": "DRAFT",  # ou versão específica em prod
    },
)
# Verificar se guardrail interveio
if response.get("stopReason") == "guardrail_intervened":
    logger.warning("Guardrail ativado", extra={"trace": response.get("trace")})
```

- Configurar filtros de conteúdo: hate, insults, sexual, violence, misconduct
- Habilitar PII detection para redação automática de dados sensíveis
- Definir denied topics para restringir escopo de respostas do modelo
- Usar versão fixa de guardrail em produção — `DRAFT` apenas em desenvolvimento
- Logar ativações de guardrail para monitoramento e ajuste de políticas

## Segurança IAM para Bedrock

- Restringir acesso a modelos específicos — nunca usar `bedrock:*`

```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
  "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-*"
}
```

- Para Converse API, adicionar `bedrock:Converse` e `bedrock:ConverseStream`
- Para Knowledge Bases, adicionar `bedrock:Retrieve` e `bedrock:RetrieveAndGenerate`
- Habilitar logging de invocações via CloudWatch para auditoria:
  - Configurar model invocation logging no console Bedrock
  - Logar input/output para debugging (excluir em produção se contiver PII)
- Usar tags de custo em invocações para rastreamento de gastos por projeto
- Monitorar métricas: `InvocationCount`, `InvocationLatency`, `ThrottledCount` via CloudWatch
