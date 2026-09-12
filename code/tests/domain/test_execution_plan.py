"""Testes unitários de ``ExecutionPlan`` e ``PlannedLayer``.

Cobrem imutabilidade, igualdade por valor e a invariante de prioridade em
``[1, 100]`` (Requisitos 6.5, 2.2, 3.6, 12.1).
"""

import dataclasses

import pytest

from qa_platform.domain.entities.execution_plan import ExecutionPlan, PlannedLayer
from qa_platform.domain.value_objects.ids import LayerId


def _planned(layer: str, priority: int) -> PlannedLayer:
    return PlannedLayer(layer_id=LayerId(layer), priority=priority)


def test_planned_layer_rejeita_prioridade_fora_do_intervalo() -> None:
    """priority deve estar em [1, 100] (Req 2.2)."""
    with pytest.raises(ValueError):
        _planned("ai", 0)
    with pytest.raises(ValueError):
        _planned("ai", 101)


@pytest.mark.parametrize("priority", [1, 50, 100])
def test_planned_layer_aceita_limites(priority: int) -> None:
    """Aceita os extremos e o meio do intervalo válido."""
    assert _planned("ai", priority).priority == priority


def test_execution_plan_imutavel_e_comparavel_por_valor() -> None:
    """ExecutionPlan é frozen e igual por valor (Req 6.5, 3.6)."""
    plan_a = ExecutionPlan(layers=(_planned("ai", 80), _planned("security", 40)))
    plan_b = ExecutionPlan(layers=(_planned("ai", 80), _planned("security", 40)))
    assert plan_a == plan_b
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan_a.layers = ()  # type: ignore[misc]


def test_execution_plan_vazio_e_valido() -> None:
    """Um plano sem camadas é válido e igual a outro plano vazio."""
    assert ExecutionPlan() == ExecutionPlan(layers=())
