"""Testes por exemplo dos cabeçalhos de segurança HTTP (Req 1.5).

Verificam que ``add_security_headers`` registra o middleware que adiciona os
cabeçalhos de segurança a QUALQUER resposta: ``X-Content-Type-Options``,
``X-Frame-Options``, ``Strict-Transport-Security`` e ``Content-Security-Policy``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qa_platform.infrastructure.security.headers import add_security_headers


def _build_app() -> FastAPI:
    """App mínima com o middleware de segurança e uma rota trivial."""
    app = FastAPI()
    add_security_headers(app)

    @app.get("/ping")
    def ping() -> dict:
        return {"pong": True}

    return app


def test_security_headers_presentes_na_resposta() -> None:
    """A resposta deve conter todos os cabeçalhos de segurança (Req 1.5)."""
    client = TestClient(_build_app())

    resp = client.get("/ping")

    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in resp.headers
    assert resp.headers["Content-Security-Policy"] == "default-src 'none'"
