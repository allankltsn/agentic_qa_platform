#!/usr/bin/env bash
#
# setup.sh — Developer_Script de setup (Requisito 6.1).
#
# Instala as dependencias do projeto e prepara o ambiente isolado via uv
# (`uv sync`). Opcionalmente cria um `.env` a partir de `.env.example` quando
# ausente (nao-destrutivo). Encerra com exit code 0 no sucesso.
#
# Falha rapida: verifica as dependencias de sistema ANTES de qualquer trabalho
# e encerra com exit code != 0 e uma mensagem que nomeia a dependencia ausente,
# sem aplicar mudancas parciais (Requisitos 6.5, 6.6).
#
# Uso:
#   bash scripts/setup.sh

set -euo pipefail

# --- raiz do projeto: diretorio que contem pyproject.toml/template.yaml ------
# Resolve independentemente de onde o script for invocado.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- helper: falha com mensagem clara e exit code != 0 -----------------------
fail() {
  echo "Erro (setup.sh): $*" >&2
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

# --- 1) instalar deps + preparar ambiente isolado ----------------------------
echo "==> Sincronizando dependencias e ambiente isolado (uv sync)"
uv sync || fail "'uv sync' falhou ao instalar as dependencias/preparar o ambiente."

# --- 2) criar .env a partir do exemplo (nao-destrutivo) ----------------------
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  echo "==> .env ja existe, preservado."
elif [[ -f "${PROJECT_ROOT}/.env.example" ]]; then
  cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env" \
    || fail "falha ao copiar .env.example para .env."
  echo "==> .env criado a partir de .env.example (ajuste os valores conforme necessario)."
else
  echo "==> Aviso: .env.example nao encontrado; pulei a criacao do .env." >&2
fi

echo "==> Setup concluido com sucesso."
