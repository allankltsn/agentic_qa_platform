"""Testes da AILayerStub: Property 8 (determinismo) + exemplos de contrato.

# Feature: workflow-orchestrator-skeleton, Property 8

Property 8: o mesmo ``(plan, manifest)`` produz ``LayerEvidence`` com campos
iguais em valor (Req 7.4). Exemplos cobrem: evidência com identidade + referência
ao plano sem ferramentas externas (7.2); entrada malformada → erro sem evidência
(7.5); e fail-fast quando ``MODEL_PROVIDER`` está ausente (12.6).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.entities.execution_plan import ExecutionPlan, PlannedLayer
from qa_platform.domain.entities.manifest import QATargetManifest, RiskParameters
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.layers.ai_layer_stub import (
    AILayerStub,
    InvalidLayerInputError,
    ModelProviderNotConfiguredError,
)
from qa_platform.infrastructure.secrets.in_memory import InMemorySecretsProvider
from qa_platform.infrastructure.secrets.resolver import SecretResolver

_AI = LayerId("ai")
_layer_values = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def _stub_with_provider() -> AILayerStub:
    """AILayerStub com MODEL_PROVIDER resolvido via provider in-memory (testável)."""
    resolver = SecretResolver(
        secrets_provider=InMemorySecretsProvider({"MODEL_PROVIDER": "openai"})
    )
    return AILayerStub(resolver=resolver)


@st.composite
def _plan_and_manifest(draw: st.DrawFn) -> tuple[ExecutionPlan, QATargetManifest]:
    values = draw(st.lists(_layer_values, min_size=0, max_size=5, unique=True))
    plan = ExecutionPlan(
        layers=tuple(PlannedLayer(layer_id=LayerId(v), priority=50) for v in values)
    )
    manifest = QATargetManifest(
        target_ref="repo/example",
        target_version="1.0.0",
        applicable_layers=(_AI,),
        risk_parameters={_AI: RiskParameters(weight=0.5)},
    )
    return plan, manifest


# Feature: workflow-orchestrator-skeleton, Property 8
# Property 8: determinismo da AILayerStub (Req 7.4).
# Validates: Requirements 7.4; Property 8
@settings(max_examples=100)
@given(case=_plan_and_manifest())
def test_determinismo_da_ai_layer_stub(
    case: tuple[ExecutionPlan, QATargetManifest],
) -> None:
    """O mesmo (plan, manifest) produz LayerEvidence igual em valor (Req 7.4)."""
    plan, manifest = case
    stub = _stub_with_provider()
    assert stub.execute(plan, manifest) == stub.execute(plan, manifest)


def test_evidencia_contem_identidade_e_referencia_ao_plano() -> None:
    """A evidência traz a identidade da camada e referência ao plano, sem tools externas (7.2)."""
    plan = ExecutionPlan(layers=(PlannedLayer(layer_id=_AI, priority=80),))
    manifest = QATargetManifest(
        target_ref="repo/example",
        target_version="1.0.0",
        applicable_layers=(_AI,),
        risk_parameters={_AI: RiskParameters(weight=0.5)},
    )
    evidence = _stub_with_provider().execute(plan, manifest)

    assert isinstance(evidence, LayerEvidence)
    assert evidence.layer_id == _AI
    # Referência ao plano codificada em um finding determinístico.
    assert evidence.findings and "plan=" in evidence.findings[0].detail


def test_entrada_malformada_gera_erro_sem_evidencia() -> None:
    """Plano/manifest ausente ou malformado → erro sem evidência (Req 7.5)."""
    stub = _stub_with_provider()
    manifest = QATargetManifest(target_ref="r", target_version="1")
    with pytest.raises(InvalidLayerInputError):
        stub.execute(None, manifest)  # type: ignore[arg-type]
    with pytest.raises(InvalidLayerInputError):
        stub.execute(ExecutionPlan(), None)  # type: ignore[arg-type]


def test_model_provider_ausente_fail_fast_nomeando_a_env() -> None:
    """MODEL_PROVIDER ausente interrompe a init nomeando a env (Req 12.6)."""
    resolver = SecretResolver(secrets_provider=InMemorySecretsProvider({}))
    with pytest.raises(ModelProviderNotConfiguredError) as exc_info:
        AILayerStub(resolver=resolver)
    assert "MODEL_PROVIDER" in str(exc_info.value)
