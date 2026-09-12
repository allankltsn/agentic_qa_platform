"""ExecutionPlan e PlannedLayer: value objects puros do plano de execução.

Representam o plano determinístico derivado do manifesto pelo Risk_Planner. São
código de domínio puro: sem qualquer import de framework de orquestração
(Agno), parser de YAML ou de infraestrutura (Requisitos 6.5, 12.1). Ambos são
value objects imutáveis com igualdade por valor, garantindo determinismo
byte-a-byte na comparação de planos (Requisito 3.6).
"""

from dataclasses import dataclass

from qa_platform.domain.value_objects.ids import LayerId

PRIORITY_MIN = 1
PRIORITY_MAX = 100


@dataclass(frozen=True)
class PlannedLayer:
    """Camada planejada para execução, com prioridade determinística.

    Value object imutável e comparável por valor.

    Campos:
        layer_id: identidade da camada a ser executada.
        priority: prioridade inteira no intervalo ``[1, 100]`` (Requisito 2.2);
            maior valor = maior prioridade.
        reduced_mode: marcado pela Cost_Condition quando a camada roda em modo
            reduzido para economizar custo (Requisito 5.2).
    """

    layer_id: LayerId
    priority: int
    reduced_mode: bool = False

    def __post_init__(self) -> None:
        if not PRIORITY_MIN <= self.priority <= PRIORITY_MAX:
            raise ValueError(
                f"priority deve estar em [{PRIORITY_MIN}, {PRIORITY_MAX}]: "
                f"{self.priority}"
            )


@dataclass(frozen=True)
class ExecutionPlan:
    """Plano de execução: sequência estável e imutável de camadas planejadas.

    Value object imutável e comparável por valor (Requisitos 6.5, 12.1). O uso
    de ``tuple`` torna o plano imutável e comparável byte-a-byte, garantindo o
    determinismo exigido pelo ADR-001 (Requisitos 1.2, 3.6).

    Campos:
        layers: camadas planejadas, ordenadas de forma estável.
    """

    layers: tuple[PlannedLayer, ...] = ()
