"""Testes unitários dos value objects de identidade ``LayerId`` e ``RunId``.

Cobrem a rejeição de valores ausentes/vazios/whitespace e a igualdade por valor
(Requisitos 6.1, 7.1, 1.3, 11.6).
"""

import pytest

from qa_platform.domain.value_objects.ids import LayerId, RunId


@pytest.mark.parametrize("value", ["", " ", "   ", "\t", "\n"])
def test_layer_id_rejeita_vazio_ou_whitespace(value: str) -> None:
    """LayerId rejeita ausente/vazio/só-espaços (Req 6.1)."""
    with pytest.raises(ValueError):
        LayerId(value)


@pytest.mark.parametrize("value", ["", " ", "   ", "\t", "\n"])
def test_run_id_rejeita_vazio_ou_whitespace(value: str) -> None:
    """RunId rejeita ausente/vazio/só-espaços (Req 11.6)."""
    with pytest.raises(ValueError):
        RunId(value)


def test_layer_id_iguais_por_valor() -> None:
    """Dois LayerId com o mesmo valor são iguais e têm o mesmo hash."""
    assert LayerId("ai") == LayerId("ai")
    assert hash(LayerId("ai")) == hash(LayerId("ai"))
    assert LayerId("ai") != LayerId("security")


def test_run_id_iguais_por_valor() -> None:
    """Dois RunId com o mesmo valor são iguais e têm o mesmo hash."""
    assert RunId("run-1") == RunId("run-1")
    assert RunId("run-1") != RunId("run-2")
