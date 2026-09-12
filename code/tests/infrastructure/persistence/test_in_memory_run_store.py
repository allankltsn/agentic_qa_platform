"""Testes de propriedade do InMemoryRunStateStore (Properties 13, 14, 15).

# Feature: workflow-orchestrator-skeleton, Property 13
# Feature: workflow-orchestrator-skeleton, Property 14
# Feature: workflow-orchestrator-skeleton, Property 15

Round-trip persistir→recuperar (Req 11.2/11.4/11.7); Run_Id duplicado não
sobrescreve e sinaliza conflito (Req 11.3); Run_Id inexistente sinaliza ausência
(Req 11.5).
"""

from hypothesis import given, settings
from hypothesis import strategies as st
import pytest

from qa_platform.domain.entities.execution_plan import ExecutionPlan, PlannedLayer
from qa_platform.domain.entities.run_result import RunResult
from qa_platform.domain.exceptions import RunIdConflictError, RunNotFoundError
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId
from qa_platform.infrastructure.persistence.in_memory_run_store import (
    InMemoryRunStateStore,
)

_run_id_values = st.text(min_size=1, max_size=16).filter(lambda v: v.strip() != "")
_layer_values = st.text(min_size=1, max_size=8).filter(lambda v: v.strip() != "")


@st.composite
def _run_results(draw: st.DrawFn, run_id: RunId) -> RunResult:
    values = draw(st.lists(_layer_values, min_size=0, max_size=4, unique=True))
    plan = ExecutionPlan(
        layers=tuple(PlannedLayer(layer_id=LayerId(v), priority=50) for v in values)
    )
    evidences = tuple(LayerEvidence(layer_id=LayerId(v)) for v in values)
    return RunResult(
        run_id=run_id,
        target_ref="target",
        target_version="1.0.0",
        plan=plan,
        evidences=evidences,
    )


# Feature: workflow-orchestrator-skeleton, Property 13
# Property 13: Round-trip persistir → recuperar (Req 11.2, 11.4, 11.7).
# Validates: Requirements 11.2, 11.4, 11.7; Property 13
@settings(max_examples=100)
@given(value=_run_id_values, data=st.data())
def test_round_trip_persistir_recuperar(value: str, data: st.DataObject) -> None:
    """save_result → get retorna RunResult igual em valor (Req 11.2/11.4)."""
    run_id = RunId(value)
    result = data.draw(_run_results(run_id))
    store = InMemoryRunStateStore()

    store.save_result(run_id, result)
    assert store.get(run_id) == result


# Feature: workflow-orchestrator-skeleton, Property 14
# Property 14: Run_Id duplicado não sobrescreve e sinaliza conflito (Req 11.3).
# Validates: Requirements 11.3; Property 14
@settings(max_examples=100)
@given(value=_run_id_values, data=st.data())
def test_run_id_duplicado_sinaliza_conflito_sem_sobrescrever(
    value: str, data: st.DataObject
) -> None:
    """Segundo save_result com mesmo id levanta RunIdConflictError; get mantém original (Req 11.3)."""
    run_id = RunId(value)
    original = data.draw(_run_results(run_id))
    outro = RunResult(
        run_id=run_id,
        target_ref="target",
        target_version="1.0.0",
        plan=ExecutionPlan(),
        failures=("x",),
    )
    store = InMemoryRunStateStore()

    store.save_result(run_id, original)
    with pytest.raises(RunIdConflictError) as exc_info:
        store.save_result(run_id, outro)

    assert value in str(exc_info.value)
    # get posterior retorna o resultado original, inalterado.
    assert store.get(run_id) == original


# Feature: workflow-orchestrator-skeleton, Property 15
# Property 15: Run_Id inexistente sinaliza ausência (Req 11.5).
# Validates: Requirements 11.5; Property 15
@settings(max_examples=100)
@given(value=_run_id_values)
def test_run_id_inexistente_sinaliza_ausencia(value: str) -> None:
    """get de id nunca persistido levanta RunNotFoundError nomeando o id (Req 11.5)."""
    store = InMemoryRunStateStore()
    with pytest.raises(RunNotFoundError) as exc_info:
        store.get(RunId(value))
    assert value in str(exc_info.value)
