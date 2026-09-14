"""LayerRegistry: ponto de extensão do roteamento de QA_Layers (infra).

O ``LayerRegistry`` mapeia ``LayerId -> QA_Layer`` e é o único ponto de extensão
para tornar uma nova ``QA_Layer`` elegível ao roteamento: registrar uma camada
que implementa o ``QALayerContract`` a torna disponível sem alterar os
Executor_Functions nem o Orchestrator_Workflow (Requisito 3.5).

Expõe consulta por identidade (``is_registered``, ``get``) e a validação das
identidades declaradas em um ``QATargetManifest`` contra as camadas registradas
(``validate_manifest``): cada id aplicável deve corresponder exatamente a uma
identidade registrada (Requisito 8.4) e, havendo ids não correspondidos, agrega
**todos** eles em um único ``UnknownLayerError`` nomeando cada um (Requisito 8.5).

Código de infraestrutura puro: não importa o framework de orquestração (Agno) —
os tipos da Agno ficam confinados aos primitivos (router/workflow) deste pacote.
"""

from __future__ import annotations

from collections.abc import Iterable

from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.exceptions import UnknownLayerError
from qa_platform.domain.ports.qa_layer import QALayerContract
from qa_platform.domain.value_objects.ids import LayerId


class LayerRegistry:
    """Registro imutável por construção de ``QA_Layer`` por ``LayerId``.

    Constrói um mapa interno ``LayerId -> QALayerContract`` a partir de uma
    iterável de camadas. Cada camada deve expor uma identidade única; registrar
    duas camadas com a mesma identidade é um erro de programação e é rejeitado na
    construção. Depois de construído, o registro só é consultado — o que garante
    seleção determinística e estado inalterado entre consultas.

    Registrar uma nova camada (via construção do registro) a torna elegível ao
    roteamento sem qualquer alteração nos Executor_Functions ou no
    Orchestrator_Workflow: o registro é o ponto de extensão (Requisito 3.5).
    """

    def __init__(self, layers: Iterable[QALayerContract] = ()) -> None:
        """Cria o registro a partir de uma iterável de ``QA_Layer``.

        Args:
            layers: camadas que implementam o ``QALayerContract``. Cada uma é
                indexada por sua ``layer_id``.

        Raises:
            ValueError: se duas camadas declararem a mesma ``layer_id``.
        """
        registry: dict[LayerId, QALayerContract] = {}
        for layer in layers:
            layer_id = layer.layer_id
            if layer_id in registry:
                raise ValueError(
                    f"Camada duplicada para a identidade: {layer_id.value}"
                )
            registry[layer_id] = layer
        self._layers: dict[LayerId, QALayerContract] = registry

    def layer_ids(self) -> tuple[LayerId, ...]:
        """Retorna as identidades de todas as camadas registradas.

        Consulta pura: não altera o estado do registro. Usada pelo
        ``build_router`` para enumerar as camadas elegíveis (``choices`` do
        ``Router`` da Agno).
        """
        return tuple(self._layers.keys())

    def is_registered(self, layer_id: LayerId) -> bool:
        """Indica se ``layer_id`` corresponde a uma camada registrada.

        Consulta pura: não altera o estado do registro.
        """
        return layer_id in self._layers

    def get(self, layer_id: LayerId) -> QALayerContract:
        """Retorna a ``QA_Layer`` registrada para ``layer_id``.

        Args:
            layer_id: identidade da camada procurada.

        Returns:
            A ``QA_Layer`` (``QALayerContract``) associada a ``layer_id``.

        Raises:
            UnknownLayerError: se ``layer_id`` não estiver registrado; nomeia o
                id não correspondido.
        """
        try:
            return self._layers[layer_id]
        except KeyError:
            raise UnknownLayerError([layer_id.value]) from None

    def validate_manifest(self, manifest: QATargetManifest) -> None:
        """Valida que cada camada aplicável do manifest está registrada.

        Verifica **todas** as ``applicable_layers`` do ``manifest`` contra as
        identidades registradas. Cada id aplicável deve corresponder exatamente a
        uma camada registrada (Requisito 8.4). Havendo ids não correspondidos,
        não falha no primeiro: agrega **todos** eles e levanta um único
        ``UnknownLayerError`` nomeando cada id não correspondido (Requisito 8.5).
        Quando todas as identidades correspondem, retorna normalmente.

        Args:
            manifest: manifesto cujas camadas aplicáveis serão verificadas.

        Raises:
            UnknownLayerError: quando uma ou mais ``applicable_layers`` não
                estão registradas; nomeia cada id não correspondido de uma vez.
        """
        unmatched = [
            layer_id.value
            for layer_id in manifest.applicable_layers
            if layer_id not in self._layers
        ]
        if unmatched:
            raise UnknownLayerError(unmatched)
