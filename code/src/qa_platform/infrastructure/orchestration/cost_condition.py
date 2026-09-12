"""Cost_Condition: decisão determinística de pular trabalho caro + Agno ``Condition``.

O ``should_skip_expensive`` decide, com base **exclusivamente** no
``QATargetManifest``, se o trabalho caro de uma camada deve ser pulado
(Requisitos 5.1, 5.3). A decisão é determinística: parâmetros idênticos produzem
sempre a mesma resposta ``(skip, motivo)`` (Requisito 5.4) e nunca consulta modelo
de linguagem ou qualquer fonte externa ao manifesto (Requisito 5.3). Quando o
manifesto não contém parâmetros de custo para a camada, o trabalho caro é pulado
com um motivo não-vazio indicando parâmetros ausentes (Requisito 5.5).

O ``build_cost_condition`` mapeia essa decisão para a ``Condition`` da Agno, cujos
tipos ficam **confinados a este módulo de infraestrutura** — não vazam para o
domínio (Requisito 12.2).
"""

from __future__ import annotations

from collections.abc import Sequence

from agno.workflow import Condition, Step  # tipo da Agno CONFINADO à infraestrutura
from agno.workflow.types import StepInput

from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.domain.entities.manifest import QATargetManifest

#: Motivos padrão do salto de trabalho caro (não-vazios por contrato, Req 5.2/5.5).
REASON_MISSING_PARAMETERS = "parâmetros de custo ausentes"
REASON_NOT_JUSTIFIED = "trabalho caro não justificado pelos parâmetros de risco"


def should_skip_expensive(
    manifest: QATargetManifest, layer_id: LayerId
) -> tuple[bool, str]:
    """Decide se o trabalho caro de ``layer_id`` deve ser pulado.

    Decisão determinística baseada **apenas** no ``manifest`` (Requisitos 5.3,
    5.4): consulta os parâmetros de custo da camada e decide sem qualquer fonte
    externa nem modelo de linguagem. Retorna ``(True, motivo)`` para pular ou
    ``(False, "")`` para executar; o motivo do salto é sempre não-vazio.

    - Sem parâmetros de custo para a camada -> pular com motivo de ausência
      (Requisito 5.5).
    - Parâmetros presentes mas que não justificam o trabalho caro -> pular com
      motivo de não justificado (Requisito 5.1).
    - Parâmetros que justificam o trabalho caro -> executar (``(False, "")``).

    Args:
        manifest: manifesto de alvo (única fonte da decisão).
        layer_id: identidade da camada avaliada.

    Returns:
        Uma tupla ``(skip, motivo)``: ``skip`` indica se pular o trabalho caro;
        ``motivo`` é não-vazio quando ``skip`` é ``True`` e vazio caso contrário.
    """
    params = manifest.cost_parameters_for(layer_id)
    if params is None:
        return True, REASON_MISSING_PARAMETERS  # Req 5.5
    if not params.justifies_expensive_work():
        return True, REASON_NOT_JUSTIFIED  # Req 5.1
    return False, ""


def build_cost_condition(
    manifest: QATargetManifest,
    layer_id: LayerId,
    expensive_steps: Sequence[Step],
    reduced_steps: Sequence[Step] | None = None,
) -> Condition:
    """Monta a ``Condition`` da Agno a partir da decisão determinística.

    O ``evaluator`` da ``Condition`` inverte ``should_skip_expensive``: executa
    os ``expensive_steps`` **quando não** se deve pular; caso contrário segue
    pelos ``reduced_steps`` (modo reduzido), se fornecidos. A decisão usa apenas
    o manifesto e é determinística (Requisitos 5.3, 5.4). Os tipos da Agno
    (``Condition``/``Step``/``StepInput``) ficam confinados a este módulo
    (Requisito 12.2).

    Args:
        manifest: manifesto de alvo (fonte da decisão).
        layer_id: identidade da camada avaliada.
        expensive_steps: steps do trabalho caro (executados quando justificado).
        reduced_steps: steps do modo reduzido (executados quando pulado).

    Returns:
        Uma ``Condition`` da Agno com um ``evaluator`` determinístico.
    """

    def evaluator(_step_input: StepInput) -> bool:
        """Executa o trabalho caro apenas quando não se deve pular (determinístico)."""
        skip, _reason = should_skip_expensive(manifest, layer_id)
        return not skip

    return Condition(
        steps=list(expensive_steps),
        evaluator=evaluator,
        else_steps=list(reduced_steps) if reduced_steps is not None else None,
        name=f"cost_condition:{layer_id.value}",
    )
