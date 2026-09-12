"""Testes por exemplo dos tratadores de erro neutros (Req 1.5).

Verificam que ``register_error_handlers`` faz a app devolver uma resposta neutra
(HTTP 500 com corpo genérico) quando uma exceção não tratada ocorre, sem NUNCA
vazar stack trace ou detalhes internos ao cliente.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qa_platform.infrastructure.security.error_handlers import (
    register_error_handlers,
)


def _build_app() -> FastAPI:
    """App mínima que registra os handlers e uma rota que sempre falha."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> dict:
        raise RuntimeError("segredo-interno-sensivel: detalhe que nao deve vazar")

    return app


def test_erro_devolve_500_neutro_sem_vazar_stack_trace() -> None:
    """Erro não tratado → 500 com corpo genérico, sem detalhes (Req 1.5)."""
    # raise_server_exceptions=False faz o TestClient exercitar o handler em vez
    # de propagar a exceção para o teste.
    client = TestClient(_build_app(), raise_server_exceptions=False)

    resp = client.get("/boom")

    assert resp.status_code == 500
    assert resp.json() == {"detail": "erro interno"}

    # O corpo NUNCA deve conter a mensagem da exceção, o tipo nem stack trace.
    body = resp.text
    assert "segredo-interno-sensivel" not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
