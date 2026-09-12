"""Validação de JWT (STUB seguro, dependente de identidade).

Controle de borda dependente de identidade. No bootstrap ainda NÃO há
``AUTH_ENABLED`` configurado, então este stub é **explícito**: qualquer chamada
levanta ``NotImplementedError``. Segue a regra da skill ``agno-security``:
comportamento seguro por default, **nunca** um mock que aprova tudo
silenciosamente (Requisito 1.5).
"""

from __future__ import annotations


def verify_jwt(token: str) -> dict:
    """Valida um token JWT — ainda NÃO implementado (stub seguro).

    Quando ``AUTH_ENABLED=true``, esta função deverá validar assinatura, ``exp``,
    ``aud`` e ``iss`` de verdade. Enquanto isso, levanta ``NotImplementedError``
    para nunca aprovar um token indevidamente.
    """
    # TODO: quando AUTH_ENABLED=true, validar assinatura, exp, aud e iss de verdade.
    raise NotImplementedError("validação de JWT ainda não configurada (AUTH_ENABLED)")
