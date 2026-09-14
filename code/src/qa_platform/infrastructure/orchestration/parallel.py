"""Parallel_Runner: execução concorrente de QA_Layers + adapter Agno ``Parallel``.

O ``run_layers`` executa as camadas selecionadas **concorrentemente**, com no
máximo ``MAX_CONCURRENCY`` (8) camadas em execução simultânea (Requisito 4.1).
Coleta a ``LayerEvidence`` de **todas** as camadas antes de retornar (Requisito
4.2). Uma camada que falha é registrada nomeando-a e não interrompe as demais,
que concluem normalmente; o retorno é o parcial (evidências concluídas + falhas
nomeadas) (Requisito 4.3). Uma camada que ultrapassa ``LAYER_TIMEOUT_S`` (300s)
é tratada como falha por tempo excedido, nomeada, e o parcial é retornado
(Requisito 4.4). O conjunto de evidências independe da ordem de conclusão
(Requisito 4.5).

O ``build_parallel`` mapeia a execução para o ``Parallel`` da Agno, cujos tipos
ficam **confinados a este módulo de infraestrutura** — não vazam para o domínio
(Requisito 12.2).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import (
    FIRST_COMPLETED,
    Future,
    ThreadPoolExecutor,
    wait,
)
from typing import Any

from agno.workflow import Parallel, Step  # tipo da Agno CONFINADO à infraestrutura

from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.ports.qa_layer import QALayerContract
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.orchestration.registry import LayerRegistry

#: Máximo de camadas executadas simultaneamente (Requisito 4.1).
MAX_CONCURRENCY = 8
#: Tempo máximo, em segundos, que uma camada pode levar antes de ser tratada
#: como falha por tempo excedido (Requisito 4.4).
LAYER_TIMEOUT_S = 300.0


def run_layers(
    selected: Sequence[LayerId],
    registry: LayerRegistry,
    plan: ExecutionPlan,
    manifest: QATargetManifest,
    *,
    max_concurrency: int = MAX_CONCURRENCY,
    timeout_s: float = LAYER_TIMEOUT_S,
    monotonic: Callable[[], float] | None = None,
) -> tuple[list[LayerEvidence], list[str]]:
    """Executa as camadas selecionadas concorrentemente e coleta o parcial.

    Roda as camadas em um ``ThreadPoolExecutor`` limitado a ``max_concurrency``
    workers (Requisito 4.1), aguarda a conclusão de todas antes de retornar
    (Requisito 4.2) e trata falha/timeout por camada nomeando a afetada,
    deixando as demais concluírem (Requisitos 4.3, 4.4). O conjunto de
    evidências independe da ordem de conclusão (Requisito 4.5).

    O timeout é medido por um relógio monotônico injetável (``monotonic``) para
    permitir testes determinísticos com clock controlado; por padrão usa
    ``time.monotonic``.

    Args:
        selected: identidades das camadas a executar (já deduplicadas/ordenadas).
        registry: registro que resolve ``LayerId -> QA_Layer``.
        plan: plano de execução repassado a cada camada.
        manifest: manifesto de alvo repassado a cada camada.
        max_concurrency: limite de execuções simultâneas (default 8).
        timeout_s: tempo máximo por camada em segundos (default 300).
        monotonic: relógio monotônico injetável (default ``time.monotonic``).

    Returns:
        Uma tupla ``(evidences, failures)``: ``evidences`` são as
        ``LayerEvidence`` das camadas concluídas com sucesso; ``failures`` são
        strings ``"<layer_id>: <causa>"`` nomeando cada camada que falhou ou
        excedeu o tempo.
    """
    if monotonic is None:
        import time

        monotonic = time.monotonic

    if not selected:
        return [], []

    # Limita o pool ao menor entre a concorrência máxima e o nº de camadas.
    workers = max(1, min(max_concurrency, len(selected)))
    evidences: list[LayerEvidence] = []
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        start = monotonic()
        future_to_layer: dict[Future[LayerEvidence], LayerId] = {}
        for layer_id in selected:
            layer = registry.get(layer_id)
            future_to_layer[pool.submit(_execute_layer, layer, plan, manifest)] = (
                layer_id
            )

        pending: set[Future[LayerEvidence]] = set(future_to_layer)
        # Aguarda todas concluírem, coletando resultado/erro por camada e
        # aplicando o timeout global monotônico por camada pendente (Req 4.4).
        while pending:
            remaining = timeout_s - (monotonic() - start)
            if remaining <= 0:
                break
            done, pending = wait(
                pending, timeout=remaining, return_when=FIRST_COMPLETED
            )
            for future in done:
                layer_id = future_to_layer[future]
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001 - nomeia a camada afetada
                    failures.append(
                        f"{layer_id.value}: {type(exc).__name__}"
                    )  # Req 4.3
                    continue
                # Retorno não conforme ao QA_Layer_Contract (não é LayerEvidence):
                # registra como falha NOMEANDO a camada de origem, sem propagar um
                # objeto sem identidade adiante (Req 6.4). A verificação fina dos
                # campos obrigatórios continua no workflow.
                if not isinstance(result, LayerEvidence):
                    failures.append(
                        f"{layer_id.value}: retorno nao e LayerEvidence "
                        f"({type(result).__name__})"
                    )
                    continue
                evidences.append(result)

        # Camadas ainda pendentes ultrapassaram o timeout: nomeadas como falha
        # por tempo excedido; as demais já concluíram (Req 4.4).
        for future in pending:
            layer_id = future_to_layer[future]
            future.cancel()
            failures.append(f"{layer_id.value}: timeout>{timeout_s:g}s")

    return evidences, failures


def _execute_layer(
    layer: QALayerContract, plan: ExecutionPlan, manifest: QATargetManifest
) -> LayerEvidence:
    """Executa uma camada via o contrato puro ``QALayerContract``.

    Função de apoio isolada para ser submetida ao pool; delega ao ``execute`` do
    contrato, sem lógica adicional.
    """
    return layer.execute(plan, manifest)


def build_parallel(steps: Sequence[Step]) -> Parallel:
    """Monta o ``Parallel`` da Agno a partir dos steps das camadas.

    Agrupa os ``Step`` das camadas independentes em um ``Parallel`` da Agno para
    execução concorrente no ``Workflow`` (Requisitos 4.1, 4.2). Os tipos da Agno
    (``Parallel``/``Step``) ficam confinados a este módulo (Requisito 12.2).

    Args:
        steps: steps das camadas a executar concorrentemente.

    Returns:
        Um ``Parallel`` da Agno agrupando os steps fornecidos.
    """
    # Elementos são Step; o *args do Parallel espera o union de tipos da Agno.
    agno_steps: list[Any] = list(steps)
    return Parallel(*agno_steps, name="parallel_layers")
