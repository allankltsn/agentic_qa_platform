"""Porta (Protocol) da fonte de segredos.

Define o contrato ``SecretsProvider`` usado pelo ``SecretResolver`` para
consultar uma fonte secundária de segredos (por exemplo, AWS Secrets Manager
ou uma fonte em memória para testes). Manter a fonte atrás de uma porta mantém
o resolver testável sem rede e isola dependências concretas (Requisito 7.1).
"""

from __future__ import annotations

from typing import Protocol


class SecretsProvider(Protocol):
    """Fonte secundária de segredos.

    Retorna o valor associado à chave ou ``None`` quando ausente. As
    implementações NUNCA logam o valor retornado (Requisito 7.1).
    """

    def get(self, key: str) -> str | None:
        """Retorna o valor da chave, ou ``None`` se ausente/vazio."""
        ...
