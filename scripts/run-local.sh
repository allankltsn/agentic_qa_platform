#!/usr/bin/env bash
#
# run-local.sh — Developer_Script de execucao local (Requisito 6.2).
#
# Sobe o QA_Platform_Service localmente via uvicorn, expondo o Health_Endpoint
# (GET /health). Carrega o `.env` se presente (para prover SERVICE_VERSION e
# demais variaveis). SERVICE_VERSION e OBRIGATORIA: o servico falha rapido na
# inicializacao se ela estiver ausente/vazia.
#
# Falha rapida: verifica as dependencias de sistema ANTES de subir o servico e
# encerra com exit code != 0 e uma mensagem que nomeia a dependencia/causa
# ausente, sem aplicar mudancas parciais (Requisitos 6.5, 6.6).
#
# Variaveis de ambiente relevantes (com default):
#   HOST (default 0.0.0.0)   — endereco de bind
#   PORT (default 8000)      — porta HTTP
#   SERVICE_VERSION          — OBRIGATORIA (via .env ou ambiente)
#
# Uso:
#   bash scripts/run-local.sh

set -euo pipefail

# --- raiz do projeto ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- helper: falha com mensagem clara e exit code != 0 -----------------------
fail() {
  echo "Erro (run-local.sh): $*" >&2
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
require_command uv "Instale o uv: https://docs.astral.sh/uv/"

cd "${PROJECT_ROOT}"

# --- carregar .env, se presente ----------------------------------------------
# Exporta as variaveis definidas no .env para o processo do servico.
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  echo "==> Carregando variaveis de ambiente de .env"
  set -a
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/.env"
  set +a
else
  echo "==> Aviso: .env nao encontrado; o ambiente deve prover SERVICE_VERSION." >&2
fi

# --- SERVICE_VERSION e obrigatoria -------------------------------------------
# O servico falha rapido de qualquer forma; validamos aqui para uma mensagem clara.
if [[ -z "${SERVICE_VERSION:-}" ]]; then
  fail "variavel obrigatoria ausente: 'SERVICE_VERSION'. Defina-a no .env ou no ambiente."
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# --- subir o servico ---------------------------------------------------------
echo "==> Iniciando QA_Platform_Service em http://${HOST}:${PORT} (rota: /health)"
exec uv run uvicorn qa_platform.interface.api.main:app --host "${HOST}" --port "${PORT}"
