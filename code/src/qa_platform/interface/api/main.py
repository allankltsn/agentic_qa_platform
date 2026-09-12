"""Ponto de entrada Lambda (Mangum) — adapta a app FastAPI para o AWS Lambda.

Adapta a **mesma** app FastAPI usada na execução local ao modelo de invocação do
AWS Lambda por meio do adapter ASGI :class:`Mangum` (Requisitos 3.1, 3.4). A app
é construída no import do módulo via ``build_app()``: se a inicialização falhar
(ex.: ``MissingConfigError`` por ``SERVICE_VERSION`` ausente), a exceção sobe no
próprio import — a init do Lambda falha e a invocação encerra com erro, **nunca**
retornando HTTP 200 (Requisito 3.3).

O ``Handler`` do SAM aponta para ``qa_platform.interface.api.main.handler``. Como
a factory da app é compartilhada com a execução local, as rotas e o comportamento
de "não encontrado" (404) são idênticos nos dois ambientes (Requisitos 3.2, 3.5).
"""

from __future__ import annotations

from mangum import Mangum

from qa_platform.composition_root import build_app

app = build_app()  # se a config faltar, levanta aqui (falha a init, sem 200)
handler = Mangum(app)  # traduz evento API Gateway <-> ASGI
