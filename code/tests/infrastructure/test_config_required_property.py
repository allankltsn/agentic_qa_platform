"""Teste de propriedade da falha rápida agregada de config (Property 2).

# Feature: executable-environment-bootstrap, Property 2

Property 2: Falha rápida agregada de variáveis obrigatórias.
- Para qualquer ambiente em que um subconjunto NÃO-VAZIO das variáveis
  obrigatórias esteja ausente ou tenha valor vazio/só-whitespace, ``load_settings``
  deve levantar ``MissingConfigError`` (impedindo a inicialização).
- A mensagem do erro deve conter o nome de CADA variável obrigatória ausente
  desse subconjunto.

A propriedade é escrita de forma genérica sobre ``_REQUIRED``: continua válida
se o conjunto de obrigatórias crescer no futuro. As variáveis obrigatórias fora
do subconjunto ausente recebem valores válidos, isolando o efeito do subconjunto
gerado.

Validates: Requirements 1.4, 7.2, 7.3
"""

from __future__ import annotations

import os

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.config import (
    MissingConfigError,
    _REQUIRED,
    load_settings,
)

# Valor "ausente": None (variável não definida), vazio ou apenas whitespace.
_absent_values = st.one_of(
    st.none(),
    st.sampled_from(["", " ", "   ", "\t", "\n", " \t \n "]),
)

# Valor "presente"/válido: não-vazio e não apenas whitespace após strip.
_present_values = st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != "")


@st.composite
def _missing_subset(draw: st.DrawFn) -> frozenset[str]:
    """Subconjunto NÃO-VAZIO das variáveis obrigatórias a tornar ausentes."""
    return frozenset(
        draw(
            st.sets(
                st.sampled_from(_REQUIRED),
                min_size=1,
                max_size=len(_REQUIRED),
            )
        )
    )


@settings(max_examples=200)
@given(
    missing=_missing_subset(),
    absent_value=_absent_values,
    valid_value=_present_values,
)
def test_aggregated_fail_fast_names_every_missing_required(
    missing: frozenset[str],
    absent_value: str | None,
    valid_value: str,
) -> None:
    """Property 2: falha rápida agregada nomeando CADA obrigatória ausente.

    # Feature: executable-environment-bootstrap, Property 2
    Validates: Requirements 1.4, 7.2, 7.3
    """
    # Gerencia os.environ manualmente com try/finally (Hypothesis reexecuta o
    # corpo muitas vezes; monkeypatch não é confiável dentro de @given).
    previous: dict[str, str | None] = {name: os.environ.get(name) for name in _REQUIRED}
    try:
        for name in _REQUIRED:
            if name in missing:
                # Ausente: remove ou define como vazio/whitespace.
                if absent_value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = absent_value
            else:
                # As demais obrigatórias recebem um valor válido.
                os.environ[name] = valid_value

        # Um subconjunto não-vazio de obrigatórias ausentes -> fail-fast agregado.
        with pytest.raises(MissingConfigError) as exc_info:
            load_settings()

        message = str(exc_info.value)
        # A mensagem deve nomear CADA variável ausente do subconjunto.
        for name in missing:
            assert name in message
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
