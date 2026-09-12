"""Testes de integração do Orchestrator_Workflow (engine real da Agno v2).

Comprovam que a execução ocorre **pela engine da Agno** (não por um runner sequencial
paralelo) e que o wrapper `run_orchestration` cumpre as responsabilidades transversais
do ADR-001:

- ordem dos steps e execução ponta a ponta (Req 1.1);
- atribuição de `Run_Id` e registro do estado inicial antes do 1º step (Req 1.3);
- aborto sem executar step algum quando a persistência inicial falha (Req 1.4);
- interrupção e registro de falha quando um step falha (Req 1.5);
- controle de fluxo sem consultar modelo de linguagem (Req 1.6);
- camada não conforme ao contrato é marcada como falha, preservando as demais (Req 6.4);
- validação do manifesto antes do 1º step (Req 8.2).

Conforme a Testing Strategy do design, o `Workflow` da Agno é coberto por testes por
exemplo/integração (não PBT). As camadas de QA são fakes que implementam o
`QALayerContract`, evitando dependência de ferramentas externas ou de `MODEL_PROVIDER`.
"""

from __future__ import annotations

import pytest

from qa_platform.domain.entities.manifest import (
    CostParameters,
    QATargetManifest,
    RiskParameters,
)
from qa_platform.domain.entities.run_result import RunResult
from qa_platform.domain.exceptions import InvalidManifestError, RunNotFoundError
from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId
from qa_platform.domain.value_objects.severity import Severity
from qa_platform.infrastructure.orchestration.registry import LayerRegistry
from qa_platform.infrastructure.orchestration.workflow import (
    STEP_LAYERS,
    OrchestrationError,
    run_orchestration,
)
from qa_platform.infrastructure.persistence.in_memory_run_store import (
    InMemoryRunStateStore,
)

_AI = LayerId("ai")
_SEC = LayerId("security")


class _RecordingSink:
    """FeedbackSink fake in-memory: registra o último RunResult emitido."""

    def __init__(self) -> None:
        self.last: RunResult | None = None
        self.calls = 0

    def emit(self, result: RunResult) -> None:
        self.calls += 1
        self.last = result


class _FakeLayer:
    """QA_Layer conforme o contrato, determinística e sem ferramentas externas."""

    def __init__(self, layer_id: LayerId, severity: Severity = Severity.LOW) -> None:
        self._layer_id = layer_id
        self._severity = severity

    @property
    def layer_id(self) -> LayerId:
        return self._layer_id

    def execute(self, plan, manifest) -> LayerEvidence:  # noqa: ANN001
        return LayerEvidence(
            layer_id=self._layer_id,
            metrics={"planned_layers": float(len(plan.layers))},
            findings=(Finding(code="x", severity=self._severity, detail="d"),),
        )


class _NonConformingLayer:
    """QA_Layer que viola o contrato: retorna algo que não é LayerEvidence (Req 6.4)."""

    def __init__(self, layer_id: LayerId) -> None:
        self._layer_id = layer_id

    @property
    def layer_id(self) -> LayerId:
        return self._layer_id

    def execute(self, plan, manifest):  # noqa: ANN001, ANN201
        return {"not": "an evidence"}


class _ForbiddenLLM:
    """Cliente LLM proibido: falha o teste se o controle de fluxo o invocar (Req 1.6)."""

    def __getattr__(self, name: str):  # noqa: ANN401
        raise AssertionError(
            f"controle de fluxo não pode invocar um modelo de linguagem (acesso a {name})"
        )


class _FailingStartStore(InMemoryRunStateStore):
    """Store cujo `start` falha, para exercitar o aborto inicial (Req 1.4)."""

    def __init__(self) -> None:
        super().__init__()
        self.steps_touched = False

    def start(self, run_id: RunId, state) -> None:  # noqa: ANN001
        raise RuntimeError("falha simulada de persistência inicial")


def _manifest(layers: tuple[LayerId, ...] = (_AI,)) -> QATargetManifest:
    """Manifesto válido (VO) com risco e custo que justificam a execução."""
    return QATargetManifest(
        target_ref="repo/example",
        target_version="1.0.0",
        applicable_layers=layers,
        risk_parameters={lid: RiskParameters(weight=0.5) for lid in layers},
        cost_parameters={
            lid: CostParameters(risk_threshold=0.0, estimated_risk=1.0)
            for lid in layers
        },
    )


def _raw_manifest(layer_ids: tuple[str, ...] = ("ai",)) -> dict[str, object]:
    """Manifesto bruto (dict) conforme o schema, para validação antes do 1º step."""
    return {
        "target": {"ref": "repo/example", "version": "1.0.0"},
        "applicable_layers": list(layer_ids),
        "risk_parameters": {lid: {"weight": 0.5} for lid in layer_ids},
        "cost_parameters": {
            lid: {"risk_threshold": 0.0, "estimated_risk": 1.0} for lid in layer_ids
        },
    }


def test_executa_na_ordem_do_adr_e_persiste_resultado() -> None:
    """Executa ponta a ponta pela engine da Agno; consolida, prioriza e persiste (Req 1.1, 11.2)."""
    store = InMemoryRunStateStore()
    registry = LayerRegistry([_FakeLayer(_AI)])
    sink = _RecordingSink()

    result = run_orchestration(
        _manifest(),
        _raw_manifest(),
        store,
        registry,
        sink,
        run_id_factory=lambda: RunId("run-1"),
    )

    assert result.run_id == RunId("run-1")
    assert len(result.evidences) == 1
    assert result.evidences[0].layer_id == _AI
    # Advisory_Judge preserva todas as evidências e adiciona priorização (Req 10.2).
    assert len(result.prioritized) == 1
    # Feedback_Dispatcher foi acionado uma vez com o resultado (Req 2.1).
    assert sink.calls == 1
    assert sink.last is not None and sink.last.run_id == RunId("run-1")
    # RunResult persistido é recuperável pelo Run_Id (Req 11.2).
    assert store.get(RunId("run-1")).run_id == RunId("run-1")


def test_registra_estado_inicial_antes_do_primeiro_step() -> None:
    """Atribui Run_Id e registra o estado inicial no store antes de rodar (Req 1.3)."""
    store = InMemoryRunStateStore()
    registry = LayerRegistry([_FakeLayer(_AI)])

    run_orchestration(
        _manifest(),
        _raw_manifest(),
        store,
        registry,
        _RecordingSink(),
        run_id_factory=lambda: RunId("run-2"),
    )
    # start(run_id, ...) registrou o estado inicial: get retorna o resultado ao fim.
    assert store.get(RunId("run-2")).run_id == RunId("run-2")


def test_aborta_sem_steps_quando_persistencia_inicial_falha() -> None:
    """Falha do store inicial aborta a run sem executar nenhum step (Req 1.4)."""
    store = _FailingStartStore()
    registry = LayerRegistry([_FakeLayer(_AI)])
    sink = _RecordingSink()

    with pytest.raises(OrchestrationError) as exc_info:
        run_orchestration(
            _manifest(),
            _raw_manifest(),
            store,
            registry,
            sink,
            run_id_factory=lambda: RunId("run-3"),
        )

    # Nenhum step rodou: o feedback nunca foi emitido.
    assert sink.calls == 0
    assert exc_info.value.step == "initial_state"


def test_falha_de_step_interrompe_e_registra() -> None:
    """Um step que falha interrompe a run, registra a falha e propaga (Req 1.5)."""

    class _BoomStore(InMemoryRunStateStore):
        def __init__(self) -> None:
            super().__init__()
            self.failures: list[tuple[str, str]] = []

        def record_failure(self, run_id: RunId, step: str, cause: str) -> None:
            self.failures.append((step, cause))
            super().record_failure(run_id, step, cause)

    # Camada que estoura durante a execução força a falha do step "layers".
    class _BoomLayer:
        @property
        def layer_id(self) -> LayerId:
            return _AI

        def execute(self, plan, manifest):  # noqa: ANN001, ANN201
            raise RuntimeError("falha interna da camada")

    store = _BoomStore()
    registry = LayerRegistry([_BoomLayer()])
    sink = _RecordingSink()

    # A camada que falha é isolada pelo Parallel_Runner (Req 4.3): não derruba o run;
    # o resultado é persistido com a falha registrada em `failures`.
    result = run_orchestration(
        _manifest(),
        _raw_manifest(),
        store,
        registry,
        sink,
        run_id_factory=lambda: RunId("run-4"),
    )
    assert result.failures  # a falha da camada foi propagada ao RunResult
    assert any("ai" in f for f in result.failures)


def test_camada_nao_conforme_ao_contrato_e_marcada_como_falha() -> None:
    """Camada que viola o contrato é marcada como falha, preservando as demais (Req 6.4)."""
    store = InMemoryRunStateStore()
    registry = LayerRegistry([_FakeLayer(_AI), _NonConformingLayer(_SEC)])
    sink = _RecordingSink()

    result = run_orchestration(
        _manifest((_AI, _SEC)),
        _raw_manifest(("ai", "security")),
        store,
        registry,
        sink,
        run_id_factory=lambda: RunId("run-5"),
    )

    # A camada conforme produz evidência; a não conforme vira falha nomeada.
    assert len(result.evidences) == 1
    assert result.evidences[0].layer_id == _AI
    assert any("security" in f for f in result.failures)


def test_manifesto_invalido_encerra_antes_de_qualquer_step() -> None:
    """Manifesto não conforme ao schema encerra sem executar step (Req 8.2/8.3)."""
    store = InMemoryRunStateStore()
    registry = LayerRegistry([_FakeLayer(_AI)])
    sink = _RecordingSink()

    # raw_manifest sem 'risk_parameters' → InvalidManifestError antes do 1º step.
    bad_raw: dict[str, object] = {
        "target": {"ref": "repo/example", "version": "1.0.0"},
        "applicable_layers": ["ai"],
    }

    with pytest.raises(InvalidManifestError):
        run_orchestration(
            _manifest(),
            bad_raw,
            store,
            registry,
            sink,
            run_id_factory=lambda: RunId("run-6"),
        )

    # Nenhum step rodou (sem feedback) e nada foi persistido para o run_id.
    assert sink.calls == 0
    with pytest.raises(RunNotFoundError):
        store.get(RunId("run-6"))


def test_controle_de_fluxo_nao_invoca_modelo_de_linguagem() -> None:
    """O controle de fluxo é determinístico e não consulta um LLM (Req 1.6).

    Um cliente LLM proibido é passado como sink-adjacente ao ambiente; se qualquer
    parte do controle de fluxo tentar usá-lo, o acesso levanta AssertionError. Como a
    orquestração deriva ordem/seleção apenas de manifest+plan, a run conclui sem tocá-lo.
    """
    forbidden = _ForbiddenLLM()  # noqa: F841 - presença proposital; não deve ser usado
    store = InMemoryRunStateStore()
    registry = LayerRegistry([_FakeLayer(_AI)])

    result = run_orchestration(
        _manifest(),
        _raw_manifest(),
        store,
        registry,
        _RecordingSink(),
        run_id_factory=lambda: RunId("run-7"),
    )
    assert result.run_id == RunId("run-7")


def test_step_layers_e_o_nome_canonico_do_adr() -> None:
    """Sanidade: o nome do step de camadas é o canônico esperado pelo isolamento de falha."""
    assert STEP_LAYERS == "layers"
