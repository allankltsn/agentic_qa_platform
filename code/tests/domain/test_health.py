"""Testes unitários por exemplo do value object HealthStatus (Req 1.2, 1.3, 5.2)."""

from qa_platform.domain.value_objects.health import STATUS_OK, HealthStatus


def test_healthy_produz_status_ok() -> None:
    """HealthStatus.healthy deve produzir status == "ok" (Req 1.2)."""
    health = HealthStatus.healthy("1.0.0")

    assert health.status == "ok"
    assert health.status == STATUS_OK


def test_healthy_preserva_a_versao() -> None:
    """HealthStatus.healthy deve preservar a versão informada (Req 1.3)."""
    health = HealthStatus.healthy("2.3.4")

    assert health.version == "2.3.4"


def test_healthy_e_imutavel() -> None:
    """HealthStatus é frozen: atribuir a um campo levanta erro (Req 5.2)."""
    health = HealthStatus.healthy("1.0.0")

    try:
        health.version = "9.9.9"  # type: ignore[misc]
    except Exception as exc:  # dataclasses.FrozenInstanceError herda de AttributeError
        assert isinstance(exc, AttributeError)
    else:
        raise AssertionError("HealthStatus deveria ser imutável (frozen)")
