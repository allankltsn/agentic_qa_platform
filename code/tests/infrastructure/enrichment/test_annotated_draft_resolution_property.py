"""Teste de propriedade da máquina de estados da resolução de sugestão (Property 7).

Property 7 — Máquina de estados da resolução de sugestão: para toda
:class:`Suggestion` no estado ``"pendente"`` e toda ação válida em
``{aceitar, editar, descartar}``, ``Suggestion.resolve`` transiciona ``state``
para o estado correspondente do mapa determinístico
(``aceitar → aceito``, ``editar → editado``, ``descartar → descartado``),
aplicando **exatamente uma** ação: a instância original permanece inalterada e
apenas a cópia retornada carrega o novo estado.

A máquina de estados é fechada e defensiva:

1. **Transição válida** — a partir de ``"pendente"``, cada ação válida leva ao
   estado esperado; ``editar`` com novo valor substitui ``value``, enquanto
   ``aceitar``/``descartar`` preservam ``value``.
2. **Exatamente uma ação** — resolver não muta a instância de origem (transição
   imutável); só a nova :class:`Suggestion` reflete o estado resolvido.
3. **Ação inválida não altera estado** — qualquer string fora do conjunto válido
   retorna uma cópia com o mesmo estado ``"pendente"``.
4. **Idempotência de resolvidas** — resolver uma sugestão já resolvida
   (``aceito``/``editado``/``descartado``) com qualquer ação não altera o estado.

Hypothesis gera a sugestão pendente (``field``/``value``/``origin``), a ação
válida, um novo valor de edição e strings de ação inválidas. Sem AWS envolvida
(modelo Pydantic puro de borda), portanto sem ``moto``.

# Feature: hybrid-target-discovery, Property 7
"""

from __future__ import annotations

from typing import cast

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.enrichment.annotated_draft import (
    ResolutionAction,
    Suggestion,
    SuggestionField,
    SuggestionOrigin,
    SuggestionState,
)

# --- Estratégias -------------------------------------------------------------

# Conjuntos fechados dos campos/origens válidos das sugestões.
_fields: st.SearchStrategy[SuggestionField] = st.sampled_from(
    ("expected_domain", "golden_set")
)
_origins: st.SearchStrategy[SuggestionOrigin] = st.sampled_from(
    ("sugestão", "candidato")
)

# Estados já resolvidos (não-``pendente``) para a máquina defensiva.
_resolved_states: tuple[SuggestionState, ...] = ("aceito", "editado", "descartado")

# Mapa determinístico ação válida -> estado esperado (espelha _ACTION_TO_STATE).
_ACTION_TO_STATE: dict[ResolutionAction, SuggestionState] = {
    "aceitar": "aceito",
    "editar": "editado",
    "descartar": "descartado",
}
_valid_actions: st.SearchStrategy[ResolutionAction] = st.sampled_from(
    tuple(_ACTION_TO_STATE)
)

# Valores de sugestão simples e distinguíveis (str para expected_domain, dict
# para golden_set), suficientes para verificar preservação/substituição.
_values = st.one_of(
    st.text(max_size=20),
    st.dictionaries(
        keys=st.sampled_from(("input", "expected", "note")),
        values=st.text(max_size=20),
        max_size=3,
    ),
)

# Strings de ação inválidas: qualquer texto fora do conjunto válido.
_invalid_actions = st.text(max_size=15).filter(lambda s: s not in _ACTION_TO_STATE)


def _make_pending(
    field: SuggestionField, value: object, origin: SuggestionOrigin
) -> Suggestion:
    """Constrói uma :class:`Suggestion` no estado inicial ``"pendente"``."""
    return Suggestion(field=field, value=value, origin=origin)


# Feature: hybrid-target-discovery, Property 7
# Property 7: Máquina de estados da resolução de sugestão.
# Validates: Requirements 7.5
@settings(max_examples=100)
@given(
    field=_fields,
    value=_values,
    origin=_origins,
    action=_valid_actions,
    new_value=_values,
)
def test_acao_valida_transiciona_e_aplica_exatamente_uma(
    field: SuggestionField,
    value: object,
    origin: SuggestionOrigin,
    action: ResolutionAction,
    new_value: object,
) -> None:
    """Ação válida em 'pendente' transiciona para o estado esperado (Req 7.5).

    Verifica a transição correta, que exatamente uma ação é aplicada (original
    inalterada) e a política de valor: ``editar`` substitui, demais preservam.
    """
    # Arrange
    pending = _make_pending(field, value, origin)

    # Act — ``editar`` recebe novo valor; demais ações não usam ``value``.
    if action == "editar":
        resolved = pending.resolve(action, value=new_value)
    else:
        resolved = pending.resolve(action)

    # Assert — transição correta segundo o mapa determinístico.
    assert resolved.state == _ACTION_TO_STATE[action]

    # Exatamente uma ação: a instância original permanece 'pendente' e intacta.
    assert pending.state == "pendente"
    assert resolved is not pending

    # Política de valor: editar substitui; aceitar/descartar preservam.
    if action == "editar":
        assert resolved.value == new_value
    else:
        assert resolved.value == value

    # Campos não relacionados à resolução são preservados na cópia.
    assert resolved.field == field
    assert resolved.origin == origin


# Feature: hybrid-target-discovery, Property 7
# Property 7: Máquina de estados da resolução de sugestão.
# Validates: Requirements 7.5
@settings(max_examples=100)
@given(
    field=_fields,
    value=_values,
    origin=_origins,
    action=_invalid_actions,
)
def test_acao_invalida_nao_altera_estado(
    field: SuggestionField,
    value: object,
    origin: SuggestionOrigin,
    action: str,
) -> None:
    """Ação fora do conjunto válido mantém o estado 'pendente' (Req 7.5)."""
    # Arrange
    pending = _make_pending(field, value, origin)

    # Act — ação inválida (string arbitrária fora do conjunto). O ``cast``
    # documenta que passamos deliberadamente um valor fora de ``ResolutionAction``
    # para exercitar o ramo defensivo da máquina de estados.
    result = pending.resolve(cast("ResolutionAction", action))

    # Assert — estado inalterado e original intacto.
    assert result.state == "pendente"
    assert pending.state == "pendente"
    assert result.value == value


# Feature: hybrid-target-discovery, Property 7
# Property 7: Máquina de estados da resolução de sugestão.
# Validates: Requirements 7.5
@settings(max_examples=100)
@given(
    field=_fields,
    value=_values,
    origin=_origins,
    initial_state=st.sampled_from(_resolved_states),
    action=st.one_of(_valid_actions, _invalid_actions),
    new_value=_values,
)
def test_sugestao_ja_resolvida_nao_transiciona(
    field: SuggestionField,
    value: object,
    origin: SuggestionOrigin,
    initial_state: SuggestionState,
    action: str,
    new_value: object,
) -> None:
    """Resolver uma sugestão já resolvida não altera seu estado (Req 7.5)."""
    # Arrange — sugestão em estado terminal (não-'pendente').
    resolved_input = Suggestion(
        field=field, value=value, origin=origin, state=initial_state
    )

    # Act — a ação pode ser válida ou inválida; nenhuma transição parte de um
    # estado já resolvido, então o ``cast`` cobre ambos os casos gerados.
    result = resolved_input.resolve(cast("ResolutionAction", action), value=new_value)

    # Assert — máquina só transiciona a partir de 'pendente'.
    assert result.state == initial_state
    assert resolved_input.state == initial_state
