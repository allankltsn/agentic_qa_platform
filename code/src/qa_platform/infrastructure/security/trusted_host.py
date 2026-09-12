"""Trusted Host (controle FUNCIONAL de borda).

Restringe os hosts (cabeçalho ``Host``) aceitos pela aplicação via
``TrustedHostMiddleware``, mitigando ataques de Host header (Requisito 1.5).
"""

from __future__ import annotations

from starlette.middleware.trustedhost import TrustedHostMiddleware


def add_trusted_host(app, allowed_hosts: list[str]) -> None:
    """Registra o ``TrustedHostMiddleware`` com os hosts permitidos.

    Quando ``allowed_hosts`` estiver vazio, cai no ``["*"]`` do Starlette para
    não quebrar o bootstrap local; em produção a lista deve ser explícita.
    """
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts or ["*"])
