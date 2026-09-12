"""Rate limiting (STUB por env, default OFF, dependente de identidade).

Controle de borda dependente de identidade (principal/IP). No bootstrap fica
**desligado explicitamente** por env (``RATE_LIMIT_ENABLED`` default ``false``).
Se habilitado por env mas ainda sem implementação real, levanta
``NotImplementedError`` — nunca aprova silenciosamente (Requisito 1.5).
"""

from __future__ import annotations

import os

_RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "false").lower() == "true"


def add_rate_limit(app) -> None:
    """Registra rate limit na app — desligado por default (stub seguro).

    Com ``RATE_LIMIT_ENABLED`` ausente/``false`` retorna sem efeito (desligado
    EXPLICITAMENTE por env). Se habilitado sem implementação real, levanta
    ``NotImplementedError`` em vez de deixar a borda aberta silenciosamente.
    """
    if not _RATE_LIMIT_ENABLED:
        return  # bootstrap: desligado EXPLICITAMENTE por env
    # TODO: cabear rate limit por principal/IP (ex.: slowapi) quando houver auth.
    raise NotImplementedError(
        "rate limit habilitado por env, mas ainda não configurado"
    )
