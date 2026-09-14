"""Teste de propriedade do determinismo do Target_Discovery (Property 11)."""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qa_platform.domain.exceptions import TargetResolutionError
from qa_platform.infrastructure.manifest.target_discovery import (
    discover_target,
    has_pending_fields,
)

# Conteúdos sintéticos de arquivo Python plausíveis para as heurísticas da Fase 1
# (imports de framework, tools, prompts). Mantém a árvore de repo pequena e
# determinística sem tocar em rede/LLM.
_file_contents = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    max_size=200,
)


# Feature: workflow-orchestrator-skeleton, Property 11
# Property 11: Determinismo do Target_Discovery — a mesma referência resolvível
# produz o mesmo rascunho (iguais em valor), conforme o schema; inclui
# exemplos de pendência e de referência irresolvível → erro.
# Validates: Requirements 9.4; Property 11
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(content=_file_contents)
def test_discover_target_e_deterministico_para_mesma_referencia(
    tmp_path: Path,
    content: str,
) -> None:
    """A mesma referência resolvível produz rascunho idêntico (Req 9.4)."""
    # Arrange — o novo corpo lê o filesystem local; a referência precisa apontar
    # para um artefato real (arquivo/diretório) para produzir um Draft.
    target = tmp_path / "agent.py"
    target.write_text(content, encoding="utf-8")
    target_ref = str(target)

    # Act
    first = discover_target(target_ref)
    second = discover_target(target_ref)

    # Assert
    assert first == second
    assert has_pending_fields(first)


@pytest.mark.parametrize("target_ref", [None, "", "   "])
def test_discover_target_referencia_irresolvivel_levanta_erro(
    target_ref: str | None,
) -> None:
    """Referência ausente ou irresolvível levanta TargetResolutionError (Req 9.5)."""
    with pytest.raises(TargetResolutionError):
        discover_target(target_ref)
