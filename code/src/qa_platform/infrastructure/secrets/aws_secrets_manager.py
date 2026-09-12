"""Adapter de segredos do AWS Secrets Manager (import tardio de boto3).

Implementa a porta ``SecretsProvider`` lendo um segredo JSON do AWS Secrets
Manager e resolvendo chaves por nome. O ``import boto3`` é **tardio** (feito
dentro de ``_load``), de modo que este módulo permanece importável e testável
sem o SDK instalado e sem rede — o boto3 só é exigido quando a fonte é de fato
consultada. O nome do segredo e o endpoint são configuráveis por variável de
ambiente (``SECRET_NAME`` / ``AWS_ENDPOINT_URL``). O resultado é cacheado por
processo e valores/segredos nunca são logados (Requisito 7.1).
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional


class AWSSecretsManagerProvider:
    """Lê um segredo JSON do AWS Secrets Manager e resolve chaves por nome.

    Import tardio do boto3: o módulo permanece importável/testável sem o SDK.
    """

    SECRET_NAME_ENV = "SECRET_NAME"
    DEFAULT_SECRET_NAME = "qa-platform-secrets"

    def __init__(self, secret_name: Optional[str] = None) -> None:
        self._secret_name = (
            secret_name
            or os.environ.get(self.SECRET_NAME_ENV)
            or self.DEFAULT_SECRET_NAME
        )
        self._cache: Optional[Dict[str, str]] = None

    def _load(self) -> Dict[str, str]:
        """Carrega (e cacheia por processo) o segredo JSON como dict de strings."""
        if self._cache is not None:
            return self._cache
        import boto3  # import tardio: sem SDK, só falha se a fonte for usada

        client = boto3.client(
            "secretsmanager",
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None,
        )
        raw = (
            client.get_secret_value(SecretId=self._secret_name).get("SecretString")
            or "{}"
        )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}  # segredo não-JSON: trate como vazio, sem vazar conteúdo
        self._cache = {k: str(v) for k, v in data.items() if isinstance(v, str)}
        return self._cache

    def get(self, key: str) -> Optional[str]:
        """Retorna o valor da chave; vazio vira ``None`` (vazio == ausente)."""
        return self._load().get(key) or None
