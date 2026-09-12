"""CORS restritivo (controle FUNCIONAL de borda).

Configura o CORS de forma restritiva: filtra origens vazias e NUNCA aceita o
coringa ``"*"``. Somente o método ``GET`` e os cabeçalhos estritamente
necessários são permitidos (Requisitos 1.1, 1.5).
"""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware


def add_cors(app, allowed_origins: list[str]) -> None:
    """Registra o ``CORSMiddleware`` restritivo na app.

    Remove entradas vazias e o coringa ``"*"`` de ``allowed_origins`` — o CORS
    nunca é liberado para qualquer origem. Habilita credenciais, restringe os
    métodos a ``GET`` e os cabeçalhos a ``Authorization``/``Content-Type``.
    """
    origins = [o for o in allowed_origins if o and o != "*"]  # nunca "*"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type"],
    )
