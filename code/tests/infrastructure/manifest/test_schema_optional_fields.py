"""Teste por exemplo — os 3 campos opcionais estão em ``properties`` e fora de ``required``.

Inspeciona o JSON Schema carregado (``load_schema``) e afirma, por exemplo concreto,
que os campos ``discovery``, ``expected_domain`` e ``golden_set`` foram declarados no
nível raiz do schema dentro de ``properties`` **sem** entrar em ``required`` — ou seja,
são opcionais e não quebram a retrocompatibilidade (Req 5.4).

Este é um teste por exemplo (não de propriedade): não usa Hypothesis. Ele verifica
diretamente a estrutura do schema versionado em ``code/schemas/qa-target.schema.json``.

Requisitos verificados:
- 5.1: ``discovery`` é campo opcional, ausente de ``required``.
- 5.2: ``expected_domain`` é campo string opcional, ausente de ``required``.
- 5.3: ``golden_set`` é campo lista opcional, ausente de ``required``.
"""

from __future__ import annotations

import pytest

from qa_platform.infrastructure.manifest.schema import load_schema

# Os 3 campos introduzidos pela feature, todos opcionais no nível raiz do schema.
_OPTIONAL_FIELDS = ("discovery", "expected_domain", "golden_set")


@pytest.mark.parametrize("field", _OPTIONAL_FIELDS)
def test_campo_opcional_declarado_em_properties(field: str) -> None:
    """Cada um dos 3 campos existe em ``properties`` no nível raiz (Req 5.1, 5.2, 5.3)."""
    schema = load_schema()
    properties = schema.get("properties", {})

    assert field in properties, f"campo '{field}' ausente de properties"


@pytest.mark.parametrize("field", _OPTIONAL_FIELDS)
def test_campo_opcional_fora_de_required(field: str) -> None:
    """Nenhum dos 3 campos aparece em ``required`` no nível raiz (Req 5.1, 5.2, 5.3)."""
    schema = load_schema()
    required = schema.get("required", [])

    assert field not in required, f"campo opcional '{field}' não deve estar em required"


def test_required_permanece_apenas_com_os_campos_obrigatorios() -> None:
    """``required`` mantém somente os campos obrigatórios originais (retrocompat, Req 5.4)."""
    schema = load_schema()

    assert set(schema.get("required", [])) == {
        "target",
        "applicable_layers",
        "risk_parameters",
    }
