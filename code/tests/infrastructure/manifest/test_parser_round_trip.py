"""Teste de propriedade do round-trip do Manifest_Parser (Property 8).

Property 8 — Round-trip do parser do manifesto: para todo ``QATargetManifest``
com os campos opcionais (``discovery``, ``expected_domain``, ``golden_set``)
preenchidos de forma arbitrária, serializar o VO para a forma do manifesto
(``dict`` conforme o schema) e fazer o parse de volta produz um VO equivalente
por valor — ``parse(serialize(m)) == m``. Complementarmente, quando os campos
opcionais estão ausentes no manifesto, o parser preenche os VOs default
(``DiscoveryInfo.empty()``, ``expected_domain=None`` e ``golden_set=()``),
confirmando a retrocompatibilidade de código (Requisitos 5.5, 5.6).

O serializador vive neste teste (a produção só precisa do sentido
manifesto→VO); ele espelha o mapeamento do parser, inclusive a tradução
``Framework.NOT_DETECTED`` ↦ ``null`` no campo ``framework``.

# Feature: hybrid-target-discovery, Property 8
"""

from __future__ import annotations

from typing import Any

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.entities.manifest import (
    CostParameters,
    QATargetManifest,
    RiskParameters,
)
from qa_platform.domain.value_objects.discovery import (
    DetectedItem,
    DiscoveryInfo,
    Framework,
)
from qa_platform.domain.value_objects.golden_case import GoldenCase
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.infrastructure.manifest.parser import parse_manifest_text

# --- Geradores de valores conformes ao schema -------------------------------

# Identificadores/strings não-vazios exigidos pelo schema (``minLength: 1``).
# Excluímos surrogates isolados (categoria ``Cs``) por não serem serializáveis.
_non_empty_text = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=16,
)

# Texto livre opcional (pode ser vazio) para notas. Restringe ao mesmo alfabeto
# ASCII imprimível de ``_non_empty_text`` porque o round-trip do teste passa por
# ``yaml.safe_dump(..., allow_unicode=True)`` + ``safe_load``, que normaliza
# quebras de linha/controle Unicode (ex.: U+0085 NEL) para espaço em branco —
# valores que o parser e os VOs preservam fielmente, mas o próprio serializador
# YAML do teste altera, quebrando ``parse(serialize(m)) == m``.
_free_text = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=0,
    max_size=32,
)

_layer_ids = _non_empty_text

# Pesos/limiares não-negativos (schema exige ``minimum: 0``). Restringe a
# inteiros e floats "redondos" para round-trip exato via YAML/``float(...)``.
_non_negative_number = st.integers(min_value=0, max_value=1000)

# Frameworks concretos (o enum inclui NOT_DETECTED, tratado à parte no framework
# predominante). ``frameworks_detected`` só admite os concretos pelo schema.
_concrete_frameworks = st.sampled_from([Framework.AGNO, Framework.LANGGRAPH])


@st.composite
def _detected_items(draw: st.DrawFn) -> tuple[DetectedItem, ...]:
    """Gera uma tupla (possivelmente vazia) de ``DetectedItem`` conformes."""
    items = draw(
        st.lists(
            st.builds(
                DetectedItem,
                identifier=_non_empty_text,
                source=_non_empty_text,
            ),
            max_size=4,
        )
    )
    return tuple(items)


@st.composite
def _discovery_infos(draw: st.DrawFn) -> DiscoveryInfo:
    """Gera um ``DiscoveryInfo`` arbitrário conforme o schema/domínio."""
    detected = draw(st.lists(_concrete_frameworks, max_size=2, unique=True))
    frameworks_detected = tuple(detected)
    if not detected:
        framework = Framework.NOT_DETECTED
    else:
        framework = draw(st.sampled_from(detected))
    return DiscoveryInfo(
        framework=framework,
        frameworks_detected=frameworks_detected,
        ambiguous=draw(st.booleans()),
        tools=draw(_detected_items()),
        prompts=draw(_detected_items()),
        rag=draw(_detected_items()),
        fragility_note=draw(_free_text),
    )


@st.composite
def _golden_cases(draw: st.DrawFn) -> tuple[GoldenCase, ...]:
    """Gera uma tupla (possivelmente vazia) de ``GoldenCase`` conformes."""
    cases = draw(
        st.lists(
            st.builds(
                GoldenCase,
                input=_non_empty_text,
                expected=_non_empty_text,
                note=st.text(
                    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
                    max_size=24,
                ),
            ),
            max_size=4,
        )
    )
    return tuple(cases)


@st.composite
def _manifests(draw: st.DrawFn) -> QATargetManifest:
    """Gera um ``QATargetManifest`` completo com campos opcionais preenchidos."""
    layer_names = draw(st.lists(_layer_ids, min_size=1, max_size=4, unique=True))
    applicable_layers = tuple(LayerId(name) for name in layer_names)

    risk_parameters = {
        layer: RiskParameters(weight=float(draw(_non_negative_number)))
        for layer in applicable_layers
    }

    cost_parameters: dict[LayerId, CostParameters] = {}
    if draw(st.booleans()):
        for layer in applicable_layers:
            cost_parameters[layer] = CostParameters(
                risk_threshold=float(draw(_non_negative_number)),
                estimated_risk=float(draw(_non_negative_number)),
            )

    expected_domain = draw(st.none() | _non_empty_text)

    return QATargetManifest(
        target_ref=draw(_non_empty_text),
        target_version=draw(_non_empty_text),
        applicable_layers=applicable_layers,
        risk_parameters=risk_parameters,
        cost_parameters=cost_parameters,
        discovery=draw(_discovery_infos()),
        expected_domain=expected_domain,
        golden_set=draw(_golden_cases()),
    )


# --- Serializador VO -> manifesto (dict conforme o schema) ------------------


def _framework_to_json(framework: Framework) -> str | None:
    """Traduz ``Framework`` para a forma do schema (``NOT_DETECTED`` ↦ ``null``)."""
    return None if framework is Framework.NOT_DETECTED else framework.value


def _detected_items_to_json(items: tuple[DetectedItem, ...]) -> list[dict[str, str]]:
    """Serializa itens detectados para a forma ``{identifier, source}``."""
    return [{"identifier": item.identifier, "source": item.source} for item in items]


def _discovery_to_json(discovery: DiscoveryInfo) -> dict[str, Any]:
    """Serializa o ``DiscoveryInfo`` para o bloco ``discovery`` do manifesto."""
    return {
        "framework": _framework_to_json(discovery.framework),
        "frameworks_detected": [fw.value for fw in discovery.frameworks_detected],
        "ambiguous": discovery.ambiguous,
        "tools": _detected_items_to_json(discovery.tools),
        "prompts": _detected_items_to_json(discovery.prompts),
        "rag": _detected_items_to_json(discovery.rag),
        "fragility_note": discovery.fragility_note,
    }


def _serialize(manifest: QATargetManifest) -> dict[str, Any]:
    """Serializa o VO para a forma do manifesto (``dict`` conforme o schema)."""
    raw: dict[str, Any] = {
        "target": {
            "ref": manifest.target_ref,
            "version": manifest.target_version,
        },
        "applicable_layers": [layer.value for layer in manifest.applicable_layers],
        "risk_parameters": {
            layer.value: {"weight": params.weight}
            for layer, params in manifest.risk_parameters.items()
        },
    }
    if manifest.cost_parameters:
        raw["cost_parameters"] = {
            layer.value: {
                "risk_threshold": params.risk_threshold,
                "estimated_risk": params.estimated_risk,
            }
            for layer, params in manifest.cost_parameters.items()
        }
    if manifest.expected_domain is not None:
        raw["expected_domain"] = manifest.expected_domain
    if manifest.golden_set:
        raw["golden_set"] = [
            {"input": case.input, "expected": case.expected, "note": case.note}
            for case in manifest.golden_set
        ]
    # ``discovery`` é sempre serializado explicitamente para exercitar o mapeamento
    # (o parser trata ausência como ``DiscoveryInfo.empty()``, coberto abaixo).
    raw["discovery"] = _discovery_to_json(manifest.discovery)
    return raw


# Feature: hybrid-target-discovery, Property 8
# Property 8: Round-trip do parser do manifesto — parse(serialize(m)) == m para
# todo manifesto com os campos opcionais preenchidos.
# Validates: Requirements 5.5, 5.6
@settings(max_examples=100)
@given(manifest=_manifests())
def test_round_trip_do_parser_preserva_o_vo(manifest: QATargetManifest) -> None:
    """``parse(serialize(m))`` é equivalente por valor a ``m`` (Req 5.5, 5.6)."""
    text = yaml.safe_dump(_serialize(manifest), allow_unicode=True)
    parsed = parse_manifest_text(text)
    assert parsed == manifest


# Feature: hybrid-target-discovery, Property 8
# Property 8 (complemento): ausência dos campos opcionais → VOs default.
# Validates: Requirements 5.5, 5.6
@settings(max_examples=100)
@given(manifest=_manifests())
def test_ausencia_de_opcionais_produz_vos_default(
    manifest: QATargetManifest,
) -> None:
    """Sem ``discovery``/``expected_domain``/``golden_set`` → defaults (Req 5.5, 5.6)."""
    raw = _serialize(manifest)
    # Remove os três campos opcionais, simulando um manifesto que não os declara.
    raw.pop("discovery", None)
    raw.pop("expected_domain", None)
    raw.pop("golden_set", None)

    parsed = parse_manifest_text(yaml.safe_dump(raw, allow_unicode=True))

    assert parsed.discovery == DiscoveryInfo.empty()
    assert parsed.expected_domain is None
    assert parsed.golden_set == ()
