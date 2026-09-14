"""Teste de propriedade — sugestões nunca sobrescrevem silenciosamente (Property 6).

Property 6 — Sugestões nunca sobrescrevem silenciosamente: para todo Draft
determinístico e toda saída de LLM (``expected_domain`` e/ou ``golden_set``),
:meth:`LLMEnricher.enrich` produz um :class:`AnnotatedDraft` em que:

1. ``base_fields`` é uma cópia **fiel** do Draft — mesmas chaves, mesmos valores,
   nada removido/alterado/reordenado (Req 7.3) — e o Draft de entrada **não** é
   mutado.
2. Cada saída ``expected_domain`` vira uma :class:`Suggestion` com
   ``origin == "sugestão"`` e ``state == "pendente"`` (Req 7.1); cada item de
   ``golden_set`` vira uma ``Suggestion`` com ``origin == "candidato"`` e
   ``state == "pendente"`` (Req 7.2).
3. **Nenhum** valor de sugestão pendente é aplicado em ``base_fields``: os campos
   permanecem idênticos ao Draft independentemente das sugestões (Req 7.6).
4. Quando o Draft **já** traz um valor não vazio para ``expected_domain``, esse
   valor é **preservado** em ``base_fields`` e a sugestão entra como entrada
   **separada** (Req 7.4).

MOCKING: o provider de LLM (Agno) é isolado ao substituir
``LLMEnricher._enrich_via_agno`` por um stub que devolve as ``outputs`` geradas
por Hypothesis. Assim a lógica real sob teste — deepcopy fiel de ``base_fields``,
o ``_to_suggestions`` (marcação ``origin``/``state``) e a não-aplicação de
pendentes — roda de fato, sem qualquer chamada de rede/LLM. ``MODEL_PROVIDER`` é
definido via ``monkeypatch.setenv`` para o fail-fast do :class:`SecretResolver`
passar (Req 8.4), usando um ``SecretResolver`` real.

# Feature: hybrid-target-discovery, Property 6
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.enrichment.annotated_draft import AnnotatedDraft
from qa_platform.infrastructure.enrichment.llm_enricher import (
    MODEL_PROVIDER_ENV,
    LLMEnricher,
)
from qa_platform.infrastructure.secrets.resolver import SecretResolver

# --- Estratégias -------------------------------------------------------------

# Valores escalares simples que compõem estruturas arbitrárias do Draft.
_scalars = st.one_of(
    st.text(max_size=20),
    st.integers(),
    st.booleans(),
    st.none(),
)

# Estrutura arbitrária (rasa) para valores de campos do Draft: escalares,
# listas e dicts de escalares. Suficiente para exercer a cópia fiel sem
# explodir o espaço de busca.
_json_like = st.recursive(
    _scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=10), children, max_size=4),
    ),
    max_leaves=10,
)

# Draft determinístico com a forma típica da Fase 1 (chaves target/
# applicable_layers/risk_parameters) mais chaves extras arbitrárias. Um
# ``expected_domain`` pré-existente NÃO é incluído aqui; um teste dedicado cobre
# o caso de valor pré-existente (Req 7.4).
_base_drafts = st.fixed_dictionaries(
    {
        "target": _json_like,
        "applicable_layers": st.lists(st.text(max_size=15), max_size=5),
        "risk_parameters": st.dictionaries(
            st.text(max_size=10), _json_like, max_size=4
        ),
    },
).flatmap(
    lambda base: st.dictionaries(
        # Chaves extras que não colidem com as fixas nem com expected_domain.
        keys=st.text(max_size=10).filter(
            lambda k: (
                k
                not in {
                    "target",
                    "applicable_layers",
                    "risk_parameters",
                    "expected_domain",
                }
            )
        ),
        values=_json_like,
        max_size=3,
    ).map(lambda extra: {**base, **extra})
)

# Saída do LLM: ``expected_domain`` (str opcional) e/ou ``golden_set`` (lista de
# casos). Ao menos uma das chaves costuma estar presente, mas o caso vazio
# também é válido (nenhuma sugestão).
_expected_domain_out = st.text(min_size=1, max_size=30)
_golden_case = st.fixed_dictionaries(
    {
        "input": st.text(max_size=20),
        "expected": st.text(max_size=20),
    }
)
_golden_set_out = st.lists(_golden_case, max_size=5)

_llm_outputs = st.fixed_dictionaries(
    {},
    optional={
        "expected_domain": _expected_domain_out,
        "golden_set": _golden_set_out,
    },
)


def _make_enricher_with_stub(
    monkeypatch: pytest.MonkeyPatch, outputs: dict[str, object]
) -> LLMEnricher:
    """Cria um ``LLMEnricher`` real com o seam de Agno isolado.

    Define ``MODEL_PROVIDER`` (fail-fast do resolver passa) e substitui
    ``_enrich_via_agno`` por um stub que devolve as ``outputs`` geradas — a
    lógica real de ``base_fields``/``_to_suggestions`` continua rodando.
    """
    monkeypatch.setenv(MODEL_PROVIDER_ENV, "aws:claude-3-sonnet")
    enricher = LLMEnricher(SecretResolver())

    def _stub_enrich_via_agno(
        self: LLMEnricher, provider: str, base_fields: dict[str, object]
    ) -> list[Any]:
        # Delega ao conversor real para exercer a marcação origin/state (Req 7).
        return LLMEnricher._to_suggestions(outputs, base_fields)

    monkeypatch.setattr(
        LLMEnricher, "_enrich_via_agno", _stub_enrich_via_agno, raising=True
    )
    return enricher


# Feature: hybrid-target-discovery, Property 6
# Property 6: Sugestões nunca sobrescrevem silenciosamente.
# Validates: Requirements 7.1, 7.2, 7.3, 7.6, 8.4
@settings(max_examples=100)
@given(draft=_base_drafts, outputs=_llm_outputs)
def test_base_fields_e_copia_fiel_e_sugestoes_sao_marcadas(
    draft: dict[str, object], outputs: dict[str, object]
) -> None:
    """base_fields = cópia fiel do Draft; sugestões marcadas e não aplicadas."""
    # Arrange — snapshot do Draft para provar não-mutação da entrada.
    original = copy.deepcopy(draft)
    monkeypatch = pytest.MonkeyPatch()
    try:
        enricher = _make_enricher_with_stub(monkeypatch, outputs)

        # Act
        annotated = enricher.enrich(draft)
    finally:
        monkeypatch.undo()

    # Assert — tipo de retorno.
    assert isinstance(annotated, AnnotatedDraft)

    # Cópia fiel: mesmas chaves, mesmos valores, mesma ordem (Req 7.3).
    assert annotated.base_fields == draft
    assert list(annotated.base_fields.keys()) == list(draft.keys())

    # Entrada não mutada e cópia independente do objeto original.
    assert draft == original
    assert annotated.base_fields is not draft

    # Marcação origin/state por origem da sugestão (Req 7.1, 7.2).
    expected_domain_out = outputs.get("expected_domain")
    golden_set_out = outputs.get("golden_set")

    domain_suggestions = [
        s for s in annotated.suggestions if s.field == "expected_domain"
    ]
    golden_suggestions = [s for s in annotated.suggestions if s.field == "golden_set"]

    if expected_domain_out is not None:
        assert len(domain_suggestions) == 1
        assert domain_suggestions[0].value == expected_domain_out
    else:
        assert domain_suggestions == []

    for suggestion in domain_suggestions:
        assert suggestion.origin == "sugestão"  # Req 7.1
        assert suggestion.state == "pendente"

    expected_golden = golden_set_out if isinstance(golden_set_out, list) else []
    assert len(golden_suggestions) == len(expected_golden)
    for suggestion, case in zip(golden_suggestions, expected_golden, strict=True):
        assert suggestion.origin == "candidato"  # Req 7.2
        assert suggestion.state == "pendente"
        assert suggestion.value == case

    # Nenhuma sugestão pendente é aplicada em base_fields (Req 7.6): os campos
    # permanecem idênticos ao Draft, mesmo havendo sugestões.
    assert annotated.base_fields == draft
    for suggestion in annotated.suggestions:
        assert (
            suggestion.field not in draft
            or draft[suggestion.field] == (annotated.base_fields[suggestion.field])
        )


# Feature: hybrid-target-discovery, Property 6
# Property 6: Sugestões nunca sobrescrevem silenciosamente.
# Validates: Requirements 7.4, 7.6
@settings(max_examples=100)
@given(
    draft=_base_drafts,
    existing_domain=st.text(min_size=1, max_size=30),
    suggested_domain=st.text(min_size=1, max_size=30),
    golden_set_out=_golden_set_out,
)
def test_valor_preexistente_e_preservado_e_sugestao_e_separada(
    draft: dict[str, object],
    existing_domain: str,
    suggested_domain: str,
    golden_set_out: list[dict[str, str]],
) -> None:
    """Valor pré-existente de expected_domain é preservado; sugestão é separada."""
    # Arrange — Draft JÁ traz expected_domain não vazio (Req 7.4).
    draft_with_domain = {**draft, "expected_domain": existing_domain}
    original = copy.deepcopy(draft_with_domain)
    outputs: dict[str, object] = {
        "expected_domain": suggested_domain,
        "golden_set": golden_set_out,
    }

    monkeypatch = pytest.MonkeyPatch()
    try:
        enricher = _make_enricher_with_stub(monkeypatch, outputs)
        # Act
        annotated = enricher.enrich(draft_with_domain)
    finally:
        monkeypatch.undo()

    # Assert — valor pré-existente preservado em base_fields (Req 7.4, 7.6).
    assert annotated.base_fields["expected_domain"] == existing_domain
    assert annotated.base_fields == draft_with_domain
    assert draft_with_domain == original  # entrada não mutada

    # A sugestão entra como entrada SEPARADA, sem sobrescrever o valor do Draft.
    domain_suggestions = [
        s for s in annotated.suggestions if s.field == "expected_domain"
    ]
    assert len(domain_suggestions) == 1
    assert domain_suggestions[0].value == suggested_domain
    assert domain_suggestions[0].origin == "sugestão"
    assert domain_suggestions[0].state == "pendente"
    # base_fields continua com o valor original, não o sugerido.
    assert annotated.base_fields["expected_domain"] != suggested_domain or (
        suggested_domain == existing_domain
    )
