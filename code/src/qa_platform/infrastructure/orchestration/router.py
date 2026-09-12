"""Layer_Router: seleção determinística de QA_Layers + adapter Agno ``Router``.

O ``select_layers`` é a decisão determinística de roteamento: seleciona
exatamente as camadas referenciadas pelo ``ExecutionPlan``, na ordem estável do
plano, deduplicando referências repetidas e produzindo seleção vazia para plano
vazio (Requisitos 3.1, 3.2, 3.6, 3.7, 3.8). Uma referência a camada não
registrada agrega **todas** as não registradas e encerra com ``UnknownLayerError``
sem selecionar nada, preservando o registro inalterado (Requisito 3.3). A decisão
usa **apenas** o plano e o registro — sem consultar modelo de linguagem
(Requisito 3.4).

O ``build_router`` mapeia essa seleção determinística para o ``Router`` da Agno,
cujos tipos ficam **confinados a este módulo de infraestrutura** — não vazam para
o domínio (Requisitos 12.2, 12.3). Registrar uma nova camada no ``LayerRegistry``
a torna elegível sem alterar Executor_Functions nem o Workflow (Requisito 3.5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agno.workflow import Router, Step  # tipo da Agno CONFINADO à infraestrutura
from agno.workflow.types import StepInput

from qa_platform.domain.exceptions import UnknownLayerError
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.registry import LayerRegistry


def select_layers(plan: ExecutionPlan, registry: LayerRegistry) -> list[LayerId]:
    """Seleciona deterministicamente as camadas do plano registradas.

    Percorre as camadas planejadas na ordem estável do ``ExecutionPlan``
    (Requisito 3.6), selecionando cada ``LayerId`` uma única vez mesmo que o
    plano o referencie mais de uma vez (Requisito 3.8). Camadas registradas mas
    ausentes do plano são omitidas (Requisito 3.2). Um plano vazio produz uma
    seleção vazia (Requisito 3.7). A decisão usa apenas o plano e o registro,
    sem qualquer consulta a modelo de linguagem (Requisito 3.4).

    Se o plano referenciar uma ou mais camadas não registradas, agrega **todas**
    as não registradas e levanta ``UnknownLayerError`` nomeando cada uma, sem
    selecionar nenhuma camada, deixando o registro inalterado (Requisito 3.3).

    Args:
        plan: plano de execução com as camadas a rotear (ordem estável).
        registry: registro de camadas elegíveis (ponto de extensão).

    Returns:
        Lista de ``LayerId`` selecionados, na ordem estável do plano, sem
        duplicatas. Vazia quando o plano é vazio.

    Raises:
        UnknownLayerError: quando o plano referencia uma ou mais camadas não
            registradas; nomeia cada id não correspondido de uma vez.
    """
    seen: set[str] = set()
    selected: list[LayerId] = []
    unknown: list[str] = []
    for planned in plan.layers:  # já ordenado de forma estável pelo Risk_Planner
        layer_id = planned.layer_id
        if layer_id.value in seen:
            continue  # dedupe: seleciona a camada uma única vez (Req 3.8)
        if not registry.is_registered(layer_id):
            unknown.append(layer_id.value)  # coleta não registradas (Req 3.3)
            continue
        seen.add(layer_id.value)
        selected.append(layer_id)
    if unknown:
        # Encerra sem selecionar nada, nomeando cada não registrada (Req 3.3).
        raise UnknownLayerError(unknown)
    return selected


def build_router(
    registry: LayerRegistry,
    step_factory: Callable[[LayerId], Step],
) -> Router:
    """Monta o ``Router`` da Agno cujo selector usa ``select_layers``.

    O ``Router`` da Agno recebe um ``selector`` determinístico que, a cada
    invocação, deriva do ``ExecutionPlan`` corrente a mesma seleção de camadas
    (Requisito 3.6) e mapeia cada ``LayerId`` selecionado para o ``Step`` da
    Agno correspondente, produzido por ``step_factory``. Os ``choices`` do
    ``Router`` são os ``Step`` de todas as camadas registradas; a seleção é
    exatamente o subconjunto indicado pelo plano (Requisitos 3.1, 3.2).

    Os tipos da Agno (``Router``/``Step``/``StepInput``) ficam confinados a este
    módulo — não vazam para o domínio (Requisitos 12.2, 12.3).

    Args:
        registry: registro de camadas elegíveis.
        step_factory: função pura que mapeia um ``LayerId`` para o ``Step`` da
            Agno que executa a camada correspondente.

    Returns:
        Um ``Router`` da Agno configurado com um selector determinístico.
    """
    # choices: um Step por camada registrada (todas elegíveis a seleção).
    registered_ids = sorted(registry.layer_ids(), key=lambda lid: lid.value)
    # Anotado como list[Any] apenas na fronteira da Agno: o Router espera uma
    # list invariante do union de tipos da Agno; os elementos são Step (Req 12.2).
    choices: list[Any] = [step_factory(layer_id) for layer_id in registered_ids]

    def selector(step_input: StepInput) -> list[Any]:
        """Selector determinístico: plano corrente -> Steps das camadas."""
        plan = _plan_from_step_input(step_input)
        selected = select_layers(plan, registry)
        return [step_factory(layer_id) for layer_id in selected]

    return Router(choices=choices, selector=selector, name="layer_router")


def _plan_from_step_input(step_input: StepInput) -> ExecutionPlan:
    """Extrai o ``ExecutionPlan`` corrente do ``StepInput`` da Agno.

    O Risk_Planner produz o ``ExecutionPlan`` no step anterior; o selector o
    recupera do conteúdo do step precedente. Função pura de adaptação: converte
    a entrada da Agno no value object do domínio, sem lógica de negócio.
    """
    content = step_input.previous_step_content
    if isinstance(content, ExecutionPlan):
        return content
    # Sem plano derivável: trata como plano vazio -> seleção vazia (Req 3.7).
    return ExecutionPlan()
