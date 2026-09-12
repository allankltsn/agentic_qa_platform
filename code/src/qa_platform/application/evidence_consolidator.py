"""Evidence_Consolidator: Executor_Function pura que agrega as evidências.

Agrega as ``LayerEvidence`` produzidas pelas camadas de QA num único
``RunResult``, preservando a identidade de origem de cada evidência
(Requisitos 2.4, 2.6). A consolidação é invariante à ordem de fornecimento:
ordena as evidências por ``layer_id`` para produzir uma ordem total e estável,
garantindo que qualquer permutação da entrada gere um ``RunResult`` idêntico
em valor (Requisito 2.6).

Executor_Function pura: não invoca modelos de linguagem, não abre conexões de
rede e não importa framework de orquestração (Agno), parser de YAML ou
infraestrutura (Requisito 2.1). Depende exclusivamente do ``domain``.
"""

from collections.abc import Iterable

from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.value_objects.ids import RunId
from qa_platform.domain.entities.run_result import RunResult


def consolidate(
    run_id: RunId,
    manifest: QATargetManifest,
    plan: ExecutionPlan,
    evidences: Iterable[LayerEvidence],
) -> RunResult:
    """Consolida as ``LayerEvidence`` num ``RunResult`` determinístico.

    Executor_Function pura: sem LLM, sem rede (Requisito 2.1). Preserva a
    identidade de origem de cada evidência (Requisito 2.4) e é invariante à
    ordem de fornecimento — ordena por ``layer_id`` para uma ordem total e
    estável, de modo que permutações da entrada produzam ``RunResult`` iguais
    em valor (Requisito 2.6).

    Preenche a identidade do alvo (``target_ref``/``target_version``) a partir
    do ``manifest``, de modo que o laudo seja atribuível e comparável por alvo
    ao longo do tempo (Requisito 8.2). Apenas a referência e a versão do alvo
    são copiadas; os detalhes internos do alvo permanecem no manifesto de
    entrada e não entram no ``RunResult`` (Requisito 8.3).

    Args:
        run_id: identidade da execução que originou as evidências.
        manifest: manifesto do alvo de QA, fonte da identidade do alvo.
        plan: plano de execução usado na run.
        evidences: evidências das camadas, em qualquer ordem.

    Returns:
        O ``RunResult`` com a identidade do alvo preenchida e as evidências
        ordenadas de forma estável por ``layer_id``, preservando todas as
        evidências de origem.
    """
    # Ordena por layer_id para uma ordem total e estável, tornando a
    # consolidação invariante à ordem de fornecimento (Requisito 2.6).
    ordered = tuple(sorted(evidences, key=lambda e: e.layer_id.value))
    return RunResult(
        run_id=run_id,
        target_ref=manifest.target_ref,
        target_version=manifest.target_version,
        plan=plan,
        evidences=ordered,
    )
