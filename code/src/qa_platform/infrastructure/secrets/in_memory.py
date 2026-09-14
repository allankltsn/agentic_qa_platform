"""Adapter de segredos em memória (para testes; sem rede).

Implementa a porta ``SecretsProvider`` sobre um dicionário em memória. É usado
nos testes para exercitar o ``SecretResolver`` sem dependências externas.
Trata valor vazio como ausente (``"" == None``) e nunca loga valores
(Requisito 7.1).
"""

from __future__ import annotations


class InMemorySecretsProvider:
    """Fonte de segredos baseada em um dicionário em memória."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = dict(secrets or {})

    def get(self, key: str) -> str | None:
        """Retorna o valor da chave; valor vazio vira ``None`` (vazio == ausente)."""
        return self._secrets.get(key) or None
