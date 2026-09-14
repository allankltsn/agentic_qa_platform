"""Teste de propriedade — erro em referência de alvo ruim (Property 10).

Property 10 — Erro em referência de alvo ruim: para toda referência de alvo
ausente (``None``), vazia (``""``) ou composta apenas de caracteres brancos
(espaço, tab, quebra de linha etc.), o ``Static_Inspector`` levanta
``TargetResolutionError`` **antes** de qualquer leitura, sem produzir Draft.
A indicação de erro **nomeia** a referência afetada — para refs não-``None``, o
valor da referência aparece na mensagem (Requisito 1.4).

Complementa a checagem por exemplo já existente em ``test_target_discovery.py``
(``None``/``""``/``"   "`` parametrizados) com quantificação universal sobre
strings só-espaços geradas via Hypothesis.

# Feature: hybrid-target-discovery, Property 10
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.exceptions import TargetResolutionError
from qa_platform.infrastructure.manifest.target_discovery import discover_target

# Conjunto de caracteres brancos reconhecidos por ``str.strip()``: espaço, tab,
# quebra de linha, retorno de carro, form feed, vertical tab. Uma string
# composta apenas destes é irresolvível na Fase 1 determinística.
_WHITESPACE_CHARS = " \t\n\r\f\v"

# Strings **não-vazias** compostas somente de caracteres brancos.
_whitespace_only = st.text(alphabet=_WHITESPACE_CHARS, min_size=1, max_size=20)

# Referências ruidosas: ``None``, ``""`` e strings só-espaços não-vazias.
_bad_refs = st.one_of(
    st.none(),
    st.just(""),
    _whitespace_only,
)


# Feature: hybrid-target-discovery, Property 10
# Property 10: Erro em referência de alvo ruim.
# Validates: Requirements 1.4
@settings(max_examples=100)
@given(target_ref=_bad_refs)
def test_referencia_ruim_levanta_erro_nomeando_a_ref_sem_draft(
    target_ref: str | None,
) -> None:
    """Ref ausente/vazia/só-espaços → ``TargetResolutionError`` nomeando a ref.

    Nenhum Draft é retornado: o ``pytest.raises`` garante que a chamada não
    devolve valor algum (o ``raise`` ocorre em ``_resolve_ref``, antes de
    qualquer leitura de repositório).
    """
    with pytest.raises(TargetResolutionError) as exc_info:
        discover_target(target_ref)

    message = str(exc_info.value)

    # A mensagem sempre nomeia a referência afetada (Req 1.4): o ``Static_Inspector``
    # inclui a representação (``repr``) da referência recebida, que preserva o seu
    # conteúdo literal de forma inequívoca — inclusive para ``None``, ``""`` e
    # caracteres de controle (ex.: ``'\r'`` vira ``"'\\r'"``). Verificar a presença
    # do ``repr`` cobre uniformemente todos os casos ruins gerados.
    assert repr(target_ref) in message
