"""Dependency FastAPI de autenticação (STUB seguro, dependente de identidade).

No bootstrap a autenticação por request ainda NÃO está configurada. Esta
dependency é **segura por default**, seguindo a skill ``agno-security``:

- ``AUTH_ENABLED`` tem default ``false`` → retorna ``None`` (sem principal),
  de forma **explícita por configuração**. A rota ``GET /health`` do bootstrap
  é pública.
- ``AUTH_ENABLED=true`` mas sem credencial → nega com ``401``.
- ``AUTH_ENABLED=true`` com credencial → delega para ``verify_jwt`` (stub que
  ainda levanta ``NotImplementedError``); a dependency traduz isso para ``401``.

Em nenhum cenário esta dependency "aprova tudo" silenciosamente (Requisito 1.5).
"""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from qa_platform.infrastructure.security.jwt import verify_jwt

# ``auto_error=False``: não deixamos o esquema Bearer decidir sozinho; a decisão
# de negar/permitir é explícita aqui, para nunca aprovar por omissão.
_bearer = HTTPBearer(auto_error=False)


def _auth_enabled() -> bool:
    """Lê ``AUTH_ENABLED`` do ambiente (default ``false``).

    Avaliado a cada request para permitir alternar por configuração sem depender
    do momento do import do módulo.
    """
    return os.environ.get("AUTH_ENABLED", "false").strip().lower() == "true"


def get_current_principal(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """Resolve o principal autenticado do request (stub seguro).

    Retorna ``None`` quando a autenticação está desligada por configuração; caso
    contrário, exige e valida uma credencial, negando com ``401`` sempre que a
    autenticação não puder ser comprovada. **Nunca** aprova silenciosamente.
    """
    if not _auth_enabled():
        # Bootstrap: authn desligada EXPLICITAMENTE por env (comportamento documentado).
        return None

    if cred is None:
        # Auth ligada mas sem credencial: nega (nunca aprova por omissão).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciais de autenticação ausentes",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # STUB: ``verify_jwt`` ainda levanta ``NotImplementedError``.
        return verify_jwt(cred.credentials)
    except NotImplementedError as exc:
        # Auth ligada mas validação de JWT ainda não configurada: NEGA (nunca aprova).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="autenticação ainda não configurada",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
