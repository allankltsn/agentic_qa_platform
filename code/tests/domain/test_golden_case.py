"""Testes unitários de ``GoldenCase``.

Cobrem imutabilidade (``frozen``), igualdade por valor e o default de ``note``
(Requisitos 5.3, 10.5). São testes por exemplo, sem AWS, rede ou Hypothesis.
"""

import dataclasses

import pytest

from qa_platform.domain.value_objects.golden_case import GoldenCase


def test_golden_case_e_imutavel() -> None:
    """``GoldenCase`` é ``frozen``: atribuir atributo levanta erro (Req 5.3)."""
    case = GoldenCase(input="entrada", expected="saida")
    with pytest.raises(dataclasses.FrozenInstanceError):
        case.expected = "outra"  # type: ignore[misc]


def test_golden_case_igual_por_valor() -> None:
    """Dois ``GoldenCase`` com os mesmos campos são iguais por valor."""
    a = GoldenCase(input="e", expected="s", note="n")
    b = GoldenCase(input="e", expected="s", note="n")
    assert a == b


def test_golden_case_diferente_quando_campo_muda() -> None:
    """``GoldenCase`` difere quando qualquer campo diverge."""
    base = GoldenCase(input="e", expected="s", note="n")
    assert base != GoldenCase(input="x", expected="s", note="n")
    assert base != GoldenCase(input="e", expected="x", note="n")
    assert base != GoldenCase(input="e", expected="s", note="x")


def test_golden_case_note_default_vazio() -> None:
    """``note`` é opcional e assume string vazia por default (Req 5.3)."""
    case = GoldenCase(input="e", expected="s")
    assert case.note == ""
    assert case == GoldenCase(input="e", expected="s", note="")


def test_golden_case_e_hashable() -> None:
    """``GoldenCase`` é hashable (frozen) e utilizável em ``set``."""
    a = GoldenCase(input="e", expected="s")
    b = GoldenCase(input="e", expected="s")
    c = GoldenCase(input="x", expected="s")
    assert {a, b, c} == {a, c}
