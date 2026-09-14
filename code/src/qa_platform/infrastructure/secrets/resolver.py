"""Resolver de config/segredos com pipe de fallback ``env -> Secrets Manager``.

Implementa a falha rápida agregada de configuração: cada valor é buscado
primeiro nas variáveis de ambiente (a env sempre vence) e, quando ausente,
numa fonte secundária opcional (``SecretsProvider``). Valor vazio ou apenas
com espaços conta como ausente. Se um valor obrigatório não for encontrado em
nenhuma fonte, levanta ``MissingSecretError`` nomeando SOMENTE o nome da
variável — nunca o valor de qualquer segredo (Requisitos 7.1, 7.2).
"""

from __future__ import annotations

import os

from qa_platform.infrastructure.secrets.ports import SecretsProvider


class MissingSecretError(RuntimeError):
    """Segredo/config obrigatório ausente em TODAS as fontes.

    Impede a aplicação de subir. Nomeia SOMENTE o nome da env — nunca o valor
    de qualquer segredo (Requisitos 7.1, 7.2).
    """


class SecretResolver:
    """Resolve config/segredos por pipe de fallback: env -> Secrets Manager.

    ``secrets_provider`` é opcional: sem ele, usa apenas a env. A env sempre
    vence sobre o Secrets Manager (override local/CI).
    """

    def __init__(self, secrets_provider: SecretsProvider | None = None) -> None:
        self._secrets = secrets_provider

    def resolve(
        self,
        env_name: str,
        *,
        required: bool = True,
        default: str | None = None,
    ) -> str | None:
        """Resolve ``env_name`` pelo pipe de fallback.

        Ordem: (1) variável de ambiente, que sempre vence; (2) Secrets Manager,
        quando um provider estiver configurado. Valor vazio ou apenas
        whitespace conta como ausente. Se ``required`` e não houver ``default``
        e o valor não for encontrado em nenhuma fonte, levanta
        ``MissingSecretError`` nomeando a variável (Requisitos 7.1, 7.2).
        """
        raw = os.environ.get(env_name)  # fonte 1: env (vence sempre)
        if raw is not None and raw.strip() != "":
            return raw
        if self._secrets is not None:  # fonte 2: Secrets Manager
            from_sm = self._secrets.get(env_name)
            if from_sm is not None and from_sm.strip() != "":
                return from_sm
        if required and default is None:  # fail fast: nomeia a env
            raise MissingSecretError(
                f"Configuração obrigatória ausente: '{env_name}' não foi encontrada "
                f"nem nas variáveis de ambiente nem no Secrets Manager."
            )
        return default
