"""Cabeçalhos de segurança HTTP (controle FUNCIONAL de borda).

Middleware que adiciona cabeçalhos de segurança baratos a QUALQUER resposta,
inclusive ``/health``: ``nosniff``, ``X-Frame-Options``, HSTS e uma CSP
restritiva. É funcional e aplicável desde o bootstrap (Requisitos 1.1, 1.5).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona cabeçalhos de segurança padrão a toda resposta HTTP."""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        resp.headers["Content-Security-Policy"] = "default-src 'none'"
        return resp


def add_security_headers(app) -> None:
    """Registra o ``SecurityHeadersMiddleware`` na app FastAPI/Starlette."""
    app.add_middleware(SecurityHeadersMiddleware)
