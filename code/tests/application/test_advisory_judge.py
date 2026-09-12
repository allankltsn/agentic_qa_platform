"""Teste de propriedade do Advisory_Judge (Property 12).

# Feature: workflow-orchestrator-skeleton, Property 12

Property 12: Priorização determinística, por severidade, preservadora e sem
veredito — ordena por severidade de forma estável, preserva contagem/identidades,
não emite pass/fail, é idêntica em execuções repetidas, e vazia quando não há
evidências (Requisitos 10.1, 10.2, 10.4, 10.5).
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.application.advisory_judge import prioritize
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.run_result import RunResult
from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId
from qa_platform.domain.value_objects.severity import Severity

_layer_values = st.text(min_size=1, max_size=10).filter(lambda v: v.strip() != "")
_severities = st.sampled_from(list(Severity))


@st.composite
def _run_results(draw: st.DrawFn) -> RunResult:
    """RunResult consolidado com evidências variadas (incluindo vazio)."""
    values = draw(st.lists(_layer_values, min_size=0, max_size=8, unique=True))
    evidences = []
    for v in values:
        n_findings = draw(st.integers(min_value=0, max_value=3))
        findings = tuple(
            Finding(code=f"c{i}", severity=draw(_severities), detail="d")
            for i in range(n_findings)
        )
        evidences.append(LayerEvidence(layer_id=LayerId(v), findings=findings))
    return RunResult(
        run_id=RunId("run"),
        target_ref="target",
        target_version="1.0.0",
        plan=ExecutionPlan(),
        evidences=tuple(evidences),
    )


def _max_severity(evidence: LayerEvidence) -> int:
    return int(max((f.severity for f in evidence.findings), default=Severity.INFO))


# Feature: workflow-orchestrator-skeleton, Property 12
# Property 12: Priorização determinística, por severidade, preservadora e sem veredito.
# Validates: Requirements 10.1, 10.2, 10.4, 10.5; Property 12
@settings(max_examples=100)
@given(result=_run_results())
def test_prioritize_deterministica_por_severidade_preservadora_sem_veredito(
    result: RunResult,
) -> None:
    """prioritize ordena por severidade, preserva origem, é determinística e sem veredito."""
    judged = prioritize(result)

    # (d) Determinística: repetir produz o mesmo resultado (Req 10.4).
    assert prioritize(result) == judged

    # (b) Preserva todas as evidências de origem: mesma contagem e identidades (Req 10.2).
    assert len(judged.prioritized) == len(result.evidences)
    assert {e.layer_id for e in judged.prioritized} == {
        e.layer_id for e in result.evidences
    }
    # As evidências de origem não são descartadas.
    assert judged.evidences == result.evidences

    # (a) Ordenação por severidade máxima decrescente, estável (Req 10.1).
    severidades = [_max_severity(e) for e in judged.prioritized]
    assert severidades == sorted(severidades, reverse=True)

    # (c) Sem veredito pass/fail em nenhuma evidência priorizada (Req 6.6/10.1).
    for ev in judged.prioritized:
        assert not (set(vars(ev)) & {"passed", "failed", "verdict"})

    # (e) Sem evidências → priorização vazia, sem erro (Req 10.5).
    if not result.evidences:
        assert judged.prioritized == ()
