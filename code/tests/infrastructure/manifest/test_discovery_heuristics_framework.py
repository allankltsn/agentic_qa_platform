"""Teste de propriedade da detecção de framework por heurística (Property 3).

Property 3 — Detecção de framework por heurística: para toda visão de repositório
sintética, se contém apenas indícios de Agno → ``framework == agno``; se apenas de
LangGraph → ``framework == langgraph``; se de ambos → ``ambiguous == True`` e
``frameworks_detected`` contém os dois; se de nenhum → ``framework == not_detected``
e a inspeção conclui sem erro.

Hypothesis gera repos sintéticos em memória cobrindo os quatro casos
{só Agno, só LangGraph, ambos, nenhum}, montando uma ``RepoView`` diretamente
(sem tocar o filesystem) e afirmando o contrato de detecção.

# Feature: hybrid-target-discovery, Property 3
"""

from __future__ import annotations

from enum import Enum

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.domain.value_objects.discovery import Framework
from qa_platform.infrastructure.manifest.discovery_heuristics import detect
from qa_platform.infrastructure.manifest.repo_reader import RepoView


class _Case(Enum):
    """Os quatro casos de detecção gerados pela propriedade."""

    ONLY_AGNO = "only_agno"
    ONLY_LANGGRAPH = "only_langgraph"
    BOTH = "both"
    NONE = "none"


# Trechos que ativam (ou não) cada heurística de import de framework.
_AGNO_SNIPPET = "from agno.agent import Agent\n"
_LANGGRAPH_SNIPPET = "import langgraph\n"
# Conteúdo neutro que NÃO deve casar com nenhuma heurística de framework: menciona
# os nomes apenas como substring/comentário, jamais como import de topo.
_NEUTRAL_SNIPPET = "# nota: nada de agno nem langgraph aqui\nx = 'agnostic'\n"

# Nome de arquivo relativo, não-vazio, sem separadores de caminho ambíguos.
_file_names = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=10,
).map(lambda stem: f"{stem}.py")


def _build_repo_view(draw: st.DrawFn, case: _Case) -> RepoView:
    """Monta uma ``RepoView`` sintética coerente com ``case``."""
    file_names = draw(st.lists(_file_names, min_size=1, max_size=4, unique=True))
    # Arquivo dedicado a cada indício exigido pelo caso, garantindo presença.
    files: list[tuple[str, str]] = []
    if case in (_Case.ONLY_AGNO, _Case.BOTH):
        files.append(("_agno_marker.py", _AGNO_SNIPPET))
    if case in (_Case.ONLY_LANGGRAPH, _Case.BOTH):
        files.append(("_lg_marker.py", _LANGGRAPH_SNIPPET))
    # Arquivos neutros adicionais não alteram a classificação.
    files.extend((name, _NEUTRAL_SNIPPET) for name in file_names)
    return RepoView(root="/synthetic", files=tuple(sorted(files)))


# Feature: hybrid-target-discovery, Property 3
# Property 3: Detecção de framework por heurística.
# Validates: Requirements 3.1, 3.2, 3.3, 3.4
@settings(max_examples=100)
@given(case=st.sampled_from(_Case), data=st.data())
def test_deteccao_de_framework_por_heuristica(case: _Case, data: st.DataObject) -> None:
    """A classificação do framework segue o caso gerado (Req 3.1–3.4)."""
    repo_view = _build_repo_view(data.draw, case)

    info = detect(repo_view)

    if case is _Case.ONLY_AGNO:
        assert info.framework == Framework.AGNO
        assert info.frameworks_detected == (Framework.AGNO,)
        assert info.ambiguous is False
    elif case is _Case.ONLY_LANGGRAPH:
        assert info.framework == Framework.LANGGRAPH
        assert info.frameworks_detected == (Framework.LANGGRAPH,)
        assert info.ambiguous is False
    elif case is _Case.BOTH:
        assert info.ambiguous is True
        assert set(info.frameworks_detected) == {
            Framework.AGNO,
            Framework.LANGGRAPH,
        }
        # frameworks_detected é ordenado alfabeticamente (agno < langgraph).
        assert info.frameworks_detected == (Framework.AGNO, Framework.LANGGRAPH)
    else:  # _Case.NONE — conclui sem erro e sem framework (Req 3.4).
        assert info.framework == Framework.NOT_DETECTED
        assert info.frameworks_detected == ()
        assert info.ambiguous is False
