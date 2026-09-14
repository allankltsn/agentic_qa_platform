"""Heurísticas de detecção da Fase 1 (Requisitos 3 e 4).

A partir de uma ``RepoView`` imutável (produzida por ``repo_reader``), detecta —
por heurísticas **sintáticas** de import/arquivo, sem LLM e sem rede — o framework
de agente (Agno/LangGraph) e extrai ferramentas, prompts e indícios de RAG
declarados, devolvendo um ``DiscoveryInfo`` puro do domínio.

Determinismo por design (Requisito 2.4): este módulo **não importa** ``agno``,
``boto3`` nem clientes HTTP; toda a detecção é análise de texto local. Os
``DetectedItem`` são ordenados por ``(source, identifier)`` (ASCII, case-sensitive)
e ``frameworks_detected`` alfabeticamente — ordem total, estável e independente da
ordem de leitura do filesystem.

Limites documentados (Requisito 3.5): a detecção é sintática, não semântica —
pode gerar falso positivo (ex.: arquivo de exemplo que importa Agno) ou falso
negativo (ex.: import via alias exótico, construção dinâmica). Por isso
``DiscoveryInfo`` é documental/derivado e carrega uma ``fragility_note`` fixa
marcando que o resultado exige revisão do Developer.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from qa_platform.domain.value_objects.discovery import (
    DetectedItem,
    DiscoveryInfo,
    Framework,
)
from qa_platform.infrastructure.manifest.repo_reader import RepoView

# Nota fixa de fragilidade das heurísticas (Requisito 3.5). Texto estável para
# não quebrar o determinismo byte-a-byte do Draft (Requisito 2.1).
FRAGILITY_NOTE = (
    "Heurísticas de detecção são frágeis e sintáticas: podem gerar falso "
    "positivo ou falso negativo. O resultado é documental/derivado e exige "
    "revisão do Developer."
)

# --- Heurísticas de framework (Requisitos 3.1, 3.2) -------------------------
# Import de topo (``import agno`` / ``from agno...``) ou submódulo. A âncora em
# início de linha (com ``re.MULTILINE``) reduz falso positivo de substring.
_AGNO_IMPORT = re.compile(r"^\s*(?:from|import)\s+agno(?:\.|\s|$)", re.MULTILINE)
_LANGGRAPH_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+langgraph(?:\.|\s|$)", re.MULTILINE
)

# --- Heurísticas de tools (Requisito 4.1) -----------------------------------
# Decorador ``@tool`` (Agno/LangGraph) sobre uma função: o identificador é o nome
# da função decorada na linha seguinte.
_TOOL_DECORATOR = re.compile(
    r"^\s*@tool\b[^\n]*\n\s*(?:async\s+)?def\s+(?P<name>[A-Za-z_]\w*)",
    re.MULTILINE,
)

# --- Heurísticas de prompts (Requisito 4.2) ---------------------------------
# Atribuições a nomes que terminam em ``PROMPT``/``_prompt`` (convenção comum).
_PROMPT_ASSIGN = re.compile(
    r"^\s*(?P<name>[A-Za-z_]\w*(?:PROMPT|_prompt))\s*[:=]",
    re.MULTILINE,
)

# --- Heurísticas de RAG (Requisito 4.3) -------------------------------------
# Indícios sintáticos de RAG: nomes de símbolos de conhecimento/vetor comuns nos
# frameworks suportados. Cada acerto vira um indício com o token como identifier.
_RAG_TOKENS: tuple[str, ...] = (
    "Knowledge",
    "VectorDb",
    "LanceDb",
    "PgVector",
    "retriever",
    "retrieval",
    "embeddings",
)
_RAG_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(token) for token in _RAG_TOKENS) + r")\b"
)


def detect(repo_view: RepoView) -> DiscoveryInfo:
    """Produz o ``DiscoveryInfo`` a partir de uma ``RepoView`` imutável.

    Detecta o framework (Requisito 3) e extrai tools/prompts/RAG (Requisito 4).
    Nenhum framework → ``Framework.NOT_DETECTED`` concluindo sem erro (Requisito
    3.4); ambos → ``ambiguous=True`` com os dois em ``frameworks_detected``
    (Requisito 3.3). Nenhum item → coleções vazias, sem erro (Requisito 4.4).

    Args:
        repo_view: visão imutável e ordenada do repositório-alvo.

    Returns:
        ``DiscoveryInfo`` puro, com coleções ordenadas de forma total e estável.
    """
    frameworks = _detect_frameworks(repo_view)
    framework, frameworks_detected, ambiguous = _classify_frameworks(frameworks)

    return DiscoveryInfo(
        framework=framework,
        frameworks_detected=frameworks_detected,
        ambiguous=ambiguous,
        tools=_extract(repo_view, _find_tools),
        prompts=_extract(repo_view, _find_prompts),
        rag=_extract(repo_view, _find_rag),
        fragility_note=FRAGILITY_NOTE,
    )


def _detect_frameworks(repo_view: RepoView) -> set[Framework]:
    """Varre os arquivos e retorna o conjunto de frameworks detectados."""
    found: set[Framework] = set()
    for _path, content in repo_view.files:
        if _AGNO_IMPORT.search(content):
            found.add(Framework.AGNO)
        if _LANGGRAPH_IMPORT.search(content):
            found.add(Framework.LANGGRAPH)
    return found


def _classify_frameworks(
    found: set[Framework],
) -> tuple[Framework, tuple[Framework, ...], bool]:
    """Classifica o conjunto detectado em (framework, detectados, ambíguo).

    - vazio → ``NOT_DETECTED``, sem detectados, não ambíguo (Requisito 3.4);
    - único → esse framework, um detectado, não ambíguo (Requisitos 3.1, 3.2);
    - múltiplo → ``framework`` é o primeiro alfabético (determinístico),
      ``frameworks_detected`` traz todos ordenados, ``ambiguous=True`` (Req 3.3).
    """
    if not found:
        return Framework.NOT_DETECTED, (), False

    # Ordenação alfabética estável por valor do enum (``agno`` < ``langgraph``).
    detected = tuple(sorted(found, key=lambda fw: fw.value))
    ambiguous = len(detected) > 1
    return detected[0], detected, ambiguous


def _extract(
    repo_view: RepoView,
    finder: Callable[[str], list[str]],
) -> tuple[DetectedItem, ...]:
    """Aplica ``finder`` a cada arquivo e devolve os itens ordenados/únicos.

    Ordena por ``(source, identifier)`` (ASCII, case-sensitive) e remove
    duplicatas exatas, garantindo ordem total, estável e determinística
    (Requisito 2.4). Nenhum acerto → tupla vazia, sem erro (Requisito 4.4).
    """
    collected: set[DetectedItem] = set()
    for path, content in repo_view.files:
        for identifier in finder(content):
            collected.add(DetectedItem(identifier=identifier, source=path))
    return tuple(sorted(collected, key=lambda item: (item.source, item.identifier)))


def _find_tools(content: str) -> list[str]:
    """Extrai identificadores de tools declaradas via ``@tool`` (Requisito 4.1)."""
    return [match.group("name") for match in _TOOL_DECORATOR.finditer(content)]


def _find_prompts(content: str) -> list[str]:
    """Extrai identificadores de prompts declarados (Requisito 4.2)."""
    return [match.group("name") for match in _PROMPT_ASSIGN.finditer(content)]


def _find_rag(content: str) -> list[str]:
    """Extrai indícios de RAG por tokens de conhecimento/vetor (Requisito 4.3)."""
    return [match.group(1) for match in _RAG_PATTERN.finditer(content)]


__all__ = ["FRAGILITY_NOTE", "detect"]
