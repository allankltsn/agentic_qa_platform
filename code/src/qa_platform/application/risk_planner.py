"""Risk_Planner: Executor_Function pura que planeja a execução por risco.

A partir de um ``QATargetManifest`` válido, deriva de forma determinística um
``ExecutionPlan`` que lista as camadas aplicáveis, cada uma com uma prioridade
inteira no intervalo ``[1, 100]`` derivada dos parâmetros de risco do manifesto
(Requisitos 2.1, 2.2). O plano é ordenado de forma estável e total, garantindo
que o mesmo manifesto produza planos byte-a-byte idênticos entre invocações
(Requisitos 2.5, 3.6, 1.2).

Executor_Function pura: não invoca modelos de linguagem, não abre conexões de
rede e não importa framework de orquestração (Agno), parser de YAML ou
infraestrutura (Requisito 2.1). Depende exclusivamente do ``domain``.
"""

from qa_platform.domain.exceptions import InvalidManifestError
from qa_platform.domain.entities.execution_plan import (
    PRIORITY_MAX,
    PRIORITY_MIN,
    ExecutionPlan,
    PlannedLayer,
)
from qa_platform.domain.entities.manifest import QATargetManifest, RiskParameters

# Fator de escala do peso de risco para a prioridade inteira. O peso é um valor
# relativo não-negativo; multiplicá-lo por 100 e arredondar produz uma prioridade
# proporcional, sempre saturada no intervalo válido [1, 100].
_PRIORITY_SCALE = 100.0


def _derive_priority(params: RiskParameters) -> int:
    """Deriva uma prioridade inteira em ``[1, 100]`` do peso de risco.

    Função pura e determinística: escala o ``weight`` e satura o resultado no
    intervalo válido (Requisito 2.2). Como ``PlannedLayer`` já valida o
    intervalo, garantimos aqui que o valor esteja sempre em ``[1, 100]``.
    """
    scaled = round(params.weight * _PRIORITY_SCALE)
    return max(PRIORITY_MIN, min(PRIORITY_MAX, scaled))


def plan_by_risk(manifest: QATargetManifest) -> ExecutionPlan:
    """Deriva o ``ExecutionPlan`` determinístico a partir do manifesto.

    Executor_Function pura: sem LLM, sem rede (Requisito 2.1) e determinística
    (Requisitos 1.2, 2.5). Deriva a prioridade de cada camada aplicável dos
    parâmetros de risco e ordena de forma estável por prioridade decrescente e,
    em empate, por ``layer_id`` crescente (Requisitos 2.2, 3.6).

    Rejeita manifesto inválido ou sem parâmetros de risco levantando
    ``InvalidManifestError`` que nomeia o campo problemático, sem produzir um
    plano (Requisito 2.3).

    Args:
        manifest: manifesto de alvo já parseado e validado.

    Returns:
        O ``ExecutionPlan`` com as camadas aplicáveis ordenadas de forma
        estável.

    Raises:
        InvalidManifestError: quando não há parâmetros de risco ou quando uma
            camada aplicável não possui parâmetros de risco correspondentes.
    """
    if not manifest.risk_parameters:
        raise InvalidManifestError(
            {"risk_parameters": "parâmetros de risco ausentes"}  # Req 2.3
        )

    invalid_fields: dict[str, str] = {}
    planned: list[PlannedLayer] = []
    for layer_id in manifest.applicable_layers:
        params = manifest.risk_parameters_for(layer_id)
        if params is None:
            invalid_fields[f"risk_parameters[{layer_id.value}]"] = (
                "parâmetros de risco ausentes para a camada aplicável"
            )
            continue
        priority = _derive_priority(params)
        planned.append(PlannedLayer(layer_id=layer_id, priority=priority))

    if invalid_fields:
        raise InvalidManifestError(invalid_fields)  # Req 2.3

    # Ordenação estável e total: prioridade desc, depois layer_id asc. Garante
    # determinismo byte-a-byte entre invocações (Requisitos 2.5, 3.6, 1.2).
    planned.sort(key=lambda p: (-p.priority, p.layer_id.value))
    return ExecutionPlan(layers=tuple(planned))
