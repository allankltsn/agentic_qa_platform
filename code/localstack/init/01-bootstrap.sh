#!/usr/bin/env bash
#
# 01-bootstrap.sh — Provisiona os recursos AWS que a QA Platform espera no LocalStack.
#
# Este script roda automaticamente quando o LocalStack fica pronto (é montado em
# /etc/localstack/init/ready.d pelo docker-compose). Ele garante um segredo no
# Secrets Manager, de onde o Config_Resolver/SecretResolver resolve as chaves no
# pipe env -> Secrets Manager.
#
# Requisito central: IDEMPOTÊNCIA. O LocalStack pode reexecutar os scripts de init
# a cada boot do container, e o volume de dados pode persistir entre reinícios.
# Portanto, este script trata "recurso já existe" como SUCESSO — nunca falha por
# tentar recriar algo que já está lá.
#
# Usa `awslocal`, o wrapper da AWS CLI que já aponta para o endpoint do LocalStack
# e injeta credenciais fake — não é preciso configurar --endpoint-url manualmente.

set -euo pipefail

AWS_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-1}}"
# Nome lógico do segredo JSON (bate com SECRET_NAME do .env.example).
SECRET_NAME="${SECRET_NAME:-qa-platform-secrets}"
# Valor inicial do segredo. Placeholder — NUNCA um segredo real. O valor de
# verdade é injetado no ambiente/deploy; aqui só garantimos que o segredo existe.
SECRET_INITIAL_VALUE="${SECRET_INITIAL_VALUE:-{}}"

echo "[bootstrap] Iniciando provisionamento no LocalStack (região=${AWS_REGION})"

# --------------------------------------------------------------------------- #
# Segredo no Secrets Manager (idempotente)                                    #
# --------------------------------------------------------------------------- #
# Estratégia: describe-secret primeiro. Se já existe, não recriamos (recriar
# dispararia ResourceExistsException). Se não existe, criamos com o placeholder.
echo "[bootstrap] Verificando segredo '${SECRET_NAME}'..."
if awslocal secretsmanager describe-secret \
    --secret-id "${SECRET_NAME}" \
    --region "${AWS_REGION}" >/dev/null 2>&1; then
  echo "[bootstrap] Segredo '${SECRET_NAME}' já existe — nada a fazer (idempotente)."
else
  echo "[bootstrap] Segredo '${SECRET_NAME}' não existe — criando..."
  awslocal secretsmanager create-secret \
    --name "${SECRET_NAME}" \
    --secret-string "${SECRET_INITIAL_VALUE}" \
    --region "${AWS_REGION}" >/dev/null
  echo "[bootstrap] Segredo '${SECRET_NAME}' criado."
fi

echo "[bootstrap] Provisionamento concluído com sucesso."
