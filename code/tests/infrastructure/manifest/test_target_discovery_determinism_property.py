"""Teste de propriedade do determinismo/ordenação da Fase 1 (Property 1).

Property 1 — Determinismo da Fase 1 (idempotência de saída): para toda árvore de
repositório sintética resolvível, ``discover_target`` produz sempre o mesmo Draft
(igual byte-a-byte entre execuções repetidas), e as coleções do bloco
``discovery`` (``tools``/``prompts``/``rag``) saem ordenadas por
``(source, identifier)`` e ``frameworks_detected`` alfabeticamente — ordem total,
estável e independente da ordem em que o filesystem é lido/escrito.

Hypothesis gera uma árvore de arquivos-fonte sintéticos (com imports de
framework, tools ``@tool``, atribuições de prompt e tokens de RAG que as
heurísticas da Fase 1 reconhecem), escritos em ordens/nomes permutados a cada
exemplo, sob um subdiretório fresco de ``tmp_path``. Afirma:

1. **Idempotência byte-a-byte** — ``discover_target(x)`` repetido em execuções
   sucessivas produz Drafts idênticos, inclusive na serialização JSON canônica
   (``json.dumps(..., sort_keys=True)``).
2. **Ordenação independente da ordem de leitura** — permutando a ordem de escrita
   dos arquivos no filesystem, o bloco ``discovery`` serializado é idêntico e as
   listas ``tools``/``prompts``/``rag`` estão ordenadas por ``(source,
   identifier)``; ``frameworks_detected`` está em ordem alfabética.

A Fase 1 não toca rede nem LLM: apenas lê o filesystem local (``repo_reader`` →
``discovery_heuristics``). Nenhum mock de AWS é usado (não há AWS na Fase 1).

# Feature: hybrid-target-discovery, Property 1
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.manifest.target_discovery import (
    discover_target,
    has_pending_fields,
)

# --- Estratégias -------------------------------------------------------------
# Identificadores Python válidos (minúsculas), distinguíveis entre si.
_identifiers = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=10,
)

# Stem de nome de arquivo-fonte (.py será anexado).
_file_stems = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=10,
)

# Tokens de RAG reconhecidos pela heurística de ``discovery_heuristics``.
_rag_tokens = st.sampled_from(
    (
        "Knowledge",
        "VectorDb",
        "LanceDb",
        "PgVector",
        "retriever",
        "retrieval",
        "embeddings",
    )
)


def _tool_snippet(name: str) -> str:
    """Trecho que a heurística ``@tool`` reconhece (identifier = ``name``)."""
    return f"@tool\ndef {name}():\n    return None\n"


def _prompt_snippet(name: str) -> str:
    """Atribuição de prompt reconhecida (nome termina em ``_prompt``)."""
    return f"{name}_prompt = 'texto'\n"


def _rag_snippet(token: str) -> str:
    """Uso de um token de RAG reconhecido pela heurística."""
    return f"kb = {token}()\n"


@st.composite
def _synthetic_files(draw: st.DrawFn) -> list[tuple[str, str]]:
    """Gera pares ``(nome_arquivo, conteudo)`` com indícios detectáveis.

    Cada arquivo mistura, em quantidade variável (possivelmente zero), imports de
    framework, tools, prompts e tokens de RAG. Nomes de arquivo são únicos para
    que ``source`` (o caminho) seja determinístico por item.
    """
    stems = draw(st.lists(_file_stems, min_size=1, max_size=5, unique=True))
    files: list[tuple[str, str]] = []
    for stem in stems:
        parts: list[str] = []
        # Import de framework opcional (Agno e/ou LangGraph).
        if draw(st.booleans()):
            parts.append("from agno.agent import Agent\n")
        if draw(st.booleans()):
            parts.append("import langgraph\n")
        # Tools, prompts e RAG em quantidade variável (>= 0).
        for name in draw(st.lists(_identifiers, min_size=0, max_size=3, unique=True)):
            parts.append(_tool_snippet(name))
        for name in draw(st.lists(_identifiers, min_size=0, max_size=3, unique=True)):
            parts.append(_prompt_snippet(name))
        for token in draw(st.lists(_rag_tokens, min_size=0, max_size=3, unique=True)):
            parts.append(_rag_snippet(token))
        files.append((f"{stem}.py", "".join(parts)))
    return files


def _write_tree(base: Path, files: list[tuple[str, str]]) -> None:
    """Escreve os arquivos sintéticos sob ``base`` na ordem fornecida."""
    base.mkdir(parents=True, exist_ok=True)
    for name, content in files:
        (base / name).write_text(content, encoding="utf-8")


def _is_sorted_by_source_identifier(items: list[dict[str, str]]) -> bool:
    """Indica se ``items`` está ordenado por ``(source, identifier)`` (ASCII)."""
    keys = [(item["source"], item["identifier"]) for item in items]
    return keys == sorted(keys)


# Feature: hybrid-target-discovery, Property 1
# Property 1: Determinismo da Fase 1 (idempotência de saída).
# Validates: Requirements 2.1, 2.4
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(files=_synthetic_files(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_fase1_determinismo_e_ordenacao_independente_da_leitura(
    tmp_path: Path,
    files: list[tuple[str, str]],
    seed: int,
) -> None:
    """discover_target é idempotente e ordena por (source, identifier) (Req 2.1, 2.4)."""
    # Arrange — subdiretório fresco por exemplo evita vazamento entre iterações
    # do Hypothesis reusando o mesmo ``tmp_path`` function-scoped.
    repo_dir = tmp_path / f"repo_{seed}"
    _write_tree(repo_dir, files)
    target_ref = str(repo_dir)

    # Act — idempotência: mesma referência, execuções repetidas.
    first = discover_target(target_ref)
    second = discover_target(target_ref)

    # Assert — igualdade estrutural e byte-a-byte (JSON canônico).
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    # Draft continua distinguível de manifesto completo (campos PENDING).
    assert has_pending_fields(first)

    discovery: dict[str, Any] = first["discovery"]

    # Ordenação total e estável das coleções por (source, identifier) (Req 2.4).
    for collection in ("tools", "prompts", "rag"):
        assert _is_sorted_by_source_identifier(discovery[collection])

    # frameworks_detected em ordem alfabética (Req 2.4).
    assert discovery["frameworks_detected"] == sorted(discovery["frameworks_detected"])

    # Independência da ordem de leitura: reescrever a MESMA árvore numa ordem de
    # escrita permutada produz um Draft idêntico (a ordenação por caminho no
    # ``repo_reader`` + ordenação por (source, identifier) nas heurísticas tornam
    # a saída invariante à ordem de varredura do filesystem).
    permuted = list(files)
    random.Random(seed).shuffle(permuted)
    permuted_dir = tmp_path / f"repo_permuted_{seed}"
    _write_tree(permuted_dir, permuted)

    permuted_draft = discover_target(str(permuted_dir))

    # O bloco discovery independe da ordem de escrita: o único campo dependente do
    # caminho absoluto é ``target.ref``; comparamos o bloco documental discovery.
    assert permuted_draft["discovery"] == discovery
    assert json.dumps(permuted_draft["discovery"], sort_keys=True) == json.dumps(
        discovery, sort_keys=True
    )
