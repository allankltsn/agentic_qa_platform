"""Advisory_Judge: Executor_Function determinística de priorização advisory.

Prioriza as evidências consolidadas de um ``RunResult`` por severidade máxima,
em ordem decrescente e estável, preservando TODAS as evidências de origem
(mesma contagem e identidade). É estritamente advisory (Requisito 10.4): NÃO
emite veredito pass/fail — apenas produz uma ordenação em ``prioritized``,
mantendo ``evidences`` intacto.

Executor_Function pura: não invoca modelos de linguagem, não abre conexões de
rede e não importa framework de orquestração (Agno), parser de YAML ou
infraestrutura (Requisito 10.5). Depende exclusivamente do ``domain``.

Determinismo (Requisitos 10.2, 10.3): a ordenação usa uma ordem total —
severidade máxima decrescente e, como desempate, ``layer_id.value`` crescente —
de modo que a mesma entrada produza sempre a mesma priorização.
"""

from dataclasses import replace

from qa_platform.domain.entities.run_result import RunResult
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.severity import Severity


def _max_severity(evidence: LayerEvidence) -> Severity:
    """Retorna a maior severidade entre os achados de ``evidence``.

    Evidência sem achados tem severidade máxima ``INFO`` (a menor da ordem
    total), garantindo uma chave de ordenação bem definida (Requisito 10.1).

    Args:
        evidence: evidência de uma camada de QA.

    Returns:
        A ``Severity`` máxima entre ``evidence.findings``; ``Severity.INFO``
        quando não há achados.
    """
    return max(
        (finding.severity for finding in evidence.findings),
        default=Severity.INFO,
    )


def prioritize(result: RunResult) -> RunResult:
    """Prioriza as evidências por severidade máxima, sem emitir veredito.

    Executor_Function pura e determinística: sem LLM, sem rede (Requisito
    10.5). Ordena ``result.evidences`` por severidade máxima decrescente, de
    forma estável, usando ``layer_id.value`` crescente como desempate para uma
    ordem total (Requisitos 10.1, 10.2). Preserva TODAS as evidências de origem
    — mesma contagem e identidade — em ``evidences``, adicionando a ordenação
    em ``prioritized`` (Requisito 10.3). NÃO emite pass/fail (Requisito 10.4).
    Um ``RunResult`` sem evidências produz ``prioritized`` vazio, sem erro.

    Args:
        result: resultado consolidado da run com as evidências a priorizar.

    Returns:
        Um novo ``RunResult`` igual ao de entrada, com ``prioritized``
        preenchido pela ordenação advisory. Nenhum campo de veredito é criado.
    """
    prioritized = tuple(
        sorted(
            result.evidences,
            key=lambda evidence: (
                -int(_max_severity(evidence)),
                evidence.layer_id.value,
            ),
        )
    )
    # replace preserva os demais campos, incluindo a identidade do alvo
    # (target_ref/target_version), obrigatória no RunResult (Req 8.1).
    return replace(result, prioritized=prioritized)
