"""Testes do adapter CLI fino (``qa_platform.interface.cli.main``).

Cobre o comando ``health`` (Requisito 6.2): imprime o status em JSON e retorna
exit code ``0``; o default sem argumentos também resolve para ``health``; e um
comando desconhecido retorna exit code não-zero. O comando ``serve`` não é
exercido diretamente (bloquearia no ``uvicorn.run``); há um teste que faz
monkeypatch de ``uvicorn.run`` para um no-op e valida o exit code ``0``.

Validates: Requirements 6.2
"""

from __future__ import annotations

import json

import pytest

from qa_platform.interface.cli import main as cli_main
from qa_platform.interface.cli.main import main


def test_health_imprime_status_e_retorna_0(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``main(["health"])`` imprime ``{"status":"ok","version":<SERVICE_VERSION>}``
    em stdout e retorna exit code ``0`` (Req 6.2)."""
    monkeypatch.setenv("SERVICE_VERSION", "1.2.3")

    exit_code = main(["health"])

    assert exit_code == 0
    body = json.loads(capsys.readouterr().out)
    assert body == {"status": "ok", "version": "1.2.3"}


def test_sem_argumentos_faz_default_para_health(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``main([])`` sem argumentos resolve para ``health`` e retorna ``0`` (Req 6.2)."""
    monkeypatch.setenv("SERVICE_VERSION", "9.9.9")

    exit_code = main([])

    assert exit_code == 0
    body = json.loads(capsys.readouterr().out)
    assert body == {"status": "ok", "version": "9.9.9"}


def test_comando_desconhecido_retorna_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Um subcomando desconhecido retorna exit code ``2`` e reporta o erro."""
    monkeypatch.setenv("SERVICE_VERSION", "1.0.0")

    exit_code = main(["banana"])

    assert exit_code == 2
    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert "banana" in error["error"]


def test_serve_delega_ao_uvicorn_e_retorna_0(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``main(["serve"])`` delega ao ``uvicorn.run`` (aqui um no-op) e retorna ``0``.

    Não subimos o servidor de verdade: fazemos monkeypatch de ``uvicorn.run``
    para um no-op que registra a chamada, evitando o bloqueio do event loop."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _fake_run(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", _fake_run)

    exit_code = main(["serve"])

    assert exit_code == 0
    assert len(calls) == 1
    # A import string do app ASGI é o primeiro argumento posicional.
    assert calls[0][0][0] == cli_main._APP_IMPORT_STRING
