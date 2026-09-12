"""Target_Discovery mínimo e determinístico (Requisitos 9.1–9.5).

Produz um **rascunho** de ``QA_Target_Manifest`` (como ``dict`` conforme o schema)
a partir de uma referência de alvo. Os campos obrigatórios que **não** podem ser
derivados da referência são marcados como **pendentes** (sentinela ``PENDING``),
de modo que um rascunho seja sempre distinguível de um manifesto completo
(Requisito 9.2).

É mínimo e determinístico: a mesma referência produz sempre o mesmo rascunho
(Requisito 9.4), sem invocar modelo de linguagem e sem chamadas de rede
(Requisito 9.3). As QA_Layers aplicáveis são representadas por identificadores de
camada que correspondem às identidades do ``QA_Layer_Contract`` (Requisito 9.1).
Se a referência de alvo for ausente ou irresolvível, encerra sem rascunho e
levanta ``TargetResolutionError`` nomeando a referência afetada (Requisito 9.5).

Código de infraestrutura puro: sem LLM, sem rede, sem parser de framework.
"""

from __future__ import annotations

from typing import Any

from qa_platform.domain.exceptions import TargetResolutionError

# Sentinela que marca um campo obrigatório do schema ainda não derivado da
# referência de alvo; torna o rascunho distinguível de um manifesto completo
# (Requisito 9.2). O desenvolvedor substitui cada PENDING antes da execução.
PENDING = "PENDING"

# Identidades de QA_Layer aplicáveis representadas por identificadores de camada
# que correspondem às identidades do QA_Layer_Contract (Requisito 9.1). Conjunto
# fixo e ordenado: garante determinismo do rascunho (Requisito 9.4).
_DEFAULT_APPLICABLE_LAYERS: tuple[str, ...] = ("ai",)


def discover_target(target_ref: str | None) -> dict[str, Any]:
    """Produz um rascunho determinístico de ``QA_Target_Manifest``.

    Deriva da ``target_ref`` os campos possíveis e marca como ``PENDING`` cada
    campo obrigatório não derivável, mantendo o rascunho conforme o schema
    (Requisitos 9.1, 9.2). Determinístico e sem LLM/rede (Requisitos 9.3, 9.4).

    Args:
        target_ref: referência do alvo a inspecionar (ex.: identificador do
            artefato). Ausente/vazia/só-espaços é considerada irresolvível.

    Returns:
        Um ``dict`` de rascunho conforme o schema do manifesto, com campos não
        derivados marcados como ``PENDING``.

    Raises:
        TargetResolutionError: se ``target_ref`` for ausente ou irresolvível,
            nomeando a referência afetada (Requisito 9.5).
    """
    resolved_ref = _resolve_ref(target_ref)

    draft: dict[str, Any] = {
        "target": {
            # ref é derivada diretamente da referência resolvida.
            "ref": resolved_ref,
            # version não é derivável de uma referência de alvo nua: pendente.
            "version": PENDING,
        },
        # Camadas aplicáveis com identidades do QA_Layer_Contract (Req 9.1).
        "applicable_layers": list(_DEFAULT_APPLICABLE_LAYERS),
        # Parâmetros de risco não são derivados nesta fase: pendentes por camada
        # (Req 9.2). Preservam a forma do schema (mapping por layer_id).
        "risk_parameters": {
            layer_id: {"weight": PENDING} for layer_id in _DEFAULT_APPLICABLE_LAYERS
        },
    }
    return draft


def is_pending(value: Any) -> bool:
    """Indica se ``value`` é o marcador de campo pendente (``PENDING``)."""
    return value == PENDING


def has_pending_fields(draft: dict[str, Any]) -> bool:
    """Indica se ``draft`` ainda contém qualquer campo pendente.

    Percorre recursivamente o rascunho procurando o marcador ``PENDING``. Um
    manifesto completo não contém nenhum campo pendente (Requisito 9.2).
    """
    return _contains_pending(draft)


def _resolve_ref(target_ref: str | None) -> str:
    """Resolve e normaliza a referência de alvo ou levanta erro.

    Referência ausente, vazia ou só com espaços é irresolvível nesta fase
    determinística (Requisito 9.5).
    """
    if target_ref is None or not target_ref.strip():
        raise TargetResolutionError(
            f"Referência de alvo ausente ou irresolvível: {target_ref!r}"
        )
    return target_ref.strip()


def _contains_pending(value: Any) -> bool:
    """Verifica recursivamente a presença do marcador ``PENDING``."""
    if is_pending(value):
        return True
    if isinstance(value, dict):
        return any(_contains_pending(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_pending(item) for item in value)
    return False


# Nota sobre conformidade com o schema: o rascunho preserva a *forma* do schema
# (chaves target/applicable_layers/risk_parameters e sua estrutura de mapping),
# derivando os campos possíveis e marcando os demais como ``PENDING``. O marcador
# é intencionalmente distinto de um valor válido (ex.: um ``weight`` numérico),
# tornando o rascunho não confundível com um manifesto completo (Requisito 9.2):
# enquanto houver ``PENDING``, ``validate_manifest`` (schema.py) rejeita o
# manifesto, forçando o desenvolvedor a substituir cada pendência antes da
# execução.
__all__ = [
    "PENDING",
    "discover_target",
    "has_pending_fields",
    "is_pending",
]
