"""Teste de propriedade do determinismo do Risk_Planner (Property 1).

Verifica a propriedade universal de que planejar o mesmo manifesto duas vezes
produz ``ExecutionPlan`` iguais em valor e com serialização idêntica, refletindo
o determinismo byte-a-byte exigido pelo ADR-001 (Requisitos 1.2, 2.5, 3.6).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.application.risk_planner import plan_by_risk
from qa_platform.domain.entities.manifest import QATargetManifest, RiskParameters
from qa_platform.domain.value_objects.ids import LayerId

# Gerador de valores de LayerId: strings não-vazias e não compostas apenas por
# espaços, restringindo ao espaço de entrada aceito por LayerId.
_layer_id_values = st.text(min_size=1, max_size=12).filter(lambda v: v.strip() != "")

# Gerador de pesos de risco finitos e não-negativos, em faixa razoável. Evita
# NaN/inf e valores negativos, garantindo prioridade derivada válida em [1, 100].
_weights = st.floats(
    min_value=0.0,
    max_value=10.0,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def _valid_manifests(draw: st.DrawFn) -> QATargetManifest:
    """Gera um ``QATargetManifest`` válido para o Risk_Planner.

    Garante ao menos uma camada aplicável com valores de ``LayerId`` distintos e
    constrói ``risk_parameters`` cobrindo exatamente essas camadas, evitando o
    ``InvalidManifestError`` levantado quando uma camada aplicável não possui
    parâmetros de risco correspondentes.
    """
    layer_values = draw(st.lists(_layer_id_values, min_size=1, max_size=8, unique=True))
    applicable_layers = tuple(LayerId(value) for value in layer_values)
    risk_parameters = {
        layer_id: RiskParameters(weight=draw(_weights))
        for layer_id in applicable_layers
    }
    target_ref = draw(st.text(min_size=1, max_size=16).filter(lambda v: v.strip()))
    target_version = draw(st.text(min_size=1, max_size=8).filter(lambda v: v.strip()))
    return QATargetManifest(
        target_ref=target_ref,
        target_version=target_version,
        applicable_layers=applicable_layers,
        risk_parameters=risk_parameters,
    )


# Feature: workflow-orchestrator-skeleton, Property 1
# Property 1: Determinismo do Risk_Planner — planejar duas vezes o mesmo
# manifest produz ExecutionPlans iguais em valor (serialização idêntica).
# Validates: Requirements 1.2, 2.5, 8.6; Property 1
@settings(max_examples=100)
@given(manifest=_valid_manifests())
def test_plan_by_risk_planejamento_repetido_produz_planos_identicos(
    manifest: QATargetManifest,
) -> None:
    """Para qualquer manifesto válido, planejar duas vezes produz planos iguais
    em valor e com serialização idêntica (Req 1.2, 2.5, 8.6)."""
    first = plan_by_risk(manifest)
    second = plan_by_risk(manifest)

    # Igualdade por valor: ExecutionPlan e PlannedLayer são frozen dataclasses.
    assert first == second
    # Serialização/representação idêntica reflete o determinismo byte-a-byte.
    assert repr(first) == repr(second)
    assert first.layers == second.layers


# Feature: workflow-orchestrator-skeleton, Property 2
# Property 2: Prioridades no intervalo válido e cobertura das camadas — o
# ExecutionPlan produzido por plan_by_risk contém exatamente as camadas
# aplicáveis do manifesto (mesmo conjunto de layer_ids, sem extras nem
# faltantes) e cada PlannedLayer tem priority inteira em [1, 100].
# Validates: Requirements 2.2; Property 2
@settings(max_examples=100)
@given(manifest=_valid_manifests())
def test_plan_by_risk_cobre_camadas_e_prioridades_no_intervalo(
    manifest: QATargetManifest,
) -> None:
    """Para qualquer manifesto válido, o plano cobre exatamente as camadas
    aplicáveis e cada prioridade é inteira no intervalo [1, 100] (Req 2.2)."""
    plan = plan_by_risk(manifest)

    for planned in plan.layers:
        # Prioridade inteira estrita (não bool) no intervalo válido.
        assert type(planned.priority) is int
        assert 1 <= planned.priority <= 100

    # Cobertura exata: mesmo conjunto e mesma contagem de identidades, sem
    # camadas extras nem faltantes.
    planned_ids = {planned.layer_id for planned in plan.layers}
    assert planned_ids == set(manifest.applicable_layers)
    assert len(plan.layers) == len(manifest.applicable_layers)


@st.composite
def _invalid_manifests(draw: st.DrawFn) -> QATargetManifest:
    """Gera manifestos inválidos para o Risk_Planner (sem risco ou risco incompleto)."""
    kind = draw(st.sampled_from(["empty_risk", "missing_layer_risk"]))
    layer_values = draw(st.lists(_layer_id_values, min_size=1, max_size=6, unique=True))
    applicable_layers = tuple(LayerId(value) for value in layer_values)
    target_ref = draw(st.text(min_size=1, max_size=16).filter(lambda v: v.strip()))
    target_version = draw(st.text(min_size=1, max_size=8).filter(lambda v: v.strip()))

    if kind == "empty_risk":
        return QATargetManifest(
            target_ref=target_ref,
            target_version=target_version,
            applicable_layers=applicable_layers,
            risk_parameters={},
        )

    covered = draw(
        st.lists(
            st.sampled_from(layer_values),
            min_size=0,
            max_size=max(0, len(layer_values) - 1),
            unique=True,
        )
    )
    risk_parameters = {
        LayerId(layer_id): RiskParameters(weight=draw(_weights)) for layer_id in covered
    }
    return QATargetManifest(
        target_ref=target_ref,
        target_version=target_version,
        applicable_layers=applicable_layers,
        risk_parameters=risk_parameters,
    )


# Feature: workflow-orchestrator-skeleton, Property 3
# Property 3: Rejeição de manifest inválido pelo Risk_Planner — manifest sem/
# com risco inválido levanta InvalidManifestError sem produzir plano, nomeando
# o campo.
# Validates: Requirements 2.3; Property 3
@settings(max_examples=100)
@given(manifest=_invalid_manifests())
def test_plan_by_risk_rejeita_manifesto_invalido_sem_produzir_plano(
    manifest: QATargetManifest,
) -> None:
    """Para manifesto inválido, plan_by_risk levanta InvalidManifestError (Req 2.3)."""
    from qa_platform.domain.exceptions import InvalidManifestError

    with pytest.raises(InvalidManifestError) as exc_info:
        plan_by_risk(manifest)

    assert exc_info.value.invalid_fields
    assert "risk_parameters" in exc_info.value.invalid_fields or any(
        key.startswith("risk_parameters[") for key in exc_info.value.invalid_fields
    )
