"""Testes unitários de ``LayerEvidence`` e ``Finding``.

Cobrem a igualdade por valor e a ausência de qualquer veredito pass/fail no
nível da camada (Requisitos 6.5, 6.6, 2.4).
"""

from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.domain.value_objects.severity import Severity


def test_layer_evidence_preserva_identidade_de_origem() -> None:
    """LayerEvidence carrega a identidade da camada de origem (Req 2.4)."""
    ev = LayerEvidence(layer_id=LayerId("ai"), metrics={"n": 1.0})
    assert ev.layer_id == LayerId("ai")
    assert ev.metrics == {"n": 1.0}


def test_layer_evidence_nao_expoe_veredito() -> None:
    """LayerEvidence NÃO expõe nenhum campo de veredito pass/fail (Req 6.6)."""
    ev = LayerEvidence(layer_id=LayerId("ai"))
    proibidos = {"passed", "failed", "verdict", "pass_fail", "result", "status"}
    campos = set(vars(ev).keys())
    assert proibidos.isdisjoint(
        campos
    ), f"LayerEvidence não pode ter campo de veredito; encontrados: {campos & proibidos}"


def test_layer_evidence_igual_por_valor() -> None:
    """Duas evidências com os mesmos campos são iguais por valor."""
    f = Finding(code="x", severity=Severity.HIGH, detail="d")
    a = LayerEvidence(layer_id=LayerId("ai"), metrics={"n": 1.0}, findings=(f,))
    b = LayerEvidence(layer_id=LayerId("ai"), metrics={"n": 1.0}, findings=(f,))
    assert a == b
