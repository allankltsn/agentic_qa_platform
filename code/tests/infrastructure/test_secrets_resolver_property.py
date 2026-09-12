"""Teste de propriedade do pipe de fallback do ``SecretResolver`` (Property 4).

# Feature: executable-environment-bootstrap, Property 4

Property 4: Pipe de fallback do ``SecretResolver``.
- A variável de ambiente sempre vence sobre o Secrets Manager quando presente
  (valor não-vazio, não apenas whitespace).
- Quando ausente/vazia na env, mas presente no provider, vence o provider.
- Quando ausente/vazia em AMBOS e o valor é obrigatório sem default, o resolver
  levanta ``MissingSecretError`` cuja mensagem contém o NOME da variável, mas
  NUNCA o valor de qualquer segredo.

Whitespace-only é tratado como ausente em ambas as fontes.

Validates: Requirements 7.1, 7.2
"""

from __future__ import annotations

import os

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.secrets.in_memory import InMemorySecretsProvider
from qa_platform.infrastructure.secrets.resolver import (
    MissingSecretError,
    SecretResolver,
)

# Nome de variável de ambiente plausível (identificador em MAIÚSCULAS).
_var_names = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_",
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() != "")

# Um valor "presente": não-vazio e não apenas whitespace após strip. Exclui o
# caractere nulo (\x00) e os surrogates isolados (categoria Unicode "Cs",
# U+D800–U+DFFF): variáveis de ambiente do SO não podem conter nenhum dos dois
# — ``os.environ[k] = "\x00"`` levanta ValueError e um surrogate isolado quebra
# a codificação UTF-8 do ambiente no Linux (``UnicodeEncodeError``). Nenhum é um
# insumo válido para exercitar o pipe do resolver.
_present_values = st.text(
    alphabet=st.characters(
        blacklist_characters="\x00",
        blacklist_categories=("Cs",),
    ),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() != "")

# Um valor "ausente": None, string vazia ou apenas whitespace.
_absent_values = st.one_of(
    st.none(),
    st.sampled_from(["", " ", "   ", "\t", "\n", " \t \n "]),
)

# Distribui um valor entre "presente" e "ausente" para env e provider.
_env_values = st.one_of(_present_values, _absent_values)
_provider_values = st.one_of(_present_values, _absent_values)


def _is_present(value: str | None) -> bool:
    """Reflete a regra do resolver: não-None e não apenas whitespace."""
    return value is not None and value.strip() != ""


@settings(max_examples=200)
@given(
    var_name=_var_names,
    env_value=_env_values,
    provider_value=_provider_values,
)
def test_fallback_pipe_env_wins_then_provider_then_error(
    var_name: str,
    env_value: str | None,
    provider_value: str | None,
) -> None:
    """Property 4: env vence; senão provider; senão erro nomeando a variável.

    # Feature: executable-environment-bootstrap, Property 4
    Validates: Requirements 7.1, 7.2
    """
    # Gerencia os.environ manualmente com try/finally (Hypothesis reexecuta o
    # corpo muitas vezes; monkeypatch não é confiável dentro de @given).
    had_previous = var_name in os.environ
    previous = os.environ.get(var_name)
    try:
        if env_value is None:
            os.environ.pop(var_name, None)
        else:
            os.environ[var_name] = env_value

        provider = InMemorySecretsProvider(
            {var_name: provider_value} if provider_value is not None else {}
        )
        resolver = SecretResolver(secrets_provider=provider)

        env_present = _is_present(env_value)
        provider_present = _is_present(provider_value)

        if env_present:
            # A env sempre vence quando presente, retornando o valor cru.
            assert resolver.resolve(var_name) == env_value
        elif provider_present:
            # Sem env válida, o provider fornece o valor.
            assert resolver.resolve(var_name) == provider_value
        else:
            # Ausente em ambas as fontes: fail-fast nomeando a variável.
            with pytest.raises(MissingSecretError) as exc_info:
                resolver.resolve(var_name)
            message = str(exc_info.value)
            # A mensagem nomeia a variável...
            assert var_name in message
            # ...e NUNCA vaza o valor de qualquer segredo (mesmo whitespace).
            for leaked in (env_value, provider_value):
                if leaked is not None and leaked.strip() != "":
                    assert leaked not in message
    finally:
        if had_previous:
            os.environ[var_name] = previous  # type: ignore[assignment]
        else:
            os.environ.pop(var_name, None)
