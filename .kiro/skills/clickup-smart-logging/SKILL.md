---
name: clickup-smart-logging
description: 'Otimiza registro e atualização de informações no ClickUp via MCP. Triggers: "registrar", "logar", "atualizar", "criar tarefa", "time tracking", "clickup".'
allowed-tools: Read, Write, Edit, MCP
---

# ClickUp Smart Logging

Skill para otimizar interações com ClickUp MCP ao registrar e atualizar informações.

## Quando Usar

Esta skill é ativada quando o usuário solicita:
- Registrar ou logar tempo de trabalho
- Criar ou atualizar tarefas no ClickUp
- Adicionar comentários ou notas
- Modificar status, prioridades ou campos
- Qualquer operação de escrita no ClickUp

## Princípios Fundamentais

**Seja Direto e Eficiente**
- Execute ações imediatamente quando tiver informação suficiente
- Minimize perguntas - apenas pergunte o essencial
- Use parâmetros mínimos necessários
- Busque informações uma única vez

**Identifique o Contexto Rapidamente**
- Analise a solicitação para determinar o tipo de ação
- Se tarefa mencionada por nome: use `clickup_search`
- Se tarefa mencionada por ID: use diretamente
- Proceda com a ação assim que possível

---

## Fluxos de Trabalho

<details>
<parameter name="summary">⏱️ Registro de Tempo (Time Tracking)


### Fluxo de Time Tracking

**Identificar tipo de registro:**

1. **Timer em andamento** (palavras-chave: "começar", "iniciar", "estou trabalhando")
   ```
   → Use clickup_start_time_tracking
   ```

2. **Tempo passado** (palavras-chave: "trabalhei", "registrar", "logar X horas")
   ```
   → Use clickup_add_time_entry
   ```

**Processo:**

1. Identifique a tarefa:
   - Por ID (ex: "DEV-123"): use diretamente
   - Por nome: use `clickup_search` primeiro

2. Execute a ação apropriada:
   - Para timer: `clickup_start_time_tracking` (parâmetros mínimos)
   - Para tempo passado: `clickup_add_time_entry` com start + duration

3. Confirme sucesso brevemente

**Parâmetros opcionais** (use apenas se fornecidos):
- description
- tags
- billable

### Exemplos

**Iniciar timer:**
```
Usuário: "começa a contar tempo na tarefa de login"
Ação:
1. clickup_search keywords="login"
2. clickup_start_time_tracking task_id=<resultado>
Resposta: "Timer iniciado para 'Implementação Login' (DEV-123)"
```

**Registrar tempo passado:**
```
Usuário: "registra 2h30m na DEV-456"
Ação:
1. clickup_add_time_entry task_id="DEV-456", start="2025-02-24 14:00", duration="2h 30m"
Resposta: "Registrado 2h30m na tarefa DEV-456"
```

**Parar timer:**
```
Usuário: "para o timer"
Ação:
1. clickup_stop_time_tracking
Resposta: "Timer parado. Total: 1h 45m"
```

</details>

<details>
<summary>✅ Criação de Tarefas</summary>

### Fluxo de Criação

**Informações necessárias:**
- Nome da tarefa (obrigatório)
- Lista onde criar (obrigatório - SEMPRE pergunte se não fornecida)

**Informações opcionais** (use apenas se fornecidas):
- Descrição
- Assignees
- Prioridade
- Datas (due_date, start_date)
- Tags
- Custom fields

**Processo:**

1. Se lista não fornecida: pergunte "Em qual lista devo criar?"
2. Se nome de lista fornecido: use `clickup_get_list` para obter ID
3. Execute `clickup_create_task` com parâmetros mínimos
4. Confirme criação com nome e ID

### Exemplos

**Criação simples:**
```
Usuário: "cria tarefa 'Revisar PR' no Backlog"
Ação:
1. clickup_get_list list_name="Backlog"
2. clickup_create_task name="Revisar PR", list_id=<resultado>
Resposta: "Tarefa 'Revisar PR' criada no Backlog (ID: 123abc)"
```

**Criação com detalhes:**
```
Usuário: "cria tarefa urgente 'Bug no login' na lista Bugs, atribui pra mim"
Ação:
1. clickup_get_list list_name="Bugs"
2. clickup_create_task name="Bug no login", list_id=<resultado>, priority="urgent", assignees=["me"]
Resposta: "Tarefa urgente 'Bug no login' criada e atribuída a você"
```

</details>

<details>
<summary>🔄 Atualização de Tarefas</summary>

### Fluxo de Atualização

**Processo:**

1. Localize a tarefa:
   - Por ID: use diretamente
   - Por nome: use `clickup_search`

2. Execute `clickup_update_task` com APENAS campos que mudam

3. NÃO busque tarefa completa antes (desnecessário)

**Campos atualizáveis:**
- name
- description / markdown_description
- status
- priority
- assignees
- due_date / start_date
- tags
- custom_fields
- task_type

### Exemplos

**Atualizar status:**
```
Usuário: "marca a tarefa de testes como concluída"
Ação:
1. clickup_search keywords="testes"
2. clickup_update_task task_id=<resultado>, status="done"
Resposta: "Tarefa 'Testes unitários' marcada como concluída"
```

**Atualizar múltiplos campos:**
```
Usuário: "muda a prioridade da DEV-789 pra alta e atribui pro João"
Ação:
1. clickup_update_task task_id="DEV-789", priority="high", assignees=["João"]
Resposta: "DEV-789 atualizada: prioridade alta, atribuída ao João"
```

**Adicionar comentário:**
```
Usuário: "adiciona comentário 'Revisado e aprovado' na tarefa DEV-100"
Ação:
1. clickup_create_task_comment task_id="DEV-100", comment_text="Revisado e aprovado"
Resposta: "Comentário adicionado à DEV-100"
```

</details>

---

## Resolução Automática

### Assignees

O MCP ClickUp resolve automaticamente:
- "me" / "eu" / "mim" → usuário atual
- Nomes de usuários → IDs correspondentes
- Emails → IDs correspondentes

**NÃO use** `clickup_resolve_assignees` a menos que precise dos IDs separadamente.

**Uso direto:**
```javascript
assignees: ["me"]
assignees: ["João Silva", "maria@empresa.com"]
```

### Tarefas por Nome

Use `clickup_search` para encontrar tarefas por nome ou palavras-chave:

```javascript
clickup_search(keywords="implementação login")
```

Retorna tarefas correspondentes com IDs para uso posterior.

---

## Tratamento de Erros

### Erros Comuns e Soluções

**"List not found"**
- Pergunte: "Em qual lista devo criar? (nome ou ID)"
- Use `clickup_get_list` se nome fornecido

**"Task not found"**
- Use `clickup_search` com palavras-chave
- Peça ID ou nome mais específico

**"Invalid assignee"**
- Verifique nome/email
- Sugira usar "me" para si mesmo

**"Required field missing"**
- Identifique campo faltante
- Pergunte apenas o necessário

**"Invalid status"**
- Liste status válidos se disponível
- Sugira alternativas comuns (done, in progress, todo)

---

## Padrões de Resposta

### Após Sucesso

Seja conciso e confirme a ação:

✅ **Timer iniciado:** "Timer iniciado para 'Code Review' (DEV-456)"
✅ **Tempo registrado:** "Registrado 2h na 'Implementação Login' (DEV-123)"
✅ **Tarefa criada:** "Tarefa 'Revisar PR' criada no Backlog (ID: abc123)"
✅ **Tarefa atualizada:** "DEV-789 marcada como concluída"
✅ **Comentário adicionado:** "Comentário adicionado à tarefa"

### Após Erro

Explique o problema e sugira solução:

❌ **Lista não encontrada:** "Não encontrei a lista 'Backlog'. Qual lista devo usar? (forneça nome exato ou ID)"
❌ **Tarefa não encontrada:** "Não encontrei tarefa com esse nome. Pode fornecer o ID ou mais detalhes?"
❌ **Campo obrigatório:** "Preciso saber em qual lista criar a tarefa. Qual lista devo usar?"

---

## Checklist de Eficiência

Antes de executar ações, verifique:

- [ ] Tenho informação suficiente para agir?
- [ ] Preciso buscar tarefa por nome? (use `clickup_search`)
- [ ] Estou usando parâmetros mínimos necessários?
- [ ] Posso executar diretamente sem perguntas extras?
- [ ] Vou confirmar sucesso de forma concisa?

---

## Resumo

**Filosofia:** Seja rápido, direto e eficiente. Execute ações imediatamente quando possível, minimize perguntas, use parâmetros mínimos, confirme sucesso brevemente.

**Fluxos principais:**
1. Time tracking → Identifique tipo (timer vs passado) → Execute
2. Criar tarefa → Confirme lista → Execute com mínimos
3. Atualizar → Localize tarefa → Atualize apenas campos necessários

**Lembre-se:** O MCP resolve assignees automaticamente. Use `clickup_search` para encontrar tarefas por nome. Não busque informações desnecessárias.
