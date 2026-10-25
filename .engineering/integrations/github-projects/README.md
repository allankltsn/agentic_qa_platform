# GitHub Projects

Gerenciador de projetos do workflow (contrato em `core/workflow/github-projects.md`). Um único Project
(do usuário ou da organização) reúne as issues de todos os repositórios do produto.

## Configuração (uma vez)

Pré-requisito: GitHub CLI autenticado com os escopos `project` e `repo`
(`gh auth refresh -s project,repo`). O script não usa nem grava tokens.

```bash
# cria o Project com os campos do contrato
bash setup-project.sh <owner> "<título do project>"
# cria os labels padrão em cada repositório que terá issues
bash setup-labels.sh <owner>/<repo>
```

Depois, na interface do Project (o CLI não cobre estes itens):

1. **Workflows** (menu `⋯` → *Workflows*): desative *Item closed*, *Pull request merged*,
   *Item reopened* e *Auto-close issue*. O Status só muda pelas regras de autoridade do contrato.
   *Item added to project* pode ficar ativo definindo Status = `open`.
2. **Status**: confira que existem só as nove opções do contrato (o script substitui Todo/In Progress/Done).
   O script também cria `Type` (epic, story, task, bug, spike) e `Estimate` (número) para histórias.
3. **Views** sugeridas:
   - *Board* agrupado por Status (o quadro Kanban);
   - *Table* com Status, Priority, Agent, Sprint, Due date;
   - *Board* por Sprint, se usar iterações.
4. **Sprint**: o campo de iteração é criado pela interface (*+ New field* → *Iteration*), com a duração
   da sprint do time.
5. **Visibilidade**: mantenha o Project privado se algum repositório vinculado for privado.

## Histórias e épicos

Escreva histórias com `core/templates/user-story.md` (ação `/story`): narrativa, regras de negócio,
critérios Given/When/Then, fluxo e estados, requisitos não funcionais, ativos e links, metadados,
Definition of Ready e Definition of Done. Épico → história → tarefa são sub-issues encadeadas.
Em produtos com vários repositórios, histórias ficam no hub e tarefas no repositório que muda.

## Uso pelos agentes

- Criar issue: `gh issue create -R <owner>/<repo> -t "[task-N-impl] <tarefa>" -F issue.md -l role:implementer,task-N`
- Vincular ao Project: `gh project item-add <número> --owner <owner> --url <url da issue>`
- Mudar Status/campos: `gh project item-edit` (IDs via `gh project field-list <número> --owner <owner> --format json`)
- Sub-issues: pela interface ou pelas ferramentas do GitHub MCP/API que suportam sub-issues.
- Log de eventos: comentários `LOG <TIPO> | ...` na issue pai.

Sem acesso de escrita ao board, o agente devolve a atualização completa ao principal (ver contrato).
Configuração e uso por CLI não comprovam o comportamento visual do board nem as automações desligadas;
verifique na interface.
