"""Teste de propriedade da retrocompatibilidade do schema (Property 2).

Property 2 — Retrocompatibilidade do schema: para todo manifesto válido segundo o
schema *anterior* (antes de existirem os 3 campos opcionais ``discovery``,
``expected_domain`` e ``golden_set``), a validação contra o schema *estendido*
também é válida. Os 3 campos novos são opcionais (estão em ``properties`` mas fora
de ``required``), logo um manifesto antigo — que não os contém — permanece aceito.

A quantificação é universal sobre o espaço de manifestos válidos pelo schema
anterior; Hypothesis os gera e afirmamos que ``validate_manifest`` não levanta.

# Feature: hybrid-target-discovery, Property 2
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.manifest.schema import validate_manifest

# Campos introduzidos pela feature; um manifesto do schema ANTERIOR não os contém.
# A ausência deles é o cerne da retrocompatibilidade verificada por esta propriedade.
_NEW_FIELDS = ("discovery", "expected_domain", "golden_set")

# Identificadores de camada não-vazios (schema exige ``minLength: 1``, sem duplicatas).
_layer_ids = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=12,
)

# Strings não-vazias para ``target.ref``/``target.version`` (schema exige ``minLength: 1``).
_non_empty_text = st.text(min_size=1, max_size=24).filter(lambda s: s.strip() != "")

# Pesos/limiares não-negativos (schema exige ``minimum: 0``).
_non_negative_number = st.floats(
    min_value=0, max_value=1_000, allow_nan=False, allow_infinity=False
) | st.integers(min_value=0, max_value=1_000)


@st.composite
def _old_schema_manifests(draw: st.DrawFn) -> dict[str, object]:
    """Gera manifestos válidos pelo schema ANTERIOR (sem os 3 campos novos).

    Varia ``target`` (``ref``/``version`` não-vazios), ``applicable_layers`` (1..N
    ids únicos e não-vazios), ``risk_parameters`` (uma entrada por camada com
    ``weight`` >= 0) e, opcionalmente, ``cost_parameters`` (por camada, com
    ``risk_threshold``/``estimated_risk`` opcionais >= 0). Nunca emite ``discovery``,
    ``expected_domain`` nem ``golden_set`` — um manifesto antigo não os possui.
    """
    layers = draw(st.lists(_layer_ids, min_size=1, max_size=5, unique=True))

    risk_parameters = {
        layer: {"weight": draw(_non_negative_number)} for layer in layers
    }

    manifest: dict[str, object] = {
        "target": {
            "ref": draw(_non_empty_text),
            "version": draw(_non_empty_text),
        },
        "applicable_layers": layers,
        "risk_parameters": risk_parameters,
    }

    # ``cost_parameters`` é opcional já no schema anterior; inclui-o em parte dos casos.
    if draw(st.booleans()):
        cost_parameters: dict[str, dict[str, float]] = {}
        for layer in layers:
            entry: dict[str, float] = {}
            if draw(st.booleans()):
                entry["risk_threshold"] = draw(_non_negative_number)
            if draw(st.booleans()):
                entry["estimated_risk"] = draw(_non_negative_number)
            cost_parameters[layer] = entry
        manifest["cost_parameters"] = cost_parameters

    return manifest


# Feature: hybrid-target-discovery, Property 2
# Property 2: Retrocompatibilidade do schema — todo manifesto válido pelo schema
# anterior (sem discovery/expected_domain/golden_set) continua válido no schema
# estendido, pois os 3 campos novos são opcionais (fora de ``required``).
# Validates: Requirements 5.4
@settings(max_examples=100)
@given(manifest=_old_schema_manifests())
def test_manifesto_do_schema_anterior_permanece_valido(
    manifest: dict[str, object],
) -> None:
    """Manifesto do schema anterior não é rejeitado pelo schema estendido (Req 5.4)."""
    # Precondição da propriedade: o gerador não emite nenhum dos campos novos.
    assert all(field not in manifest for field in _NEW_FIELDS)

    # ``validate_manifest`` retorna ``None`` em sucesso e levanta em falha; a
    # ausência de exceção é a afirmação de retrocompatibilidade.
    validate_manifest(manifest)
