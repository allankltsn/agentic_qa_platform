"""Static_Inspector: descoberta determinística de alvo (Fase 1, Requisito 1).

Produz um **rascunho** (``Draft``) de ``QA_Target_Manifest`` (como ``dict``
conforme o schema) a partir de uma referência de alvo, agora enriquecido com um
bloco ``discovery`` documental/derivado (ADR-004, Fase 1). O corpo evoluiu da
Sprint 1 compondo dois colaboradores da mesma fase/adapter:

1. ``repo_reader.read_target`` — leitura estática total do repositório-alvo no
   filesystem local, sem rede e sem LLM (Requisitos 2.3, 2.6);
2. ``discovery_heuristics.detect`` — heurísticas sintáticas de framework, tools,
   prompts e RAG, devolvendo um ``DiscoveryInfo`` puro do domínio (Requisito 4).

**Interface preservada** (Requisito 1.1): o ``__all__`` (``PENDING``,
``discover_target``, ``has_pending_fields``, ``is_pending``), a assinatura
``(target_ref: str | None) -> dict[str, Any]`` (Requisitos 1.1, 1.5), a sentinela
``PENDING`` e a semântica de ``TargetResolutionError`` continuam idênticas à
Sprint 1. Os campos obrigatórios não deriváveis da referência permanecem
``PENDING`` (Requisito 1.2), mantendo o rascunho distinguível de um manifesto
completo.

**Determinismo por design** (Requisitos 2.2, 2.3): este módulo **não importa**
``agno``, ``boto3`` nem clientes HTTP — a fronteira é reforçada pelo contrato
``fase1-sem-llm`` do import-linter. A mesma referência produz sempre o mesmo
rascunho, com coleções totalmente ordenadas.

**Aborta sem Draft parcial** (Requisitos 2.5, 2.6): se a leitura íntegra do
repositório falhar (``RepoReadError`` do ``repo_reader``), o erro se propaga sem
que nenhum Draft parcial seja construído.

O bloco ``discovery`` é **documental/derivado** e **não** altera o roteamento do
``Layer_Router`` (Requisito 4.6) — serve para revisão do Developer.
"""

from __future__ import annotations

from typing import Any

from qa_platform.domain.exceptions import TargetResolutionError
from qa_platform.domain.value_objects.discovery import (
    DetectedItem,
    DiscoveryInfo,
    Framework,
)
from qa_platform.infrastructure.manifest import discovery_heuristics, repo_reader

# Sentinela que marca um campo obrigatório do schema ainda não derivado da
# referência de alvo; torna o rascunho distinguível de um manifesto completo
# (Requisito 1.2). O desenvolvedor substitui cada PENDING antes da execução.
PENDING = "PENDING"

# Identidades de QA_Layer aplicáveis representadas por identificadores de camada
# que correspondem às identidades do QA_Layer_Contract. Conjunto fixo e ordenado:
# garante determinismo do rascunho (Requisito 2.1).
_DEFAULT_APPLICABLE_LAYERS: tuple[str, ...] = ("ai",)


def discover_target(target_ref: str | None) -> dict[str, Any]:
    """Produz um rascunho determinístico de ``QA_Target_Manifest``.

    Resolve a referência, lê o repositório-alvo por completo (filesystem local,
    sem rede/LLM), aplica as heurísticas de detecção e monta o Draft preservando
    a forma da Sprint 1 mais o bloco ``discovery`` (serialização determinística
    do ``DiscoveryInfo``). Os campos obrigatórios não deriváveis permanecem
    ``PENDING`` (Requisitos 1.1, 1.2, 1.5).

    Args:
        target_ref: referência do alvo a inspecionar (ex.: caminho do artefato).
            Ausente/vazia/só-espaços é considerada irresolvível.

    Returns:
        Um ``dict`` de rascunho conforme o schema do manifesto, com campos não
        derivados marcados como ``PENDING`` e um bloco ``discovery`` documental.

    Raises:
        TargetResolutionError: se ``target_ref`` for ausente ou irresolvível,
            nomeando a referência afetada (Requisito 1.4). Nenhum Draft é
            produzido.
        repo_reader.RepoReadError: se a leitura íntegra do repositório-alvo
            falhar (arquivo/conteúdo inacessível). Aborta **sem Draft parcial**
            (Requisitos 2.5, 2.6).
    """
    resolved_ref = _resolve_ref(target_ref)

    # Fase 1 — leitura estática total e heurísticas determinísticas. Uma falha de
    # leitura íntegra (RepoReadError) propaga sem construir Draft parcial (Req 2.6).
    repo_view = repo_reader.read_target(resolved_ref)
    discovery = discovery_heuristics.detect(repo_view)

    draft: dict[str, Any] = {
        "target": {
            # ref é derivada diretamente da referência resolvida.
            "ref": resolved_ref,
            # version não é derivável de uma referência de alvo nua: pendente.
            "version": PENDING,
        },
        # Camadas aplicáveis com identidades do QA_Layer_Contract (Req 1.5).
        "applicable_layers": list(_DEFAULT_APPLICABLE_LAYERS),
        # Parâmetros de risco não são derivados nesta fase: pendentes por camada
        # (Req 1.2). Preservam a forma do schema (mapping por layer_id).
        "risk_parameters": {
            layer_id: {"weight": PENDING} for layer_id in _DEFAULT_APPLICABLE_LAYERS
        },
        # Bloco documental/derivado (Req 4.6): não altera o roteamento do
        # Layer_Router; serialização determinística e totalmente ordenada.
        "discovery": _serialize_discovery(discovery),
    }
    return draft


def is_pending(value: Any) -> bool:
    """Indica se ``value`` é o marcador de campo pendente (``PENDING``)."""
    return value == PENDING


def has_pending_fields(draft: dict[str, Any]) -> bool:
    """Indica se ``draft`` ainda contém qualquer campo pendente.

    Percorre recursivamente o rascunho procurando o marcador ``PENDING``. Um
    manifesto completo não contém nenhum campo pendente (Requisito 1.2).
    """
    return _contains_pending(draft)


def _resolve_ref(target_ref: str | None) -> str:
    """Resolve e normaliza a referência de alvo ou levanta erro.

    Referência ausente, vazia ou só com espaços é irresolvível nesta fase
    determinística (Requisito 1.4).
    """
    if target_ref is None or not target_ref.strip():
        raise TargetResolutionError(
            f"Referência de alvo ausente ou irresolvível: {target_ref!r}"
        )
    return target_ref.strip()


def _serialize_discovery(discovery: DiscoveryInfo) -> dict[str, Any]:
    """Serializa o ``DiscoveryInfo`` no bloco ``discovery`` do Draft.

    Serialização **determinística e totalmente ordenada** (Requisito 2.4):

    - ``framework`` vira o valor string do enum; ``Framework.NOT_DETECTED`` é
      mapeado para ``None`` no bloco (Requisito 3.4);
    - ``frameworks_detected`` é a lista dos valores string, em ordem alfabética;
    - ``tools``/``prompts``/``rag`` são listas de ``{"identifier", "source"}``
      ordenadas por ``(source, identifier)`` (ASCII, case-sensitive).

    O ``DiscoveryInfo`` já chega ordenado das heurísticas; a ordenação é
    reafirmada aqui para tornar o determinismo do Draft explícito e independente
    da origem dos dados.
    """
    return {
        "framework": _serialize_framework(discovery.framework),
        "frameworks_detected": sorted(fw.value for fw in discovery.frameworks_detected),
        "ambiguous": discovery.ambiguous,
        "tools": _serialize_items(discovery.tools),
        "prompts": _serialize_items(discovery.prompts),
        "rag": _serialize_items(discovery.rag),
        "fragility_note": discovery.fragility_note,
    }


def _serialize_framework(framework: Framework) -> str | None:
    """Mapeia o framework para string, ou ``None`` quando não detectado.

    ``Framework.NOT_DETECTED`` → ``None`` no bloco ``discovery`` (Requisito 3.4);
    os demais frameworks são serializados pelo seu valor string.
    """
    if framework is Framework.NOT_DETECTED:
        return None
    return framework.value


def _serialize_items(items: tuple[DetectedItem, ...]) -> list[dict[str, str]]:
    """Serializa ``DetectedItem`` ordenados por ``(source, identifier)``.

    Ordem total, estável e determinística (ASCII, case-sensitive), garantindo o
    determinismo byte-a-byte do Draft (Requisito 2.4).
    """
    ordered = sorted(items, key=lambda item: (item.source, item.identifier))
    return [{"identifier": item.identifier, "source": item.source} for item in ordered]


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
# tornando o rascunho não confundível com um manifesto completo (Requisito 1.2):
# enquanto houver ``PENDING``, ``validate_manifest`` (schema.py) rejeita o
# manifesto, forçando o desenvolvedor a substituir cada pendência antes da
# execução. O bloco ``discovery`` é documental/derivado e não afeta essa lógica
# nem o roteamento do Layer_Router (Requisito 4.6).
__all__ = [
    "PENDING",
    "discover_target",
    "has_pending_fields",
    "is_pending",
]
