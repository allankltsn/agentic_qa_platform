"""Tratadores de erro neutros (controle FUNCIONAL de borda).

Registra um handler global de ``Exception`` que devolve uma resposta neutra
(HTTP 500 com corpo genérico) e NUNCA vaza stack trace ou detalhes internos ao
cliente. O erro deve ser logado internamente sem PII/segredo (Requisito 1.5).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


def register_error_handlers(app) -> None:
    """Registra o handler global de exceção não tratada na app."""

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # noqa: ANN202
        # Logue ``exc`` internamente (sem PII/segredo); NUNCA devolva stack trace.
        return JSONResponse(status_code=500, content={"detail": "erro interno"})
