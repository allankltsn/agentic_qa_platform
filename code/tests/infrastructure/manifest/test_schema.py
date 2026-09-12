"""Teste de propriedade da validação de schema (Property 9).

# Feature: workflow-orchestrator-skeleton, Property 9
"""

from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.exceptions import InvalidManifestError
from qa_platform.infrastructure.manifest.schema import validate_manifest

_VALID_MANIFEST: dict[str, object] = {
    "target": {"ref": "repo/example", "version": "1.0.0"},
    "applicable_layers": ["ai"],
    "risk_parameters": {"ai": {"weight": 0.5}},
}


# Mutações que tocam a MESMA chave `target` são mutuamente exclusivas: combiná-las
# faz uma sobrescrever a outra, produzindo uma expectativa impossível (ex.: esperar
# `target` E `target.version` quando `target` virou string). O gerador escolhe no
# máximo uma mutação por grupo conflitante, garantindo expectativas coerentes.
_TARGET_MUTATIONS = ("missing_target", "missing_version", "invalid_target_type")
_RISK_MUTATIONS = (
    "missing_risk_parameters",
    "invalid_weight_type",
    "invalid_weight_minimum",
)
_INDEPENDENT_MUTATIONS = ("missing_applicable_layers",)


@st.composite
def _invalid_manifest_mutations(draw: st.DrawFn) -> tuple[dict[str, object], set[str]]:
    """Gera manifesto com subconjunto não-vazio de campos inválidos.

    Escolhe no máximo uma mutação por grupo que compartilha a mesma chave
    (``target``, ``risk_parameters``), evitando mutações conflitantes que se
    sobrescrevem e tornam a expectativa impossível de satisfazer.
    """
    manifest = deepcopy(_VALID_MANIFEST)
    expected: set[str] = set()

    chosen: list[str] = []
    target_choice = draw(st.sampled_from((None, *_TARGET_MUTATIONS)))
    if target_choice is not None:
        chosen.append(target_choice)
    risk_choice = draw(st.sampled_from((None, *_RISK_MUTATIONS)))
    if risk_choice is not None:
        chosen.append(risk_choice)
    for independent in _INDEPENDENT_MUTATIONS:
        if draw(st.booleans()):
            chosen.append(independent)

    # Garante subconjunto NÃO-vazio (Property 9 exige ao menos um campo inválido).
    if not chosen:
        chosen.append(draw(st.sampled_from(_TARGET_MUTATIONS + _RISK_MUTATIONS)))

    for mutation in chosen:
        if mutation == "missing_target":
            manifest.pop("target", None)
            expected.add("target")
        elif mutation == "missing_version":
            manifest["target"] = {"ref": "repo/example"}
            expected.add("target.version")
        elif mutation == "missing_applicable_layers":
            manifest.pop("applicable_layers", None)
            expected.add("applicable_layers")
        elif mutation == "missing_risk_parameters":
            manifest.pop("risk_parameters", None)
            expected.add("risk_parameters")
        elif mutation == "invalid_target_type":
            manifest["target"] = "not-an-object"
            expected.add("target")
        elif mutation == "invalid_weight_type":
            manifest["risk_parameters"] = {"ai": {"weight": "heavy"}}
            expected.add("risk_parameters.ai.weight")
        elif mutation == "invalid_weight_minimum":
            manifest["risk_parameters"] = {"ai": {"weight": -1}}
            expected.add("risk_parameters.ai.weight")

    return manifest, expected


# Feature: workflow-orchestrator-skeleton, Property 9
# Property 9: Validação de schema nomeia todos os campos inválidos — manifest
# com subconjunto não-vazio de campos ausentes/tipo inválido/valor fora dos
# limites é rejeitado nomeando cada campo problemático com o motivo.
# Validates: Requirements 8.3; Property 9
@settings(max_examples=100)
@given(case=_invalid_manifest_mutations())
def test_validate_manifest_nomeia_todos_os_campos_invalidos(
    case: tuple[dict[str, object], set[str]],
) -> None:
    """validate_manifest agrega e nomeia cada campo inválido (Req 8.3)."""
    manifest, expected_fields = case
    with pytest.raises(InvalidManifestError) as exc_info:
        validate_manifest(manifest)

    reported = set(exc_info.value.invalid_fields)
    assert expected_fields.issubset(reported)
