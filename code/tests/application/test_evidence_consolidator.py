"""Teste de propriedade da consolidação de evidências (Property 4).

# Feature: workflow-orchestrator-skeleton, Property 4

Property 4: Consolidação preserva origem e é invariante à ordem — qualquer
permutação da ordem de fornecimento produz ``RunResult``s iguais em valor, com a
mesma contagem e as mesmas ``layer_id`` (Requisitos 2.4, 2.6).
"""

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.application.evidence_consolidator import consolidate
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId

_layer_values = st.text(min_size=1, max_size=10).filter(lambda v: v.strip() != "")


@st.composite
def _evidences(draw: st.DrawFn) -> list[LayerEvidence]:
    """Lista de LayerEvidence com layer_id distintos (origem preservável)."""
    values = draw(st.lists(_layer_values, min_size=0, max_size=8, unique=True))
    return [
        LayerEvidence(layer_id=LayerId(v), metrics={"n": float(i)})
        for i, v in enumerate(values)
    ]


# Feature: workflow-orchestrator-skeleton, Property 4
# Property 4: Consolidação preserva origem e é invariante à ordem.
# Validates: Requirements 2.4, 2.6; Property 4
@settings(max_examples=100)
@given(evidences=_evidences(), seed=st.integers(min_value=0, max_value=10_000))
def test_consolidacao_invariante_a_ordem_e_preserva_origem(
    evidences: list[LayerEvidence], seed: int
) -> None:
    """Permutar a ordem de fornecimento produz RunResults iguais (Req 2.6)."""
    run_id = RunId("run")
    plan = ExecutionPlan()
    manifest = QATargetManifest(target_ref="target", target_version="1.0.0")

    permutada = list(evidences)
    random.Random(seed).shuffle(permutada)

    resultado_a = consolidate(run_id, manifest, plan, evidences)
    resultado_b = consolidate(run_id, manifest, plan, permutada)

    # Igualdade por valor independentemente da ordem de fornecimento (Req 2.6).
    assert resultado_a == resultado_b
    # Mesma contagem e mesmas identidades de origem preservadas (Req 2.4).
    assert len(resultado_a.evidences) == len(evidences)
    assert {e.layer_id for e in resultado_a.evidences} == {
        e.layer_id for e in evidences
    }
    # Identidade do alvo preenchida a partir do manifesto (Req 8.2/8.3).
    assert resultado_a.target_ref == manifest.target_ref
    assert resultado_a.target_version == manifest.target_version
