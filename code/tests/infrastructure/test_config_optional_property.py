"""Teste de propriedade dos defaults de variáveis opcionais (Property 3).

# Feature: executable-environment-bootstrap, Property 3

Property 3: Defaults de variáveis opcionais.
- Com TODAS as variáveis obrigatórias definidas com valores válidos (não-vazios
  e não apenas whitespace), cada variável opcional é, aleatoriamente, ora
  ausente/vazia/whitespace, ora definida com um valor não-vazio.
- Quando a opcional está ausente, vazia ou apenas whitespace, o valor efetivo
  em ``Settings`` deve ser exatamente o default predefinido em ``_OPTIONAL``.
- Quando a opcional está definida com um valor não-vazio, o valor efetivo em
  ``Settings`` deve ser exatamente esse valor fornecido.

Mapeamento env -> atributo: ``LOG_LEVEL`` -> ``log_level`` e
``ENVIRONMENT`` -> ``environment``.

Validates: Requirements 7.4
"""

from __future__ import annotations

import os

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.infrastructure.config import _OPTIONAL, load_settings

# Valores de variável de ambiente não podem conter o caractere nulo (o SO
# rejeita ``os.environ[name] = "\x00"`` com ValueError) nem surrogates isolados
# (categoria Unicode "Cs", U+D800–U+DFFF, que quebram a codificação UTF-8 do
# ambiente no Linux com ``UnicodeEncodeError``). Restringimos o alfabeto ao
# espaço de entrada válido para env vars, sem esses caracteres.
_env_text = st.text(
    alphabet=st.characters(
        blacklist_characters="\x00",
        blacklist_categories=("Cs",),
    ),
    min_size=1,
    max_size=40,
)

# Um valor "presente": não-vazio e não apenas whitespace após strip. É assim
# que o resolver decide se a variável está de fato definida.
_present_values = _env_text.filter(lambda s: s.strip() != "")

# Um valor "ausente": None (não define a env), ou string vazia/whitespace, que
# o resolver trata como ausente (aplica o default).
_absent_values = st.one_of(
    st.none(),
    st.sampled_from(["", " ", "   ", "\t", "\n", " \t \n "]),
)

# Cada opcional recebe ora um valor presente, ora um "ausente".
_optional_values = st.one_of(_present_values, _absent_values)

# Versão obrigatória sempre válida (não-vazia, não apenas whitespace).
_valid_versions = _env_text.filter(lambda s: s.strip() != "")

# Mapeia o nome da env opcional para o atributo correspondente em ``Settings``.
_ENV_TO_ATTR = {"LOG_LEVEL": "log_level", "ENVIRONMENT": "environment"}


def _set_or_pop(name: str, value: str | None) -> None:
    """Define a env com ``value`` ou a remove quando ``value is None``."""
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


@settings(max_examples=200)
@given(
    service_version=_valid_versions,
    log_level=_optional_values,
    environment=_optional_values,
)
def test_optional_defaults_applied_or_provided(
    service_version: str,
    log_level: str | None,
    environment: str | None,
) -> None:
    """Property 3: opcional ausente -> default; opcional presente -> valor.

    # Feature: executable-environment-bootstrap, Property 3
    Validates: Requirements 7.4
    """
    optional_inputs = {"LOG_LEVEL": log_level, "ENVIRONMENT": environment}
    managed = ("SERVICE_VERSION", *optional_inputs)

    # Gerencia os.environ manualmente com try/finally (Hypothesis reexecuta o
    # corpo muitas vezes; monkeypatch não é confiável dentro de @given).
    had_previous = {name: name in os.environ for name in managed}
    previous = {name: os.environ.get(name) for name in managed}
    try:
        # Todas as obrigatórias válidas.
        os.environ["SERVICE_VERSION"] = service_version
        # Opcionais ora ausentes, ora presentes.
        for name, value in optional_inputs.items():
            _set_or_pop(name, value)

        settings_obj = load_settings()

        for env_name, provided in optional_inputs.items():
            attr = _ENV_TO_ATTR[env_name]
            effective = getattr(settings_obj, attr)
            if provided is not None and provided.strip() != "":
                # Presente: o valor efetivo é exatamente o fornecido.
                assert effective == provided
            else:
                # Ausente/vazia/whitespace: aplica o default predefinido.
                assert effective == _OPTIONAL[env_name]

        # A obrigatória flui íntegra (sanidade do cenário).
        assert settings_obj.service_version == service_version
    finally:
        for name in managed:
            if had_previous[name]:
                os.environ[name] = previous[name]  # type: ignore[assignment]
            else:
                os.environ.pop(name, None)
