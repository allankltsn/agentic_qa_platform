"""Testes por exemplo do stub seguro de validação de JWT (Req 1.5).

Verificam que ``verify_jwt`` é um stub explícito: enquanto ``AUTH_ENABLED`` não
está configurado, qualquer chamada levanta ``NotImplementedError`` — nunca
aprova um token silenciosamente.
"""

from __future__ import annotations

import pytest

from qa_platform.infrastructure.security.jwt import verify_jwt


def test_verify_jwt_levanta_not_implemented() -> None:
    """O stub de JWT deve levantar NotImplementedError (Req 1.5)."""
    with pytest.raises(NotImplementedError):
        verify_jwt("qualquer.token.aqui")
