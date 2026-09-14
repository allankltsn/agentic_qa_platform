"""Testes de integração do Parallel_Runner (concorrência real).

Conforme a Testing Strategy do design, a concorrência real não usa PBT — usa
testes por exemplo com camadas fake e clock/timeout controlados. Cobre: limite de
8 simultâneas (Req 4.1); coleta de todas as evidências antes do retorno (Req 4.2);
camada que falha é nomeada e as demais concluem (Req 4.3); timeout nomeia a camada
(Req 4.4).
"""

from __future__ import annotations

import threading
import time

from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.parallel import run_layers
from qa_platform.infrastructure.orchestration.registry import LayerRegistry

_MANIFEST = QATargetManifest(target_ref="repo/x", target_version="1.0.0")
_PLAN = ExecutionPlan()


class _CountingLayer:
    """Camada que registra a concorrência simultânea observada (Req 4.1)."""

    def __init__(self, value: str, tracker: _ConcurrencyTracker) -> None:
        self._id = LayerId(value)
        self._tracker = tracker

    @property
    def layer_id(self) -> LayerId:
        return self._id

    def execute(self, plan, manifest) -> LayerEvidence:
        with self._tracker.enter():
            time.sleep(0.02)  # janela para sobreposição real de threads
        return LayerEvidence(layer_id=self._id)


class _ConcurrencyTracker:
    """Rastreia o pico de execuções simultâneas de forma thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self.peak = 0

    class _Ctx:
        def __init__(self, outer: _ConcurrencyTracker) -> None:
            self._outer = outer

        def __enter__(self):
            with self._outer._lock:
                self._outer._active += 1
                self._outer.peak = max(self._outer.peak, self._outer._active)
            return self

        def __exit__(self, *exc):
            with self._outer._lock:
                self._outer._active -= 1
            return False

    def enter(self) -> _ConcurrencyTracker._Ctx:
        return self._Ctx(self)


class _FailingLayer:
    def __init__(self, value: str) -> None:
        self._id = LayerId(value)

    @property
    def layer_id(self) -> LayerId:
        return self._id

    def execute(self, plan, manifest) -> LayerEvidence:
        raise RuntimeError("falha interna")


class _SlowLayer:
    def __init__(self, value: str) -> None:
        self._id = LayerId(value)

    @property
    def layer_id(self) -> LayerId:
        return self._id

    def execute(self, plan, manifest) -> LayerEvidence:
        time.sleep(0.5)  # excede o timeout controlado do teste
        return LayerEvidence(layer_id=self._id)


def test_respeita_limite_de_concorrencia_e_coleta_todas() -> None:
    """Máx 8 simultâneas (Req 4.1) e coleta todas as evidências antes de retornar (Req 4.2)."""
    tracker = _ConcurrencyTracker()
    values = [f"l{i}" for i in range(20)]
    registry = LayerRegistry([_CountingLayer(v, tracker) for v in values])

    evidences, failures = run_layers(
        [LayerId(v) for v in values], registry, _PLAN, _MANIFEST
    )

    assert failures == []
    # Todas as 20 evidências coletadas antes de retornar (Req 4.2).
    assert {e.layer_id.value for e in evidences} == set(values)
    # Nunca ultrapassa o limite de 8 execuções simultâneas (Req 4.1).
    assert tracker.peak <= 8


def test_camada_que_falha_e_nomeada_e_demais_concluem() -> None:
    """Uma camada que falha é nomeada; as demais concluem (Req 4.3)."""
    registry = LayerRegistry(
        [_CountingLayer("ok", _ConcurrencyTracker()), _FailingLayer("bad")]
    )

    evidences, failures = run_layers(
        [LayerId("ok"), LayerId("bad")], registry, _PLAN, _MANIFEST
    )

    assert {e.layer_id.value for e in evidences} == {"ok"}
    assert any("bad" in f for f in failures)


def test_timeout_nomeia_a_camada_e_retorna_parcial() -> None:
    """Camada que excede o timeout é nomeada como timeout; as demais concluem (Req 4.4)."""
    registry = LayerRegistry(
        [_CountingLayer("fast", _ConcurrencyTracker()), _SlowLayer("slow")]
    )

    # timeout curto força a camada lenta a estourar de forma determinística.
    evidences, failures = run_layers(
        [LayerId("fast"), LayerId("slow")],
        registry,
        _PLAN,
        _MANIFEST,
        timeout_s=0.1,
    )

    assert {e.layer_id.value for e in evidences} == {"fast"}
    assert any("slow" in f and "timeout" in f for f in failures)
