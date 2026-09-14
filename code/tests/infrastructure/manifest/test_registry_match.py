"""Teste de propriedade da correspondência de ids do registry (Property 10).

# Feature: workflow-orchestrator-skeleton, Property 10

Property 10: correspondência de ids nomeia cada id não correspondido — manifesto
com subconjunto não-vazio de ids desconhecidos encerra com ``UnknownLayerError``
nomeando cada um, sem executar camadas (Req 8.5). Inclui também um teste de
extensibilidade do registry (Req 3.5).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.entities.manifest import QATargetManifest, RiskParameters
from qa_platform.domain.exceptions import UnknownLayerError
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.registry import LayerRegistry

_layer_values = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8)


class _FakeLayer:
    def __init__(self, value: str) -> None:
        self._id = LayerId(value)

    @property
    def layer_id(self) -> LayerId:
        return self._id

    def execute(self, plan, manifest) -> LayerEvidence:
        return LayerEvidence(layer_id=self._id)


def _manifest(layer_values: list[str]) -> QATargetManifest:
    layers = tuple(LayerId(v) for v in layer_values)
    return QATargetManifest(
        target_ref="repo/x",
        target_version="1.0.0",
        applicable_layers=layers,
        risk_parameters={lid: RiskParameters(weight=0.5) for lid in layers},
    )


# Feature: workflow-orchestrator-skeleton, Property 10
# Property 10: correspondência de ids nomeia cada id não correspondido (Req 8.5).
# Validates: Requirements 8.5; Property 10
@settings(max_examples=100)
@given(
    registered=st.lists(_layer_values, min_size=0, max_size=4, unique=True),
    unknown=st.lists(_layer_values, min_size=1, max_size=4, unique=True),
)
def test_validate_manifest_nomeia_cada_id_desconhecido(
    registered: list[str], unknown: list[str]
) -> None:
    """Ids não registrados no manifesto → UnknownLayerError nomeando cada um (Req 8.5)."""
    unknown = [v for v in unknown if v not in registered]
    if not unknown:
        return

    registry = LayerRegistry([_FakeLayer(v) for v in registered])
    manifest = _manifest(registered + unknown)

    with pytest.raises(UnknownLayerError) as exc_info:
        registry.validate_manifest(manifest)

    for value in unknown:
        assert value in exc_info.value.layer_ids


def test_registrar_nova_camada_a_torna_elegivel() -> None:
    """Registrar uma QA_Layer nova a torna elegível sem alterar o núcleo (Req 3.5)."""
    registry = LayerRegistry([_FakeLayer("ai")])
    assert registry.is_registered(LayerId("ai"))
    assert not registry.is_registered(LayerId("security"))

    # Um novo registry com a camada extra a reconhece como elegível.
    estendido = LayerRegistry([_FakeLayer("ai"), _FakeLayer("security")])
    assert estendido.is_registered(LayerId("security"))
    # validate_manifest passa quando todas as camadas do manifesto estão registradas.
    estendido.validate_manifest(_manifest(["ai", "security"]))
