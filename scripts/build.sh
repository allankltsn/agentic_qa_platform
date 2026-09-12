#!/usr/bin/env bash
#
# build.sh — Developer_Script de build serverless (Requisito 6.3).
#
# Executa o build do artefato implantavel via AWS SAM (`sam build`) a partir do
# template.yaml na raiz do projeto. Encerra com exit code 0 no sucesso.
#
# Falha rapida: verifica as dependencias de sistema ANTES de qualquer trabalho e
# encerra com exit code != 0 e uma mensagem que nomeia a dependencia/causa
# ausente, sem aplicar mudancas parciais (Requisitos 6.5, 6.6).
#
# Uso:
#   bash scripts/build.sh
#   bash scripts/build.sh --use-container   # (args extras sao repassados ao sam)

set -euo pipefail

# --- raiz do projeto ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- helper: falha com mensagem clara e exit code != 0 -----------------------
fail() {
  echo "Erro (build.sh): $*" >&2
  exit 1
}

# --- helper: exige uma dependencia de sistema no PATH ------------------------
require_command() {
  local cmd="$1" hint="${2:-}"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    if [[ -n "${hint}" ]]; then
      fail "dependencia de sistema ausente: '${cmd}' nao encontrada no PATH. ${hint}"
    fi
    fail "dependencia de sistema ausente: '${cmd}' nao encontrada no PATH."
  fi
}

# --- pre-requisitos (checar ANTES de qualquer trabalho) ----------------------
require_command sam "Instale o AWS SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"

cd "${PROJECT_ROOT}"

if [[ ! -f "${PROJECT_ROOT}/template.yaml" ]]; then
  fail "template.yaml nao encontrado na raiz do projeto (${PROJECT_ROOT})."
fi

# --- build do artefato -------------------------------------------------------
echo "==> Construindo o artefato serverless (sam build)"
sam build "$@" || fail "'sam build' falhou ao produzir o artefato implantavel."

echo "==> Build concluido com sucesso."
