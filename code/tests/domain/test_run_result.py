"""Testes unitários de ``RunResult``, ``RunState`` e ``SkippedWork``.

Cobrem a preservação de campos e a transição funcional ``with_failure``
(Requisitos 6.5, 2.4, 4.3, 5.2).
"""

from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.run_result import (
    RunResult,
    RunState,
    SkippedWork,
    StepFailure,
)
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId


def test_run_state_with_failure_registra_step_e_causa() -> None:
    """with_failure é transição pura: novo estado com a falha ao final (Req 4.3)."""
    state = RunState(run_id=RunId("r1"))
    novo = state.with_failure("layers", "RuntimeError: x")

    # Original inalterado (imutabilidade funcional).
    assert state.failures == ()
    # Novo estado registra a falha nomeando step e causa.
    assert novo.failures == (StepFailure(step="layers", cause="RuntimeError: x"),)


def test_run_state_with_skipped_registra_trabalho_pulado() -> None:
    """with_skipped registra o salto sem mutar o estado original (Req 5.2)."""
    state = RunState(run_id=RunId("r1"))
    novo = state.with_skipped("ai", "parâmetros ausentes")

    assert state.skipped == ()
    assert novo.skipped == (SkippedWork(layer_id="ai", reason="parâmetros ausentes"),)


def test_run_result_preserva_campos() -> None:
    """RunResult preserva plano, evidências, priorização, skipped e failures (Req 2.4)."""
    ev = LayerEvidence(layer_id=LayerId("ai"))
    result = RunResult(
        run_id=RunId("r1"),
        target_ref="svc-a",
        target_version="1.0.0",
        plan=ExecutionPlan(),
        evidences=(ev,),
        prioritized=(ev,),
        skipped=(SkippedWork(layer_id="sec", reason="pulado"),),
        failures=("sec: timeout",),
    )
    assert result.run_id == RunId("r1")
    assert result.evidences == (ev,)
    assert result.prioritized == (ev,)
    assert result.skipped[0].layer_id == "sec"
    assert result.failures == ("sec: timeout",)
