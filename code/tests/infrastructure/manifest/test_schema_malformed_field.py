"""Teste de propriedade — campo malformado é rejeitado nomeando o campo (Property 9).

Property 9 — Campo opcional malformado é rejeitado nomeando o campo: para todo
manifesto SEM a sentinela ``PENDING``, porém com **um** campo opcional
(``discovery``, ``expected_domain``, ``golden_set``) presente e malformado segundo
o schema — OU com **um** campo obrigatório inválido —, ``validate_manifest`` levanta
``InvalidManifestError`` cujo conjunto de campos (``invalid_fields``) inclui o campo
ofensor. Não há produção de VO parcial (o validador apenas valida um ``dict`` e nada
retorna) e o manifesto de entrada não é mutado pela validação.

A propriedade cobre dois requisitos:
  - Req 5.7: campo **opcional** malformado é rejeitado nomeando o campo;
  - Req 8.2: campo **obrigatório** inválido é nomeado.

A quantificação é universal sobre (manifesto base válido, ponto de malformação):
Hypothesis gera o manifesto base e escolhe uma "receita" de malformação rotulada
com o caminho pontuado do campo ofensor esperado; afirmamos que esse caminho aparece
como chave (ou prefixo de chave, dado que arrays/objetos usam sufixos ``[i]``/``.sub``)
em ``exc.invalid_fields``, e que o ``dict`` de entrada permanece intacto.

# Feature: hybrid-target-discovery, Property 9
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.exceptions import InvalidManifestError
from qa_platform.infrastructure.manifest.schema import validate_manifest

# Uma "receita" de malformação: recebe o manifesto base VÁLIDO (dict), aplica UMA
# malformação in-place e retorna o caminho pontuado do campo ofensor esperado.
Malformation = Callable[[dict[str, Any]], str]

# Identificadores de camada não-vazios (schema exige ``minLength: 1``, sem duplicatas).
_layer_ids = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=12,
)

# Strings não-vazias para ``target.ref``/``target.version`` (schema exige ``minLength: 1``).
_non_empty_text = st.text(min_size=1, max_size=24).filter(lambda s: s.strip() != "")

# Pesos não-negativos (schema exige ``minimum: 0``).
_non_negative_number = st.floats(
    min_value=0, max_value=1_000, allow_nan=False, allow_infinity=False
) | st.integers(min_value=0, max_value=1_000)


@st.composite
def _valid_manifests(draw: st.DrawFn) -> dict[str, Any]:
    """Gera um manifesto base VÁLIDO (mesma forma do gerador da Property 2).

    Produz ``target`` (``ref``/``version`` não-vazios), ``applicable_layers``
    (1..N ids únicos e não-vazios) e ``risk_parameters`` (uma entrada por camada
    com ``weight`` >= 0). Nunca injeta a sentinela ``PENDING`` (domínio da
    Property 5) nem os campos opcionais — estes, quando presentes, são inseridos
    já malformados pela receita escolhida.
    """
    layers = draw(st.lists(_layer_ids, min_size=1, max_size=4, unique=True))
    risk_parameters = {
        layer: {"weight": draw(_non_negative_number)} for layer in layers
    }
    return {
        "target": {
            "ref": draw(_non_empty_text),
            "version": draw(_non_empty_text),
        },
        "applicable_layers": layers,
        "risk_parameters": risk_parameters,
    }


# --- Receitas de malformação -------------------------------------------------
#
# Cada receita muta o manifesto base VÁLIDO introduzindo exatamente UM defeito e
# devolve o caminho pontuado do campo ofensor esperado em ``invalid_fields``.
# Metade cobre campos OPCIONAIS (Req 5.7); a outra, campos OBRIGATÓRIOS (Req 8.2).


# expected_domain (opcional) — tipo errado e string vazia.
def _bad_expected_domain_type(m: dict[str, Any]) -> str:
    m["expected_domain"] = 123  # deveria ser string
    return "expected_domain"


def _bad_expected_domain_empty(m: dict[str, Any]) -> str:
    m["expected_domain"] = ""  # viola minLength: 1
    return "expected_domain"


# golden_set (opcional) — item sem ``input``, item com tipo errado e propriedade extra.
def _bad_golden_set_missing_input(m: dict[str, Any]) -> str:
    m["golden_set"] = [{"expected": "saida"}]  # falta ``input`` (obrigatório)
    return "golden_set[0].input"


def _bad_golden_set_wrong_input_type(m: dict[str, Any]) -> str:
    m["golden_set"] = [{"input": 42, "expected": "saida"}]  # ``input`` não-string
    return "golden_set[0].input"


def _bad_golden_set_extra_prop(m: dict[str, Any]) -> str:
    m["golden_set"] = [
        {"input": "entrada", "expected": "saida", "surpresa": "x"}
    ]  # additionalProperties: false
    return "golden_set[0].surpresa"


# discovery (opcional) — framework fora do enum e propriedade extra.
#
# Nota: os campos ``tools``/``prompts``/``rag`` de ``discovery`` referenciam o schema
# via ``$ref: #/$defs/detectedItemList``. O validador atual (``schema.py``) NÃO resolve
# ``$ref``, portanto não desce na validação dos itens desses arrays. Por isso NÃO
# usamos malformações em itens de ``tools``/``prompts``/``rag`` aqui — validamos apenas
# o que o validador de fato cobre. As malformações de ``discovery`` abaixo (enum de
# ``framework`` e propriedade extra) são declaradas inline no schema e são detectadas.
def _bad_discovery_framework_enum(m: dict[str, Any]) -> str:
    m["discovery"] = {"framework": "crewai"}  # fora do enum agno/langgraph/null
    return "discovery.framework"


def _bad_discovery_extra_prop(m: dict[str, Any]) -> str:
    m["discovery"] = {"desconhecido": True}  # additionalProperties: false
    return "discovery.desconhecido"


# Campos OBRIGATÓRIOS (Req 8.2).
def _bad_required_target_ref_empty(m: dict[str, Any]) -> str:
    m["target"]["ref"] = ""  # viola minLength: 1
    return "target.ref"


def _bad_required_applicable_layers_empty(m: dict[str, Any]) -> str:
    m["applicable_layers"] = []  # viola minItems: 1
    return "applicable_layers"


def _bad_required_risk_weight_negative(m: dict[str, Any]) -> str:
    layer = next(iter(m["risk_parameters"]))
    m["risk_parameters"][layer]["weight"] = -1  # viola minimum: 0
    return f"risk_parameters.{layer}.weight"


def _bad_required_risk_weight_type(m: dict[str, Any]) -> str:
    layer = next(iter(m["risk_parameters"]))
    m["risk_parameters"][layer]["weight"] = "pesado"  # deveria ser number
    return f"risk_parameters.{layer}.weight"


# Conjunto rotulado de receitas: opcionais (Req 5.7) + obrigatórias (Req 8.2).
_MALFORMATIONS: tuple[Malformation, ...] = (
    _bad_expected_domain_type,
    _bad_expected_domain_empty,
    _bad_golden_set_missing_input,
    _bad_golden_set_wrong_input_type,
    _bad_golden_set_extra_prop,
    _bad_discovery_framework_enum,
    _bad_discovery_extra_prop,
    _bad_required_target_ref_empty,
    _bad_required_applicable_layers_empty,
    _bad_required_risk_weight_negative,
    _bad_required_risk_weight_type,
)


# Feature: hybrid-target-discovery, Property 9
# Property 9: Campo opcional malformado é rejeitado nomeando o campo — para todo
# manifesto sem PENDING com um campo opcional malformado (ou um campo obrigatório
# inválido), validate_manifest levanta InvalidManifestError nomeando o ofensor,
# sem VO parcial e sem mutar a entrada.
# Validates: Requirements 5.7, 8.2
@settings(max_examples=100)
@given(
    manifest=_valid_manifests(),
    malformation=st.sampled_from(_MALFORMATIONS),
)
def test_campo_malformado_e_rejeitado_nomeando_o_campo(
    manifest: dict[str, Any],
    malformation: Malformation,
) -> None:
    """Campo malformado → ``InvalidManifestError`` nomeia o ofensor; entrada intacta."""
    # Aplica UMA malformação ao manifesto base válido; a receita devolve o caminho
    # pontuado do campo ofensor que esperamos ver nomeado no erro.
    expected_field = malformation(manifest)

    # Snapshot para provar que a validação não muta a entrada (sem VO parcial).
    manifest_before = copy.deepcopy(manifest)

    with pytest.raises(InvalidManifestError) as exc_info:
        validate_manifest(manifest)

    invalid_fields = exc_info.value.invalid_fields

    # O campo ofensor deve aparecer como chave (ou prefixo de chave, tolerando
    # sufixos de índice/aninhamento como ``[0]``/``.sub``) em ``invalid_fields``.
    assert any(
        key == expected_field or key.startswith(expected_field)
        for key in invalid_fields
    ), (
        f"campo ofensor '{expected_field}' não nomeado; "
        f"invalid_fields={sorted(invalid_fields)}"
    )

    # A validação recebe um ``dict`` e não retorna VO nem muta a entrada: o
    # manifesto permanece idêntico ao estado imediatamente antes da chamada.
    assert manifest == manifest_before
