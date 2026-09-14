"""Teste de propriedade da preservação da sentinela PENDING (Property 5).

Property 5 — Preservação da sentinela PENDING: um rascunho de manifesto com
subconjuntos de campos marcados como ``PENDING`` permanece distinguível de um
manifesto completo. Verificamos duas facetas coerentes entre si:

1. **Detecção estrutural (``has_pending_fields``/``is_pending``):** para qualquer
   subconjunto de campos marcados como ``PENDING``, ``has_pending_fields`` é
   verdadeiro sse e somente se existe ao menos um ``PENDING``, e ``is_pending``
   é verdadeiro exatamente nos valores marcados (Requisitos 1.2, 1.3, 8.1).

2. **Rejeição pelo parser nomeando o campo:** quando um campo numérico do schema
   (``risk_parameters.<layer>.weight``) recebe a sentinela — que é uma string,
   não um número —, ``parse_manifest_text`` levanta ``InvalidManifestError``
   nomeando **cada** ``weight`` pendente em ``invalid_fields``, sem produzir um
   VO parcial (Requisito 8.1). Assim o rascunho nunca é confundido com um
   manifesto executável enquanto houver pendências onde o schema as detecta.

# Feature: hybrid-target-discovery, Property 5
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.exceptions import InvalidManifestError
from qa_platform.infrastructure.manifest.parser import parse_manifest_text
from qa_platform.infrastructure.manifest.target_discovery import (
    PENDING,
    has_pending_fields,
    is_pending,
)

# Identificadores de camada não-vazios (schema exige ``minLength: 1``).
_layer_ids = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=10,
)


def _complete_draft(layers: list[str]) -> dict[str, Any]:
    """Constrói um rascunho válido (sem pendências) para as camadas dadas."""
    return {
        "target": {"ref": "artifact://x", "version": "1.0.0"},
        "applicable_layers": list(layers),
        "risk_parameters": {layer: {"weight": 1.0} for layer in layers},
    }


@st.composite
def _drafts_with_pending(draw: st.DrawFn) -> tuple[dict[str, Any], list[str], bool]:
    """Gera um rascunho e injeta ``PENDING`` num subconjunto arbitrário de campos.

    Retorna o rascunho, os caminhos pontuados dos ``weight`` marcados como
    pendentes (subconjunto possivelmente vazio) e se ``target.version`` também
    recebeu a sentinela.
    """
    layers = draw(st.lists(_layer_ids, min_size=1, max_size=4, unique=True))
    draft = _complete_draft(layers)

    # Subconjunto arbitrário de camadas cujo ``weight`` fica PENDING.
    pending_layers = draw(
        st.lists(st.sampled_from(layers), max_size=len(layers), unique=True)
    )
    pending_weight_paths: list[str] = []
    for layer in pending_layers:
        draft["risk_parameters"][layer]["weight"] = PENDING
        pending_weight_paths.append(f"risk_parameters.{layer}.weight")

    # ``target.version`` opcionalmente pendente: a sentinela é uma string válida
    # pelo schema, logo não é rejeitada pelo parser — mas É detectada por
    # ``has_pending_fields``. Isso exercita a distinção estrutural.
    version_pending = draw(st.booleans())
    if version_pending:
        draft["target"]["version"] = PENDING

    return draft, pending_weight_paths, version_pending


# Feature: hybrid-target-discovery, Property 5
# Property 5: Preservação da sentinela PENDING — detecção estrutural coerente.
# Validates: Requirements 1.2, 1.3, 8.1
@settings(max_examples=100)
@given(case=_drafts_with_pending())
def test_deteccao_estrutural_de_pending_e_coerente(
    case: tuple[dict[str, Any], list[str], bool],
) -> None:
    """``has_pending_fields``/``is_pending`` refletem exatamente as pendências."""
    draft, pending_weight_paths, version_pending = case
    any_pending = bool(pending_weight_paths) or version_pending

    assert has_pending_fields(draft) is any_pending

    # ``is_pending`` verdadeiro exatamente nos ``weight`` marcados.
    for layer, params in draft["risk_parameters"].items():
        path = f"risk_parameters.{layer}.weight"
        assert is_pending(params["weight"]) is (path in pending_weight_paths)

    # E coerente para ``target.version``.
    assert is_pending(draft["target"]["version"]) is version_pending


# Feature: hybrid-target-discovery, Property 5
# Property 5: Preservação da sentinela PENDING — parser rejeita nomeando cada
# ``weight`` pendente, sem VO parcial.
# Validates: Requirements 8.1
@settings(max_examples=100)
@given(case=_drafts_with_pending())
def test_parser_rejeita_pending_nomeando_cada_weight(
    case: tuple[dict[str, Any], list[str], bool],
) -> None:
    """``PENDING`` num ``weight`` → ``InvalidManifestError`` nomeando o campo."""
    draft, pending_weight_paths, _version_pending = case

    # O parser não deve mutar sua entrada (sem VO/estado parcial).
    text = yaml.safe_dump(copy.deepcopy(draft), allow_unicode=True)

    if not pending_weight_paths:
        # Sem ``weight`` pendente, o rascunho é aceito pelo schema (mesmo que
        # ``target.version`` seja a string "PENDING", válida pelo schema).
        parse_manifest_text(text)
        return

    with pytest.raises(InvalidManifestError) as exc_info:
        parse_manifest_text(text)

    invalid_fields = exc_info.value.invalid_fields
    # Cada ``weight`` pendente é nomeado no erro agregado (nenhum silenciado).
    for path in pending_weight_paths:
        assert path in invalid_fields
