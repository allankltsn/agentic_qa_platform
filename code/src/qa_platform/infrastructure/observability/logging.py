"""Logging estruturado em JSON (controle FUNCIONAL de observabilidade).

Emite uma linha JSON por evento em ``stdout`` (encaminhada ao CloudWatch quando
executando em Lambda). Nunca registra PII ou segredos — apenas metadados do
evento. Observabilidade é preocupação de infraestrutura, cabeada no
``composition_root``; o domínio não a conhece (Requisitos 1.2, 1.3).
"""

from __future__ import annotations

import json
import logging


def build_json_logger(name: str = "qa-platform", level: str = "INFO") -> logging.Logger:
    """Constrói um logger que emite cada mensagem como uma linha em ``stdout``.

    A mensagem já vem serializada em JSON (ver :func:`log_event`), por isso o
    formatter apenas repassa ``%(message)s``. Limpa handlers pré-existentes para
    evitar duplicação e desativa a propagação ao logger raiz.
    """
    logger = logging.getLogger(name)
    logger.handlers.clear()
    handler = logging.StreamHandler()  # stdout -> CloudWatch em Lambda
    handler.setFormatter(logging.Formatter("%(message)s"))  # a msg já é JSON
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """Registra um evento como uma única linha JSON.

    NUNCA logue PII/segredo — apenas metadados do evento. ``ensure_ascii=False``
    preserva acentuação legível nos campos.
    """
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False))
