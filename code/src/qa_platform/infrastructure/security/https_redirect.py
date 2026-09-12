"""Redirecionamento HTTPS (STUB por env, default OFF).

Controle de borda ligado/desligado por env (``HTTPS_REDIRECT_ENABLED`` default
``false``). No bootstrap o TLS é terminado no API Gateway/ALB, então o redirect
fica desligado por padrão. Quando habilitado, registra o
``HTTPSRedirectMiddleware`` do Starlette (Requisito 1.5).
"""

from __future__ import annotations

import os

from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

_HTTPS_REDIRECT_ENABLED = (
    os.environ.get("HTTPS_REDIRECT_ENABLED", "false").lower() == "true"
)


def add_https_redirect(app) -> None:
    """Registra o redirect para HTTPS na app — desligado por default.

    Com ``HTTPS_REDIRECT_ENABLED`` ausente/``false`` retorna sem efeito (TLS
    terminado no API Gateway/ALB). Se habilitado, adiciona o
    ``HTTPSRedirectMiddleware``.
    """
    if not _HTTPS_REDIRECT_ENABLED:
        return  # bootstrap: TLS terminado no API Gateway/ALB; redirect off por default
    app.add_middleware(HTTPSRedirectMiddleware)
