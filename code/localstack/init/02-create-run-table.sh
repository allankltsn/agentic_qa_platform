#!/usr/bin/env bash
#
# 02-create-run-table.sh — Provisiona a tabela DynamoDB de histórico de runs no LocalStack.
#
# Este script roda automaticamente quando o LocalStack fica pronto (é montado em
# /etc/localstack/init/ready.d pelo docker-compose). Ele garante a tabela de
# histórico de runs, de onde o DynamoDBRunStateStore persiste/recupera o RunResult
# final (backend durável selecionado por RUN_STORE_BACKEND=dynamodb).
#
# A tabela espelha a definição do SAM (code/template.yaml):
#   - chave de partição: run_id (S)
#   - BillingMode: PAY_PER_REQUEST
# (SSE é padrão gerenciado no LocalStack; não é preciso declarar aqui.)
#
# Requisito central: IDEMPOTÊNCIA (Req 5.2). O LocalStack pode reexecutar os scripts
# de init a cada boot do container, e o volume de dados pode persistir entre
# reinícios. Portanto, este script trata "tabela já existe" como SUCESSO — nunca
# falha por tentar recriar algo que já está lá.
#
# Usa `awslocal`, o wrapper da AWS CLI que já aponta para o endpoint do LocalStack
# e injeta credenciais fake — não é preciso configurar --endpoint-url manualmente.

set -euo pipefail

AWS_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-1}}"
# Nome da tabela de histórico de runs (bate com RUN_TABLE_NAME do .env.example para
# o backend durável em dev). Configurável por env para alinhar com o RUN_TABLE_NAME
# usado pelo serviço; default consistente com o exemplo local.
RUN_TABLE_NAME="${RUN_TABLE_NAME:-qa-platform-run-state}"

echo "[run-table] Iniciando provisionamento da tabela no LocalStack (região=${AWS_REGION})"

# --------------------------------------------------------------------------- #
# Tabela DynamoDB de histórico de runs (idempotente)                          #
# --------------------------------------------------------------------------- #
# Estratégia: describe-table primeiro. Se já existe, não recriamos (recriar
# dispararia ResourceInUseException). Se não existe, criamos com a mesma forma do
# recurso declarado no SAM: PK run_id (S), BillingMode PAY_PER_REQUEST.
echo "[run-table] Verificando tabela '${RUN_TABLE_NAME}'..."
if awslocal dynamodb describe-table \
    --table-name "${RUN_TABLE_NAME}" \
    --region "${AWS_REGION}" >/dev/null 2>&1; then
  echo "[run-table] Tabela '${RUN_TABLE_NAME}' já existe — nada a fazer (idempotente)."
else
  echo "[run-table] Tabela '${RUN_TABLE_NAME}' não existe — criando..."
  awslocal dynamodb create-table \
    --table-name "${RUN_TABLE_NAME}" \
    --attribute-definitions AttributeName=run_id,AttributeType=S \
    --key-schema AttributeName=run_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" >/dev/null
  echo "[run-table] Tabela '${RUN_TABLE_NAME}' criada."
fi

echo "[run-table] Provisionamento da tabela concluído com sucesso."
