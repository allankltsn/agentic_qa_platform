"""Teste unitário da ordem total de ``Severity`` (Requisito 10.1)."""

from qa_platform.domain.value_objects.severity import Severity


def test_ordem_total_crescente() -> None:
    """INFO < LOW < MEDIUM < HIGH < CRITICAL (Req 10.1)."""
    assert (
        Severity.INFO
        < Severity.LOW
        < Severity.MEDIUM
        < Severity.HIGH
        < Severity.CRITICAL
    )


def test_critical_e_a_maior() -> None:
    """CRITICAL é a severidade máxima (base da priorização determinística)."""
    todas = [
        Severity.INFO,
        Severity.LOW,
        Severity.MEDIUM,
        Severity.HIGH,
        Severity.CRITICAL,
    ]
    assert max(todas) is Severity.CRITICAL
    assert min(todas) is Severity.INFO
