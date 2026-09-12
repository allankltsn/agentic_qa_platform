"""Teste de propriedade da Cost_Condition (Property 7).

# Feature: workflow-orchestrator-skeleton, Property 7

Property 7: decisão determinística baseada só no manifest — parâmetros idênticos
produzem a mesma decisão ``(skip, motivo)``; sem parâmetros de custo → pular com
motivo não-vazio (Requisitos 5.1, 5.4, 5.5).
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.entities.manifest import (
    CostParameters,
    QATargetManifest,
    RiskParameters,
)
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.cost_condition import (
    should_skip_expensive,
)

_AI = LayerId("ai")
_finite = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
)


@st.composite
def _manifests(draw: st.DrawFn) -> QATargetManifest:
    """Manifesto com ou sem parâmetros de custo para a camada 'ai'."""
    tem_custo = draw(st.booleans())
    cost = {}
    if tem_custo:
        cost = {
            _AI: CostParameters(
                risk_threshold=draw(_finite), estimated_risk=draw(_finite)
            )
        }
    return QATargetManifest(
        target_ref="repo/x",
        target_version="1.0.0",
        applicable_layers=(_AI,),
        risk_parameters={_AI: RiskParameters(weight=0.5)},
        cost_parameters=cost,
    )


# Feature: workflow-orchestrator-skeleton, Property 7
# Property 7: decisão determinística baseada só no manifest (Req 5.1, 5.4, 5.5).
# Validates: Requirements 5.1, 5.4, 5.5; Property 7
@settings(max_examples=100)
@given(manifest=_manifests())
def test_decisao_deterministica_baseada_so_no_manifest(
    manifest: QATargetManifest,
) -> None:
    """Parâmetros idênticos → mesma decisão; sem parâmetros → pular com motivo (Req 5.x)."""
    skip1, reason1 = should_skip_expensive(manifest, _AI)
    skip2, reason2 = should_skip_expensive(manifest, _AI)

    # Determinística (Req 5.4).
    assert (skip1, reason1) == (skip2, reason2)

    params = manifest.cost_parameters_for(_AI)
    if params is None:
        # Sem parâmetros → pular com motivo não-vazio (Req 5.5).
        assert skip1 is True
        assert reason1 != ""
    elif not params.justifies_expensive_work():
        # Não justificado → pular com motivo não-vazio (Req 5.1).
        assert skip1 is True
        assert reason1 != ""
    else:
        # Justificado → executar (não pular), motivo vazio.
        assert skip1 is False
        assert reason1 == ""
