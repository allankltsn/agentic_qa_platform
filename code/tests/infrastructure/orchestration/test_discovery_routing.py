"""Teste de propriedade — ``discovery`` é documental e não altera roteamento.

# Feature: hybrid-target-discovery, Property 11

Property 11: o bloco ``discovery`` do ``QATargetManifest`` é advisory/documental
(Requisito 4.6). Sua presença ou conteúdo não pode influenciar a decisão de
roteamento produzida pelo pipeline Risk_Planner → Layer_Router. Para qualquer
manifesto válido ``M``, ``select_layers(plan_by_risk(M))`` deve ser idêntico quer
o ``discovery`` esteja vazio (``DiscoveryInfo.empty()``) quer esteja arbitrário/
populado com frameworks/tools/prompts/rag.
"""

from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.application.risk_planner import plan_by_risk
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest, RiskParameters
from qa_platform.domain.value_objects.discovery import (
    DetectedItem,
    DiscoveryInfo,
    Framework,
)
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.registry import LayerRegistry
from qa_platform.infrastructure.orchestration.router import select_layers

# Valores de LayerId: strings não-vazias e não compostas apenas por espaços,
# restringindo ao espaço de entrada aceito por LayerId.
_layer_id_values = st.text(min_size=1, max_size=12).filter(lambda v: v.strip() != "")

# Pesos de risco finitos e não-negativos, produzindo prioridade válida em [1, 100].
_weights = st.floats(
    min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False
)


class _FakeLayer:
    """QA_Layer mínima usada só para registrar identidades no ``LayerRegistry``.

    Satisfaz estruturalmente o ``QALayerContract`` (``layer_id`` + ``execute``),
    sem tocar em Agno nem em rede — o roteamento consulta apenas a identidade.
    """

    def __init__(self, value: str) -> None:
        self._id = LayerId(value)

    @property
    def layer_id(self) -> LayerId:
        return self._id

    def execute(self, plan: ExecutionPlan, manifest: QATargetManifest) -> LayerEvidence:
        return LayerEvidence(layer_id=self._id)


_detected_items = st.builds(
    DetectedItem,
    identifier=st.text(min_size=1, max_size=12),
    source=st.text(min_size=1, max_size=16),
)


@st.composite
def _arbitrary_discovery(draw: st.DrawFn) -> DiscoveryInfo:
    """Gera um ``DiscoveryInfo`` arbitrário/populado (não vazio, tipicamente).

    Cobre framework único, ambíguo ou não detectado, além de coleções de
    tools/prompts/rag de tamanho variável — o espaço que um discovery real
    poderia assumir.
    """
    frameworks = draw(
        st.lists(st.sampled_from(list(Framework)), min_size=0, max_size=3, unique=True)
    )
    return DiscoveryInfo(
        framework=draw(st.sampled_from(list(Framework))),
        frameworks_detected=tuple(frameworks),
        ambiguous=draw(st.booleans()),
        tools=tuple(draw(st.lists(_detected_items, min_size=0, max_size=4))),
        prompts=tuple(draw(st.lists(_detected_items, min_size=0, max_size=4))),
        rag=tuple(draw(st.lists(_detected_items, min_size=0, max_size=4))),
        fragility_note=draw(st.text(min_size=0, max_size=32)),
    )


@st.composite
def _valid_manifest_with_discovery(
    draw: st.DrawFn,
) -> tuple[QATargetManifest, DiscoveryInfo]:
    """Gera um manifesto válido para o Risk_Planner + um ``DiscoveryInfo`` arbitrário.

    O manifesto tem ao menos uma camada aplicável com ``LayerId`` distintos e
    ``risk_parameters`` cobrindo exatamente essas camadas (evitando o
    ``InvalidManifestError``). O ``discovery`` do manifesto nasce vazio; o
    ``DiscoveryInfo`` arbitrário é devolvido à parte para montar a variante.
    """
    layer_values = draw(st.lists(_layer_id_values, min_size=1, max_size=8, unique=True))
    applicable_layers = tuple(LayerId(value) for value in layer_values)
    risk_parameters = {
        layer_id: RiskParameters(weight=draw(_weights))
        for layer_id in applicable_layers
    }
    target_ref = draw(st.text(min_size=1, max_size=16).filter(lambda v: v.strip()))
    target_version = draw(st.text(min_size=1, max_size=8).filter(lambda v: v.strip()))
    manifest = QATargetManifest(
        target_ref=target_ref,
        target_version=target_version,
        applicable_layers=applicable_layers,
        risk_parameters=risk_parameters,
    )
    return manifest, draw(_arbitrary_discovery())


# Feature: hybrid-target-discovery, Property 11
# Property 11: discovery é documental e não altera o roteamento.
# Validates: Requirements 4.6; Property 11
@settings(max_examples=100)
@given(payload=_valid_manifest_with_discovery())
def test_discovery_nao_altera_roteamento(
    payload: tuple[QATargetManifest, DiscoveryInfo],
) -> None:
    """Presença/conteúdo de ``discovery`` não muda ``select_layers(plan_by_risk(M))``.

    Constrói dois manifestos idênticos exceto pelo campo ``discovery`` (vazio vs.
    arbitrário) e afirma que a seleção de camadas do Layer_Router é a mesma para
    ambos — provando o caráter advisory do discovery (Req 4.6).
    """
    manifest, discovery = payload

    manifest_empty = replace(manifest, discovery=DiscoveryInfo.empty())
    manifest_discovery = replace(manifest, discovery=discovery)

    # Registro cobre exatamente as camadas aplicáveis → sem UnknownLayerError.
    registry = LayerRegistry(
        [_FakeLayer(layer_id.value) for layer_id in manifest.applicable_layers]
    )

    routing_empty = select_layers(plan_by_risk(manifest_empty), registry)
    routing_discovery = select_layers(plan_by_risk(manifest_discovery), registry)

    # O roteamento é idêntico independentemente do bloco discovery (Req 4.6).
    assert routing_empty == routing_discovery
    assert [lid.value for lid in routing_empty] == [
        lid.value for lid in routing_discovery
    ]
