"""Testes de contrato dos ports do domínio (Requisitos 6.1, 11.1).

``QALayerContract`` é ``runtime_checkable``: uma implementação mínima é
reconhecida estruturalmente via ``isinstance``. ``RunStateStore`` é um
``Protocol`` estrutural (não runtime_checkable): verificamos que uma
implementação mínima expõe os métodos exigidos pelo contrato.
"""

from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.entities.run_result import RunResult, RunState
from qa_platform.domain.ports.qa_layer import QALayerContract
from qa_platform.domain.ports.run_state_store import RunStateStore
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId


class _MinimalLayer:
    @property
    def layer_id(self) -> LayerId:
        return LayerId("ai")

    def execute(self, plan: ExecutionPlan, manifest: QATargetManifest) -> LayerEvidence:
        return LayerEvidence(layer_id=LayerId("ai"))


class _MinimalStore:
    def start(self, run_id: RunId, state: RunState) -> None: ...
    def record_failure(self, run_id: RunId, step: str, cause: str) -> None: ...
    def save_result(self, run_id: RunId, result: RunResult) -> None: ...
    def get(self, run_id: RunId) -> RunResult:  # pragma: no cover - stub de teste
        raise NotImplementedError


def test_qa_layer_contract_e_runtime_checkable() -> None:
    """Uma implementação mínima é reconhecida como conforme ao QALayerContract (Req 6.1)."""
    assert isinstance(_MinimalLayer(), QALayerContract)


def test_objeto_incompleto_nao_e_qa_layer() -> None:
    """Objeto sem ``execute``/``layer_id`` não é reconhecido como QALayerContract."""

    class _NotALayer:
        pass

    assert not isinstance(_NotALayer(), QALayerContract)


def test_run_state_store_conformidade_estrutural() -> None:
    """Uma implementação mínima expõe todos os métodos do RunStateStore (Req 11.1)."""
    store: RunStateStore = _MinimalStore()  # aceito estruturalmente pelo type checker
    for method in ("start", "record_failure", "save_result", "get"):
        assert callable(getattr(store, method))
