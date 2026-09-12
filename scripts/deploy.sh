#!/usr/bin/env bash
#
# deploy.sh — Developer_Script de deploy serverless (Requisito 6.4).
#
# Executa o deploy do artefato via AWS SAM (`sam deploy`), usando o
# samconfig.toml da raiz do projeto. Encerra com exit code 0 no sucesso.
# Argumentos extras sao repassados ao sam (ex.: --guided).
#
# Falha rapida: verifica as dependencias de sistema ANTES de qualquer trabalho e
# encerra com exit code != 0 e uma mensagem que nomeia a dependencia/causa
# ausente, sem aplicar mudancas parciais (Requisitos 6.5, 6.6).
#
# Uso:
#   bash scripts/deploy.sh
#   bash scripts/deploy.sh --guided        # primeiro deploy interativo
#   bash scripts/deploy.sh --no-confirm-changeset

set -euo pipefail

# --- raiz do projeto ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- helper: falha com mensagem clara e exit code != 0 -----------------------
fail() {
  echo "Erro (deploy.sh): $*" >&2
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

# O samconfig.toml e a fonte de configuracao do deploy. Sem ele, oriente o uso
# do modo --guided para gera-lo, em vez de tentar um deploy parcialmente configurado.
CONFIG_FILE="${PROJECT_ROOT}/samconfig.toml"
if [[ ! -f "${CONFIG_FILE}" ]]; then
  fail "samconfig.toml nao encontrado na raiz do projeto. Rode 'bash scripts/deploy.sh --guided' para gera-lo."
fi

# --- deploy ------------------------------------------------------------------
echo "==> Fazendo deploy do artefato serverless (sam deploy)"
sam deploy --config-file "${CONFIG_FILE}" "$@" \
  || fail "'sam deploy' falhou. Verifique credenciais AWS, a regiao e o changeset."

echo "==> Deploy concluido com sucesso."
