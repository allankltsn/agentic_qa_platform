"""Testes por exemplo do logging estruturado JSON (Req 1.2, 1.3).

Verificam que ``log_event`` emite uma única linha JSON válida contendo apenas os
campos passados (``event`` + kwargs), sem quebras de linha embutidas e sem adicionar
campos de PII/segredo além do que foi informado.
"""

from __future__ import annotations

import io
import json
import logging

from qa_platform.infrastructure.observability.logging import (
    build_json_logger,
    log_event,
)


def _capture_logger() -> tuple[logging.Logger, io.StringIO]:
    """Cria um logger JSON escrevendo em um buffer em memória para inspeção."""
    logger = build_json_logger(name="qa-platform-test", level="INFO")
    logger.handlers.clear()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger, stream


def test_log_event_emite_json_valido_de_uma_linha() -> None:
    """log_event deve emitir uma única linha que é JSON válido (Req 1.2)."""
    logger, stream = _capture_logger()

    log_event(logger, "some_event", key="val")

    output = stream.getvalue()
    # StreamHandler acrescenta um terminador de linha final; a mensagem em si
    # não deve conter nenhuma quebra de linha embutida.
    linha = output.rstrip("\n")
    assert "\n" not in linha, "o evento não deve conter quebras de linha embutidas"

    parsed = json.loads(linha)  # deve ser JSON válido
    assert parsed == {"event": "some_event", "key": "val"}


def test_log_event_contem_event_e_campos_informados() -> None:
    """A linha emitida deve conter o event e os campos passados (Req 1.3)."""
    logger, stream = _capture_logger()

    log_event(logger, "health_checked", status="ok", version="1.2.3")

    parsed = json.loads(stream.getvalue().rstrip("\n"))
    assert parsed["event"] == "health_checked"
    assert parsed["status"] == "ok"
    assert parsed["version"] == "1.2.3"


def test_log_event_nao_adiciona_campos_alem_dos_informados() -> None:
    """log_event não deve injetar PII/segredo nem campos extras (Req 1.2, 1.3)."""
    logger, stream = _capture_logger()

    log_event(logger, "startup")

    parsed = json.loads(stream.getvalue().rstrip("\n"))
    # Apenas a chave "event" deve existir quando nenhum campo é passado.
    assert set(parsed.keys()) == {"event"}
    assert parsed["event"] == "startup"


def test_log_event_emite_uma_linha_por_evento() -> None:
    """Cada chamada de log_event produz exatamente uma linha JSON (Req 1.2)."""
    logger, stream = _capture_logger()

    log_event(logger, "first")
    log_event(logger, "second")

    linhas = [linha for linha in stream.getvalue().split("\n") if linha]
    assert len(linhas) == 2
    assert json.loads(linhas[0]) == {"event": "first"}
    assert json.loads(linhas[1]) == {"event": "second"}
