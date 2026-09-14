"""Testes unitários dos VOs de descoberta estática.

Cobrem imutabilidade (``frozen``), igualdade por valor, hashability e o
construtor ``DiscoveryInfo.empty()`` retornando um VO vazio/default
(Requisitos 4.5, 5.3, 10.5). São testes por exemplo, sem AWS, rede ou
Hypothesis.
"""

import dataclasses

import pytest

from qa_platform.domain.value_objects.discovery import (
    DetectedItem,
    DiscoveryInfo,
    Framework,
)

# --- Framework enum (subclasse de str) ---------------------------------------


def test_framework_valores_sao_strings() -> None:
    """``Framework`` herda de ``str``: valores comparam como strings (Req 4.5)."""
    assert Framework.AGNO == "agno"
    assert Framework.LANGGRAPH == "langgraph"
    assert Framework.NOT_DETECTED == "not_detected"
    assert isinstance(Framework.AGNO, str)


def test_framework_value_expoe_string_bruta() -> None:
    """O atributo ``.value`` de cada membro é a string correspondente."""
    assert Framework.AGNO.value == "agno"
    assert Framework.LANGGRAPH.value == "langgraph"
    assert Framework.NOT_DETECTED.value == "not_detected"


# --- DetectedItem: imutabilidade, igualdade, hashability ---------------------


def test_detected_item_e_imutavel() -> None:
    """``DetectedItem`` é ``frozen``: atribuir atributo levanta erro (Req 4.5)."""
    item = DetectedItem(identifier="minha_tool", source="src/tools.py")
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.identifier = "outra_tool"  # type: ignore[misc]


def test_detected_item_igual_por_valor() -> None:
    """Dois ``DetectedItem`` com os mesmos campos são iguais por valor."""
    a = DetectedItem(identifier="t", source="src/a.py")
    b = DetectedItem(identifier="t", source="src/a.py")
    assert a == b


def test_detected_item_diferente_quando_campo_muda() -> None:
    """``DetectedItem`` difere quando qualquer campo diverge."""
    base = DetectedItem(identifier="t", source="src/a.py")
    assert base != DetectedItem(identifier="t", source="src/b.py")
    assert base != DetectedItem(identifier="u", source="src/a.py")


def test_detected_item_e_hashable() -> None:
    """``DetectedItem`` é hashable (frozen) e utilizável em ``set`` (Req 4.5)."""
    a = DetectedItem(identifier="t", source="src/a.py")
    b = DetectedItem(identifier="t", source="src/a.py")
    c = DetectedItem(identifier="u", source="src/b.py")
    assert {a, b, c} == {a, c}


# --- DiscoveryInfo: imutabilidade, igualdade, hashability --------------------


def test_discovery_info_e_imutavel() -> None:
    """``DiscoveryInfo`` é ``frozen``: atribuir atributo levanta erro (Req 4.5)."""
    info = DiscoveryInfo(framework=Framework.AGNO)
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.framework = Framework.LANGGRAPH  # type: ignore[misc]


def test_discovery_info_igual_por_valor() -> None:
    """Dois ``DiscoveryInfo`` com campos idênticos são iguais por valor."""
    item = DetectedItem(identifier="t", source="src/a.py")
    a = DiscoveryInfo(
        framework=Framework.AGNO,
        frameworks_detected=(Framework.AGNO,),
        ambiguous=False,
        tools=(item,),
        fragility_note="revisar",
    )
    b = DiscoveryInfo(
        framework=Framework.AGNO,
        frameworks_detected=(Framework.AGNO,),
        ambiguous=False,
        tools=(item,),
        fragility_note="revisar",
    )
    assert a == b


def test_discovery_info_diferente_quando_campo_muda() -> None:
    """``DiscoveryInfo`` difere quando qualquer campo diverge."""
    base = DiscoveryInfo(framework=Framework.AGNO)
    assert base != DiscoveryInfo(framework=Framework.LANGGRAPH)
    assert base != DiscoveryInfo(framework=Framework.AGNO, ambiguous=True)


def test_discovery_info_e_hashable() -> None:
    """``DiscoveryInfo`` é hashable e utilizável em ``set`` (frozen)."""
    a = DiscoveryInfo(framework=Framework.AGNO)
    b = DiscoveryInfo(framework=Framework.AGNO)
    c = DiscoveryInfo(framework=Framework.LANGGRAPH)
    assert {a, b, c} == {a, c}


# --- DiscoveryInfo.empty(): VO vazio/default ---------------------------------


def test_discovery_info_empty_retorna_defaults() -> None:
    """``empty()`` retorna VO com todos os campos vazios/default (Req 4.5)."""
    info = DiscoveryInfo.empty()
    assert info.framework == Framework.NOT_DETECTED
    assert info.frameworks_detected == ()
    assert info.ambiguous is False
    assert info.tools == ()
    assert info.prompts == ()
    assert info.rag == ()
    assert info.fragility_note == ""


def test_discovery_info_empty_igual_ao_construtor_default() -> None:
    """``empty()`` é equivalente a instanciar sem argumentos."""
    assert DiscoveryInfo.empty() == DiscoveryInfo()
