#!/usr/bin/env bash
# Cria um GitHub Project com os campos do contrato core/workflow/github-projects.md.
# Uso: bash setup-project.sh <owner> "<título>"
# Requer: gh autenticado com escopos project e repo. Não lê nem grava tokens.
set -euo pipefail

OWNER="${1:?uso: setup-project.sh <owner> \"<título>\"}"
TITLE="${2:?uso: setup-project.sh <owner> \"<título>\"}"
STATUS_OPTIONS="open,pending,in-progress,in-review,rejected,blocked,completed,accepted,closed"

command -v gh >/dev/null || { echo "gh não encontrado" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq não encontrado" >&2; exit 1; }

number=$(gh project create --owner "$OWNER" --title "$TITLE" --format json | jq -r '.number')
echo "Project #$number criado para $OWNER"

# O campo Status padrão (Todo/In Progress/Done) não pode ser apagado; as opções são substituídas via API.
status_id=$(gh project field-list "$number" --owner "$OWNER" --format json \
  | jq -r '.fields[] | select(.name == "Status") | .id')
# Valores fixos (sem entrada do usuário): seguros para montar a mutation em linha.
options=$(echo "$STATUS_OPTIONS" | tr ',' '\n' \
  | sed 's/.*/{name: "&", color: GRAY, description: ""}/' | paste -sd, -)
gh api graphql -f field="$status_id" -f query="
  mutation(\$field: ID!) {
    updateProjectV2Field(input: {fieldId: \$field, singleSelectOptions: [$options]}) {
      projectV2Field { ... on ProjectV2SingleSelectField { id } }
    }
  }" >/dev/null
echo "Status: $STATUS_OPTIONS"

gh project field-create "$number" --owner "$OWNER" --name Priority --data-type SINGLE_SELECT \
  --single-select-options "critical,high,medium,low" >/dev/null
gh project field-create "$number" --owner "$OWNER" --name Type --data-type SINGLE_SELECT   --single-select-options "epic,story,task,bug,spike" >/dev/null
gh project field-create "$number" --owner "$OWNER" --name Estimate --data-type NUMBER >/dev/null
gh project field-create "$number" --owner "$OWNER" --name Agent --data-type TEXT >/dev/null
gh project field-create "$number" --owner "$OWNER" --name "Due date" --data-type DATE >/dev/null
gh project field-create "$number" --owner "$OWNER" --name "Completed at" --data-type DATE >/dev/null
echo "Campos: Priority, Type, Estimate, Agent, Due date, Completed at"

echo
echo "Falta na interface (ver README): desativar os workflows automáticos, criar o campo Sprint (Iteration)"
echo "e as views. Project: $(gh project view "$number" --owner "$OWNER" --format json | jq -r '.url')"
