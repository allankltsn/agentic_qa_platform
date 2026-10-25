#!/usr/bin/env bash
# Cria os labels padrão do contrato num repositório. Idempotente (--force atualiza os existentes).
# Uso: bash setup-labels.sh <owner>/<repo>
set -euo pipefail
REPO="${1:?uso: setup-labels.sh <owner>/<repo>}"
command -v gh >/dev/null || { echo "gh não encontrado" >&2; exit 1; }

label() { gh label create "$1" -R "$REPO" --color "$2" --description "$3" --force >/dev/null && echo "  $1"; }

echo "Labels em $REPO:"
for role in architect backend python aws hosting qa security kubernetes docker cicd devsecops-infra \
            finops sre cloud ingress orchestration deployment reviewer implementer principal             product-owner ux-researcher ux-designer ui-designer brand-strategist marketing             frontend-senior privacy-compliance lay-user scribe; do
  label "role:$role" "0e8a16" "Função responsável pela issue"
done
for type in epic story bug spike; do
  label "type:$type" "5319e7" "Tipo do item (campo Type do Project)"
done
for tier in deep standard light; do
  label "tier:$tier" "bfdadc" "Camada de modelo usada (policies/models.md)"
done
label checkpoint "fbca04" "Checkpoint de capacidade de uma tarefa"
label retroativo "c5def5" "Registro retrospectivo explícito"
label abandonado "b60205" "Trabalho abandonado (fechar como not planned)"
echo "Labels task-N são criados por tarefa: gh label create task-<N> -R $REPO"
