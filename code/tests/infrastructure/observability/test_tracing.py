"""Testes por exemplo do tracing OTel ligado/desligado por env (Req 1.2, 1.3).

Verificam que, com o tracing desligado por ambiente, ``configure_tracing`` é um
NO-OP total: retorna ``False`` sem importar nenhuma dependência de OpenTelemetry.
"""

from __future__ import annotations

import pytest

from qa_platform.infrastructure.observability.tracing import configure_tracing


def _disable_tracing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garante que as variáveis que ligam o tracing estejam ausentes."""
    monkeypatch.delenv("TRACING_ENABLED", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)


def test_configure_tracing_retorna_false_quando_desligado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem env de tracing, configure_tracing é no-op e retorna False (Req 1.3)."""
    _disable_tracing_env(monkeypatch)

    assert configure_tracing() is False


def test_configure_tracing_false_com_tracing_enabled_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TRACING_ENABLED=false mantém o no-op (Req 1.3)."""
    monkeypatch.setenv("TRACING_ENABLED", "false")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert configure_tracing("qa-platform") is False


def test_configure_tracing_no_op_nao_importa_otel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O no-op não deve exigir/importar dependências de OTel (Req 1.2, 1.3).

    Bloqueamos qualquer import de ``opentelemetry`` durante a chamada; se o
    caminho desligado tentasse importar OTel, o teste falharia.
    """
    import builtins

    _disable_tracing_env(monkeypatch)
    real_import = builtins.__import__

    def _guarded_import(name: str, *args: object, **kwargs: object):
        if name.startswith("opentelemetry"):
            raise AssertionError(
                "configure_tracing desligado não deve importar OpenTelemetry"
            )
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _guarded_import)

    assert configure_tracing() is False
