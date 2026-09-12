"""Teste unitário do Feedback_Dispatcher (Executor_Function).

Verifica que ``dispatch`` apenas encaminha o ``RunResult`` ao sink plugável,
chamando ``sink.emit`` exatamente uma vez com o resultado recebido, sem
qualquer integração externa (Requisito 2.1). Usa um sink fake in-memory que
registra os resultados emitidos.
"""

from qa_platform.application.feedback_dispatcher import FeedbackSink, dispatch
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.value_objects.ids import RunId
from qa_platform.domain.entities.run_result import RunResult


class _RecordingSink:
    """Sink fake in-memory que registra os ``RunResult`` emitidos."""

    def __init__(self) -> None:
        self.emitted: list[RunResult] = []

    def emit(self, result: RunResult) -> None:
        self.emitted.append(result)


def _make_run_result() -> RunResult:
    return RunResult(
        run_id=RunId("run-1"),
        target_ref="target",
        target_version="1.0.0",
        plan=ExecutionPlan(layers=()),
    )


def test_dispatch_forwards_result_to_sink_exactly_once() -> None:
    """dispatch chama sink.emit uma vez com o RunResult recebido (Req 2.1)."""
    sink = _RecordingSink()
    result = _make_run_result()

    dispatch(result, sink)

    assert sink.emitted == [result]
    assert sink.emitted[0] is result


def test_recording_sink_is_a_feedback_sink() -> None:
    """O sink fake satisfaz estruturalmente o Protocol FeedbackSink (Req 2.1)."""
    assert isinstance(_RecordingSink(), FeedbackSink)
