"""Testes de propriedade do Layer_Router (Properties 5 e 6).

# Feature: workflow-orchestrator-skeleton, Property 5
# Feature: workflow-orchestrator-skeleton, Property 6

Property 5: seleção exata, deduplicada, ordenada e determinística (Req 3.1, 3.2,
3.6, 3.7, 3.8). Property 6: erro para camada não registrada nomeando cada uma,
sem selecionar nada (Req 3.3).
"""

from hypothesis import given, settings
from hypothesis import strategies as st
import pytest

from qa_platform.domain.entities.execution_plan import ExecutionPlan, PlannedLayer
from qa_platform.domain.exceptions import UnknownLayerError
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.registry import LayerRegistry
from qa_platform.infrastructure.orchestration.router import select_layers

_layer_values = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8)


class _FakeLayer:
    def __init__(self, value: str) -> None:
        self._id = LayerId(value)

    @property
    def layer_id(self) -> LayerId:
        return self._id

    def execute(self, plan, manifest) -> LayerEvidence:  # noqa: ANN001
        return LayerEvidence(layer_id=self._id)


def _plan(*specs: tuple[str, int]) -> ExecutionPlan:
    return ExecutionPlan(
        layers=tuple(PlannedLayer(layer_id=LayerId(v), priority=p) for v, p in specs)
    )


# Feature: workflow-orchestrator-skeleton, Property 5
# Property 5: seleção exata, deduplicada, ordenada e determinística.
# Validates: Requirements 3.1, 3.2, 3.6, 3.7, 3.8; Property 5
@settings(max_examples=100)
@given(
    values=st.lists(_layer_values, min_size=0, max_size=6, unique=True),
    dupes=st.booleans(),
)
def test_selecao_exata_deduplicada_ordenada_deterministica(
    values: list[str], dupes: bool
) -> None:
    """Seleciona exatamente as camadas do plano, uma vez, em ordem estável (Req 3.x)."""
    registry = LayerRegistry([_FakeLayer(v) for v in values])
    specs = [(v, 50) for v in values]
    if dupes:
        specs = specs + specs  # duplica todas as referências
    plan = _plan(*specs)

    resultado = select_layers(plan, registry)

    # Determinístico: mesma seleção a cada invocação (Req 3.6).
    assert select_layers(plan, registry) == resultado
    # Exata e deduplicada: cada camada aparece uma única vez (Req 3.1, 3.8).
    assert [lid.value for lid in resultado] == list(dict.fromkeys(values))
    # Plano vazio → seleção vazia (Req 3.7).
    if not values:
        assert resultado == []


# Feature: workflow-orchestrator-skeleton, Property 6
# Property 6: erro para camada não registrada nomeando cada uma (Req 3.3).
# Validates: Requirements 3.3; Property 6
@settings(max_examples=100)
@given(
    registered=st.lists(_layer_values, min_size=0, max_size=4, unique=True),
    unregistered=st.lists(_layer_values, min_size=1, max_size=4, unique=True),
)
def test_erro_para_camada_nao_registrada(
    registered: list[str], unregistered: list[str]
) -> None:
    """Plano com camadas não registradas levanta UnknownLayerError nomeando cada (Req 3.3)."""
    # Garante que as "não registradas" realmente não estão no registry.
    unregistered = [v for v in unregistered if v not in registered]
    if not unregistered:
        return  # nada a testar quando não há de fato uma não registrada

    registry = LayerRegistry([_FakeLayer(v) for v in registered])
    plan = _plan(*[(v, 50) for v in registered + unregistered])

    with pytest.raises(UnknownLayerError) as exc_info:
        select_layers(plan, registry)

    # Nomeia cada camada não registrada.
    for value in unregistered:
        assert value in exc_info.value.layer_ids
