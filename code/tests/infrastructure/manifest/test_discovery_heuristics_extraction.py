"""Teste de propriedade da extração de tools/prompts/RAG com origem (Property 4).

Property 4 — Extração de tools/prompts/RAG com origem: para toda visão de
repositório sintética que declara um conjunto de N tools (resp. prompts, indícios
de RAG) identificáveis por heurística, o bloco ``discovery`` contém exatamente
esses N itens, cada um com ``identifier`` e ``source`` corretos; quando N = 0, a
coleção correspondente é vazia e nenhuma exceção é levantada.

Hypothesis injeta N≥0 declarações de tools em arquivos sintéticos com identidade
conhecida e afirma que ``DiscoveryInfo.tools`` reflete exatamente o conjunto
injetado (identificador + caminho de origem), incluindo o caso vazio.

# Feature: hybrid-target-discovery, Property 4
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.value_objects.discovery import DetectedItem
from qa_platform.infrastructure.manifest.discovery_heuristics import detect
from qa_platform.infrastructure.manifest.repo_reader import RepoView

# Identificadores Python válidos e distinguíveis (nome de função decorada).
_tool_names = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=12,
)

# Nome de arquivo-fonte relativo (POSIX), não-vazio.
_source_names = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=10,
).map(lambda stem: f"{stem}.py")


def _tool_declaration(name: str) -> str:
    """Trecho que a heurística ``@tool`` reconhece, com nome ``name``."""
    return f"@tool\ndef {name}():\n    return None\n"


# Feature: hybrid-target-discovery, Property 4
# Property 4: Extração de tools/prompts/RAG com origem.
# Validates: Requirements 4.1, 4.2, 4.3, 4.4
@settings(max_examples=100)
@given(
    declarations=st.lists(
        st.tuples(_source_names, _tool_names),
        min_size=0,
        max_size=8,
        # (source, identifier) único: cada declaração é um DetectedItem distinto.
        unique=True,
    )
)
def test_extracao_de_tools_com_origem(
    declarations: list[tuple[str, str]],
) -> None:
    """As tools extraídas casam exatamente com o conjunto injetado (Req 4.1, 4.4)."""
    # Agrupa múltiplas tools por arquivo, preservando a origem de cada uma.
    by_source: dict[str, list[str]] = {}
    for source, identifier in declarations:
        by_source.setdefault(source, []).append(identifier)

    files = tuple(
        (source, "".join(_tool_declaration(name) for name in names))
        for source, names in by_source.items()
    )
    repo_view = RepoView(root="/synthetic", files=files)

    info = detect(repo_view)

    expected = {
        DetectedItem(identifier=identifier, source=source)
        for source, identifier in declarations
    }
    assert set(info.tools) == expected

    # Caso vazio (N = 0): coleção vazia, sem exceção (Req 4.4).
    if not declarations:
        assert info.tools == ()

    # Ordenação total e estável por (source, identifier) — Req 2.4.
    ordered = sorted(expected, key=lambda item: (item.source, item.identifier))
    assert list(info.tools) == ordered
