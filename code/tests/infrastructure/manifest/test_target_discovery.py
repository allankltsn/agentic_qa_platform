"""Teste de propriedade do determinismo do Target_Discovery (Property 11)."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.exceptions import TargetResolutionError
from qa_platform.infrastructure.manifest.target_discovery import (
    discover_target,
    has_pending_fields,
)

_resolvable_refs = st.text(min_size=1, max_size=40).filter(lambda v: v.strip() != "")


# Feature: workflow-orchestrator-skeleton, Property 11
# Property 11: Determinismo do Target_Discovery — a mesma referência resolvível
# produz o mesmo rascunho (iguais em valor), conforme o schema; inclui
# exemplos de pendência e de referência irresolvível → erro.
# Validates: Requirements 9.4; Property 11
@settings(max_examples=100)
@given(target_ref=_resolvable_refs)
def test_discover_target_e_deterministico_para_mesma_referencia(
    target_ref: str,
) -> None:
    """A mesma referência resolvível produz rascunho idêntico (Req 9.4)."""
    first = discover_target(target_ref)
    second = discover_target(target_ref)
    assert first == second
    assert has_pending_fields(first)


@pytest.mark.parametrize("target_ref", [None, "", "   "])
def test_discover_target_referencia_irresolvivel_levanta_erro(
    target_ref: str | None,
) -> None:
    """Referência ausente ou irresolvível levanta TargetResolutionError (Req 9.5)."""
    with pytest.raises(TargetResolutionError):
        discover_target(target_ref)
