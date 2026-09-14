"""Testes por exemplo/edge — interface preservada e Fase 1 sem LLM/rede.

Complementam os testes de propriedade (``test_target_discovery.py``,
``test_target_discovery_bad_ref.py``) com asserções por exemplo focadas em três
garantias da Fase 1 do ``Static_Inspector`` (ADR-004):

1. **Interface preservada** (Requisito 1.1): o import do módulo, o conteúdo de
   ``__all__``, a assinatura de ``discover_target`` e a presença das funções
   públicas (``PENDING``, ``discover_target``, ``is_pending``,
   ``has_pending_fields``) permanecem idênticos à Sprint 1.
2. **Determinismo por design — sem LLM/rede** (Requisitos 2.2, 2.3): durante uma
   chamada de ``discover_target``, nenhum framework de LLM é invocado e nenhuma
   conexão de rede (socket) é aberta.
3. **Aborta sem Draft parcial** (Requisitos 2.5, 2.6): um leitor injetado que
   tenta rede/LLM e um arquivo inacessível (``RepoReadError``) fazem a chamada
   abortar sem devolver nenhum Draft (parcial ou completo).

E também que ``discovery.fragility_note`` é não vazio num Draft bem-sucedido
(Requisito 3.5).

**Mecanismo de bloqueio de rede/LLM (nota de escolha):** ``pytest-socket`` **não**
é dependência de desenvolvimento do projeto (ver ``code/pyproject.toml``), e a
Fase 1 não deve adicionar dependência nova sem necessidade. Portanto o bloqueio
de rede usa o mecanismo mais simples já disponível: ``monkeypatch`` quebra
``socket.socket`` (qualquer tentativa de abrir socket levanta), e um "espião" de
LLM quebra o construtor ``agno.agent.Agent`` (qualquer instanciação de agente
levanta). Como a Fase 1 é determinística por design e **não importa** ``agno``
nem clientes HTTP, nenhuma dessas armadilhas dispara durante ``discover_target``
— o que prova ausência de invocação de LLM e de chamadas de rede.

# Feature: hybrid-target-discovery
"""

from __future__ import annotations

import inspect
import socket
from pathlib import Path
from typing import Any, NoReturn

import pytest

from qa_platform.domain.exceptions import TargetResolutionError
from qa_platform.infrastructure.manifest import repo_reader, target_discovery
from qa_platform.infrastructure.manifest.discovery_heuristics import FRAGILITY_NOTE
from qa_platform.infrastructure.manifest.target_discovery import (
    PENDING,
    discover_target,
    has_pending_fields,
    is_pending,
)

# --------------------------------------------------------------------------- #
# 1) Interface preservada — import, __all__ e assinaturas idênticos à Sprint 1
# --------------------------------------------------------------------------- #


def test_all_expoe_exatamente_os_simbolos_publicos_da_sprint1() -> None:
    """``__all__`` é idêntico à Sprint 1 (Req 1.1)."""
    assert target_discovery.__all__ == [
        "PENDING",
        "discover_target",
        "has_pending_fields",
        "is_pending",
    ]


def test_simbolos_publicos_existem_e_sao_do_tipo_esperado() -> None:
    """Os quatro símbolos públicos estão expostos no módulo (Req 1.1)."""
    assert PENDING == "PENDING"
    assert callable(discover_target)
    assert callable(is_pending)
    assert callable(has_pending_fields)
    # Todos os nomes de ``__all__`` resolvem para atributos reais do módulo.
    for name in target_discovery.__all__:
        assert hasattr(target_discovery, name)


def test_assinatura_de_discover_target_e_identica_a_sprint1() -> None:
    """Assinatura ``(target_ref: str | None) -> dict[str, Any]`` (Req 1.1, 1.5)."""
    signature = inspect.signature(discover_target)

    # Exatamente um parâmetro posicional chamado ``target_ref``.
    assert list(signature.parameters) == ["target_ref"]
    param = signature.parameters["target_ref"]
    assert param.annotation == "str | None"

    # Anotação de retorno preservada (``dict[str, Any]``).
    assert signature.return_annotation == "dict[str, Any]"


# --------------------------------------------------------------------------- #
# 2) Determinismo por design — nenhuma invocação de LLM e nenhuma rede
# --------------------------------------------------------------------------- #


def _forbid_socket(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Armadilha: qualquer tentativa de abrir socket falha o teste (Req 2.3)."""
    raise AssertionError(
        "Fase 1 tentou abrir um socket de rede — determinismo violado (Req 2.3)."
    )


def test_discover_target_nao_abre_socket_nem_invoca_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Durante ``discover_target`` não há rede nem invocação de LLM (Req 2.2, 2.3).

    Bloqueio de rede: ``socket.socket`` é substituído por uma armadilha que
    falha o teste se chamada. Espião de LLM: um contador registra qualquer
    tentativa de construir um ``Agent`` do Agno; a Fase 1 não importa ``agno``,
    então o contador permanece em zero.
    """
    # Arrange — artefato real mínimo para produzir um Draft.
    target = tmp_path / "agent.py"
    target.write_text("import agno\n\nAGENT_PROMPT = 'oi'\n", encoding="utf-8")

    # Bloqueio de rede: qualquer socket.socket(...) dispara a armadilha.
    monkeypatch.setattr(socket, "socket", _forbid_socket)

    # Espião de LLM: conta tentativas de instanciar um Agent do Agno. A Fase 1
    # não deve tocar o framework de LLM, então a contagem final deve ser zero.
    llm_invocations = {"count": 0}

    def _spy_agent(*_args: Any, **_kwargs: Any) -> NoReturn:
        llm_invocations["count"] += 1
        raise AssertionError(
            "Fase 1 tentou instanciar um Agent do Agno — LLM invocado (Req 2.2)."
        )

    # Instala o espião apenas se o módulo do agente estiver importável, sem
    # forçar o import de ``agno`` no caminho de produção da Fase 1.
    agno_agent = pytest.importorskip("agno.agent")
    monkeypatch.setattr(agno_agent, "Agent", _spy_agent)

    # Act — a chamada completa deve ocorrer sem disparar nenhuma armadilha.
    draft = discover_target(str(target))

    # Assert — Draft válido produzido, sem rede e sem LLM.
    assert isinstance(draft, dict)
    assert llm_invocations["count"] == 0


# --------------------------------------------------------------------------- #
# 3) Aborta sem Draft parcial — leitor que tenta rede/LLM e arquivo inacessível
# --------------------------------------------------------------------------- #


def test_leitor_que_tenta_rede_aborta_sem_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leitor injetado que tenta rede/LLM aborta sem Draft parcial (Req 2.5).

    O ``read_target`` é substituído por um fake que simula uma tentativa de
    rede/LLM levantando uma exceção. Como o colaborador falha antes de qualquer
    montagem de Draft, ``discover_target`` propaga o erro e **não** devolve valor.
    """

    def _reader_tenta_rede(_resolved_ref: str) -> NoReturn:
        # Simula um leitor indevido que tentaria abrir rede/chamar LLM: em vez de
        # de fato abrir um socket, sinaliza a violação com uma exceção. O ponto
        # do teste é que a falha do colaborador aborta sem Draft parcial.
        raise RuntimeError("leitor tentou acessar rede/LLM — proibido na Fase 1")

    monkeypatch.setattr(repo_reader, "read_target", _reader_tenta_rede)

    result: dict[str, Any] | None = None
    with pytest.raises(RuntimeError, match="rede/LLM"):
        result = discover_target("qualquer/ref")

    # Nenhum Draft (parcial ou completo) foi produzido/atribuído.
    assert result is None


def test_arquivo_inacessivel_propaga_repo_read_error_sem_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arquivo inacessível → ``RepoReadError`` sem Draft parcial (Req 2.6).

    Usa o erro do próprio colaborador (``repo_reader.RepoReadError``) para o
    cenário de arquivo inacessível: o fake de ``read_target`` levanta como o
    faria a leitura real ao encontrar conteúdo/arquivo inacessível. A chamada
    aborta sem montar Draft.
    """

    def _reader_inacessivel(resolved_ref: str) -> NoReturn:
        raise repo_reader.RepoReadError(resolved_ref, "arquivo ou conteúdo inacessível")

    monkeypatch.setattr(repo_reader, "read_target", _reader_inacessivel)

    result: dict[str, Any] | None = None
    with pytest.raises(repo_reader.RepoReadError) as exc_info:
        result = discover_target("alvo/inacessivel.py")

    # Aborta sem Draft parcial e nomeia a origem afetada (sem valores de segredo).
    assert result is None
    assert exc_info.value.source == "alvo/inacessivel.py"


def test_referencia_irresolvivel_aborta_antes_de_qualquer_leitura(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ref irresolvível levanta ``TargetResolutionError`` sem ler o repo (Req 2.5).

    Sela a garantia de "abortar sem Draft parcial" também no caminho da
    resolução: a armadilha em ``read_target`` prova que nem sequer se tenta ler
    o repositório quando a referência é irresolvível.
    """

    def _reader_nao_deve_ser_chamado(_resolved_ref: str) -> NoReturn:
        raise AssertionError("read_target não deveria ser chamado para ref inválida.")

    monkeypatch.setattr(repo_reader, "read_target", _reader_nao_deve_ser_chamado)

    with pytest.raises(TargetResolutionError):
        discover_target(None)


# --------------------------------------------------------------------------- #
# 4) fragility_note não vazio num Draft bem-sucedido (Req 3.5)
# --------------------------------------------------------------------------- #


def test_draft_bem_sucedido_tem_fragility_note_nao_vazio(tmp_path: Path) -> None:
    """Um Draft bem-sucedido carrega ``discovery.fragility_note`` não vazio (Req 3.5).

    Constrói um caso real com arquivo sintético sob ``tmp_path`` para que as
    heurísticas populem o bloco ``discovery`` com a nota de fragilidade fixa.
    """
    target = tmp_path / "agent.py"
    target.write_text(
        "from agno.agent import Agent\n\nSYSTEM_PROMPT = 'ajude o usuario'\n",
        encoding="utf-8",
    )

    draft = discover_target(str(target))

    fragility_note = draft["discovery"]["fragility_note"]
    assert isinstance(fragility_note, str)
    assert fragility_note.strip() != ""
    # A nota é a fixa definida pelas heurísticas (Req 3.5).
    assert fragility_note == FRAGILITY_NOTE
    # Draft de rascunho ainda contém campos pendentes (não é manifesto completo).
    assert has_pending_fields(draft)
    assert is_pending(draft["target"]["version"])
