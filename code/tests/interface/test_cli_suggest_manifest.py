"""Testes por exemplo/edge do subcomando CLI ``suggest-manifest`` (tarefa 10.3).

Exercita o adapter fino ``qa_platform.interface.cli.main`` para o subcomando
``suggest-manifest``, sem tocar em LLM/AWS reais: o enricher é injetado por
monkeypatch de ``qa_platform.composition_root.build_enricher`` (a CLI faz import
tardio de lá), devolvendo um fake que satisfaz ``EnricherPort`` estruturalmente.

Requisitos validados:

- Req 6.1, 6.4: ``main(["suggest-manifest", draft])`` com enricher mock imprime
  o ``AnnotatedDraft`` (via ``to_json()``) no stdout e retorna exit ``0``.
- Req 6.5: enricher/uso que levanta ``InvalidDraftError`` (ou Draft ausente/
  estrutura inválida) → exit ``2``, erro em JSON no stderr, arquivo do Draft
  intacto.
- Req 6.6: enricher que levanta ``EnrichmentError``/``EnrichmentTimeoutError`` →
  exit ``3``, erro em JSON no stderr, Draft intacto.
- Req 6.2, 6.3: o caminho padrão (Fase 1) NÃO invoca o enricher e consome zero
  tokens — ``build_enricher`` não é chamado ao rodar ``main(["health"])``.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from qa_platform.application.suggest_manifest import (
    EnrichmentError,
    EnrichmentTimeoutError,
)
from qa_platform.infrastructure.enrichment.annotated_draft import (
    AnnotatedDraft,
    Suggestion,
)
from qa_platform.interface.cli.main import main

# ---------------------------------------------------------------------------- #
# Fakes de enricher — satisfazem EnricherPort estruturalmente (sem agno/AWS).   #
# ---------------------------------------------------------------------------- #


class _StubEnricher:
    """Enricher fake que devolve um ``AnnotatedDraft`` conhecido (Req 6.1, 6.4)."""

    def __init__(self, annotated: AnnotatedDraft) -> None:
        self._annotated = annotated
        self.calls: list[dict[str, Any]] = []

    def enrich(self, draft: dict[str, Any]) -> AnnotatedDraft:
        self.calls.append(draft)
        return self._annotated


class _RaisingEnricher:
    """Enricher fake que levanta uma exceção arbitrária ao ser invocado."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls = 0

    def enrich(self, draft: dict[str, Any]) -> AnnotatedDraft:
        self.calls += 1
        raise self._exc


# Um Draft determinístico mínimo, com as chaves obrigatórias esperadas.
_VALID_DRAFT: dict[str, Any] = {
    "target": {"ref": "repo@abc123", "version": "1.0.0"},
    "applicable_layers": ["contract", "behavior"],
    "risk_parameters": {"contract": {"weight": 1.0}},
}


def _write_draft(tmp_path: Path, payload: object) -> Path:
    """Escreve ``payload`` como JSON num arquivo de Draft temporário."""
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(json.dumps(payload), encoding="utf-8")
    return draft_path


def _patch_build_enricher(
    monkeypatch: pytest.MonkeyPatch, enricher: object
) -> list[int]:
    """Faz monkeypatch de ``composition_root.build_enricher`` para devolver
    ``enricher``, retornando um contador (lista) das invocações do builder.

    A CLI importa ``build_enricher`` tardiamente de ``qa_platform.composition_root``;
    por isso o patch é aplicado no módulo de origem, não no módulo da CLI.
    """
    from qa_platform import composition_root

    call_count: list[int] = []

    def _fake_build_enricher() -> object:
        call_count.append(1)
        return enricher

    monkeypatch.setattr(composition_root, "build_enricher", _fake_build_enricher)
    return call_count


# ---------------------------------------------------------------------------- #
# Req 6.1, 6.4 — caminho feliz: imprime AnnotatedDraft e retorna exit 0.        #
# ---------------------------------------------------------------------------- #


def test_suggest_manifest_feliz_imprime_annotated_draft_e_retorna_0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``main(["suggest-manifest", draft])`` com enricher mock imprime o
    ``AnnotatedDraft`` (via ``to_json()``) no stdout e retorna ``0`` (Req 6.1, 6.4)."""
    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    annotated = AnnotatedDraft(
        base_fields=dict(_VALID_DRAFT),
        suggestions=[
            Suggestion(
                field="expected_domain",
                value="finanças",
                origin="sugestão",
            )
        ],
    )
    enricher = _StubEnricher(annotated)
    build_calls = _patch_build_enricher(monkeypatch, enricher)

    exit_code = main(["suggest-manifest", str(draft_path)])

    assert exit_code == 0
    # O builder foi acionado exatamente uma vez e o enricher recebeu o Draft.
    assert len(build_calls) == 1
    assert enricher.calls == [_VALID_DRAFT]
    # O stdout contém exatamente a serialização determinística do AnnotatedDraft.
    out = capsys.readouterr().out
    assert json.loads(out) == json.loads(annotated.to_json())


# ---------------------------------------------------------------------------- #
# Req 6.5 — InvalidDraftError / Draft ausente / estrutura inválida → exit 2.    #
# ---------------------------------------------------------------------------- #


def test_suggest_manifest_draft_ausente_no_disco_retorna_2_sem_invocar_enricher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Path aponta para um Draft inexistente → o caso de uso levanta
    ``InvalidDraftError`` (Draft ausente) antes de invocar o enricher; a CLI
    retorna exit ``2`` com erro em JSON no stderr e nenhum arquivo é criado como
    efeito colateral (Req 6.5)."""
    missing = tmp_path / "nao-existe.json"
    enricher = _RaisingEnricher(RuntimeError("nunca deveria ser chamado"))
    _patch_build_enricher(monkeypatch, enricher)

    exit_code = main(["suggest-manifest", str(missing)])

    assert exit_code == 2
    err = json.loads(capsys.readouterr().err)
    assert "error" in err
    # A mensagem nomeia o caminho ausente (natureza da invalidez).
    assert str(missing) in err["error"]
    # O enricher jamais foi invocado e nenhum arquivo foi criado.
    assert enricher.calls == 0
    assert not missing.exists()


def test_suggest_manifest_estrutura_invalida_real_retorna_2_com_draft_intacto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Draft com estrutura inválida real (falta chave obrigatória) → o caso de uso
    levanta ``InvalidDraftError`` sem invocar o enricher; a CLI retorna exit ``2``
    com erro em JSON no stderr e o arquivo do Draft permanece intacto (Req 6.5)."""
    incomplete = {k: v for k, v in _VALID_DRAFT.items() if k != "risk_parameters"}
    draft_path = _write_draft(tmp_path, incomplete)
    original_bytes = draft_path.read_bytes()
    enricher = _RaisingEnricher(RuntimeError("nunca deveria ser chamado"))
    _patch_build_enricher(monkeypatch, enricher)

    exit_code = main(["suggest-manifest", str(draft_path)])

    assert exit_code == 2
    err = json.loads(capsys.readouterr().err)
    # A mensagem nomeia a chave ausente (natureza da invalidez).
    assert "risk_parameters" in err["error"]
    # O enricher jamais foi invocado (Draft inválido antes da delegação).
    assert enricher.calls == 0
    assert draft_path.read_bytes() == original_bytes


# ---------------------------------------------------------------------------- #
# Req 6.6 — EnrichmentError / EnrichmentTimeoutError → exit 3.                  #
# ---------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "exc",
    [
        EnrichmentError("provider indisponível"),
        EnrichmentTimeoutError("enriquecimento excedeu 120s e foi abortado"),
    ],
    ids=["enrichment-error", "enrichment-timeout"],
)
def test_suggest_manifest_falha_do_enricher_retorna_3_com_draft_intacto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exc: EnrichmentError,
) -> None:
    """Enricher que levanta ``EnrichmentError`` ou ``EnrichmentTimeoutError``
    (estouro) → exit ``3``, erro em JSON no stderr e Draft intacto (Req 6.6)."""
    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    original_bytes = draft_path.read_bytes()
    enricher = _RaisingEnricher(exc)
    _patch_build_enricher(monkeypatch, enricher)

    exit_code = main(["suggest-manifest", str(draft_path)])

    assert exit_code == 3
    err = json.loads(capsys.readouterr().err)
    assert str(exc) in err["error"]
    assert enricher.calls == 1
    # O arquivo do Draft de entrada permanece intacto.
    assert draft_path.read_bytes() == original_bytes


# ---------------------------------------------------------------------------- #
# Req 6.5 — Draft ausente (arg de path ausente) → exit 2.                       #
# ---------------------------------------------------------------------------- #


def test_suggest_manifest_sem_path_retorna_2_sem_invocar_builder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``main(["suggest-manifest"])`` sem o path do Draft → exit ``2`` com erro em
    JSON no stderr; o builder do enricher NÃO é acionado (Req 6.5)."""
    enricher = _RaisingEnricher(RuntimeError("nunca deveria ser chamado"))
    build_calls = _patch_build_enricher(monkeypatch, enricher)

    exit_code = main(["suggest-manifest"])

    assert exit_code == 2
    err = json.loads(capsys.readouterr().err)
    assert "error" in err
    # Path ausente é resolvido antes de montar o enricher.
    assert build_calls == []
    assert enricher.calls == 0


# ---------------------------------------------------------------------------- #
# Req 6.2, 6.3 — caminho padrão (Fase 1) não invoca o enricher (zero tokens).   #
# ---------------------------------------------------------------------------- #


def test_comando_health_nao_invoca_build_enricher(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Rodar ``main(["health"])`` (comando padrão, Fase 1) NÃO chama
    ``build_enricher`` — o enricher só existe no subcomando ``suggest-manifest``,
    garantindo zero consumo de tokens fora da Fase 2 (Req 6.2, 6.3)."""
    monkeypatch.setenv("SERVICE_VERSION", "1.0.0")
    enricher = _RaisingEnricher(RuntimeError("nunca deveria ser chamado"))
    build_calls = _patch_build_enricher(monkeypatch, enricher)

    exit_code = main(["health"])

    assert exit_code == 0
    # O builder do enricher jamais é acionado no caminho da Fase 1.
    assert build_calls == []
    assert enricher.calls == 0
    # O health continua imprimindo o status normalmente.
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "ok"
