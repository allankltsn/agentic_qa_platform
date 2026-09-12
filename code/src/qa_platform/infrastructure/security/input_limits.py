"""Limite de payload de entrada (controle FUNCIONAL/base de borda).

Define o tamanho máximo de corpo aceito e uma função pura que rejeita
requisições cujo ``Content-Length`` exceda o limite, mitigando abuso de
payloads gigantes (Requisito 1.5).
"""

from __future__ import annotations

MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB por padrão


def enforce_body_limit(content_length: int | None) -> None:
    """Valida o tamanho do corpo contra ``MAX_BODY_BYTES``.

    Levanta ``ValueError`` quando ``content_length`` for informado e exceder o
    limite. Quando ``None`` (desconhecido), não bloqueia aqui.
    """
    if content_length is not None and content_length > MAX_BODY_BYTES:
        raise ValueError("payload excede o tamanho máximo permitido")
