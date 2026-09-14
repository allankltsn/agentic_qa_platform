"""Testes por exemplo/edge do caso de uso ``suggest_manifest`` (tarefa 9.2).

Cobre a validação do Draft e a propagação de falha do enricher, sem tocar em
LLM/AWS reais — o enricher é injetado por um fake que satisfaz
:class:`EnricherPort` estruturalmente (a aplicação não conhece o adapter
concreto). Requisitos validados:

- Req 6.1: Draft válido → o enricher recebe o Draft determinístico e produz um
  ``AnnotatedDraft`` (o fake é invocado exatamente uma vez com o Draft).
- Req 6.5: Draft ausente/ilegível/estrutura inesperada → :class:`InvalidDraftError`
  **sem** invocar o enricher; a mensagem indica a natureza da invalidez; o
  arquivo de Draft de entrada permanece intacto.
- Req 6.6: enricher que levanta / estoura timeout → erro propagado; o arquivo de
  Draft de entrada permanece intacto.

Verifica também que :class:`EnricherPort` é satisfeito estruturalmente tanto por
um fake de teste quanto pelo ``LLMEnricher`` concreto (checagem estrutural via
``Protocol`` ``runtime_checkable``, sem instanciar/rodar o adapter).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from qa_platform.application.suggest_manifest import (
    EnricherPort,
    EnrichmentError,
    EnrichmentTimeoutError,
    InvalidDraftError,
    suggest_manifest,
)
from qa_platform.infrastructure.enrichment.annotated_draft import AnnotatedDraft

# ---------------------------------------------------------------------------- #
# Fakes de teste — satisfazem EnricherPort estruturalmente (sem agno/AWS).      #
# ---------------------------------------------------------------------------- #


class _SpyEnricher:
    """Fake que registra as chamadas a ``enrich`` e devolve um ``AnnotatedDraft``.

    Usado tanto para o caminho feliz (Req 6.1) quanto como espião para provar que
    o enricher **não** é invocado quando o Draft é inválido (Req 6.5).
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def enrich(self, draft: dict[str, Any]) -> AnnotatedDraft:
        self.calls.append(draft)
        return AnnotatedDraft(base_fields=dict(draft), suggestions=[])


class _RaisingEnricher:
    """Fake que levanta uma exceção arbitrária na invocação (Req 6.6)."""

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


# ---------------------------------------------------------------------------- #
# Req 6.1 — caminho feliz: enricher recebe o Draft e produz AnnotatedDraft.     #
# ---------------------------------------------------------------------------- #


def test_draft_valido_invoca_enricher_uma_vez_e_retorna_annotated_draft(
    tmp_path: Path,
) -> None:
    """Draft válido → enricher invocado exatamente uma vez com o Draft (Req 6.1)."""
    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    enricher = _SpyEnricher()

    result = suggest_manifest(str(draft_path), enricher)

    assert isinstance(result, AnnotatedDraft)
    assert len(enricher.calls) == 1
    # O enricher recebe o Draft determinístico exatamente como desserializado.
    assert enricher.calls[0] == _VALID_DRAFT
    assert result.base_fields == _VALID_DRAFT


# ---------------------------------------------------------------------------- #
# Req 6.5 — Draft ausente/ilegível/estrutura inesperada → InvalidDraftError.    #
# ---------------------------------------------------------------------------- #


def test_draft_ausente_levanta_invalid_draft_sem_invocar_enricher(
    tmp_path: Path,
) -> None:
    """Arquivo ausente → ``InvalidDraftError``; enricher NÃO invocado (Req 6.5)."""
    missing = tmp_path / "nao-existe.json"
    enricher = _SpyEnricher()

    with pytest.raises(InvalidDraftError) as exc_info:
        suggest_manifest(str(missing), enricher)

    # Mensagem indica a natureza da invalidez, nomeando o caminho.
    assert str(missing) in str(exc_info.value)
    # Enricher jamais invocado.
    assert enricher.calls == []
    # Nenhum arquivo foi criado como efeito colateral.
    assert not missing.exists()


def test_draft_ilegivel_conteudo_malformado_levanta_invalid_draft(
    tmp_path: Path,
) -> None:
    """Conteúdo não-JSON → ``InvalidDraftError``; enricher NÃO invocado (Req 6.5)."""
    draft_path = tmp_path / "draft.json"
    malformed = "{ isto não é json válido "
    draft_path.write_text(malformed, encoding="utf-8")
    original_bytes = draft_path.read_bytes()
    enricher = _SpyEnricher()

    with pytest.raises(InvalidDraftError):
        suggest_manifest(str(draft_path), enricher)

    assert enricher.calls == []
    # Arquivo de entrada permanece intacto byte-a-byte.
    assert draft_path.read_bytes() == original_bytes


def test_draft_json_nao_objeto_levanta_invalid_draft(tmp_path: Path) -> None:
    """JSON válido mas não-objeto (lista) → ``InvalidDraftError`` (Req 6.5)."""
    draft_path = _write_draft(tmp_path, ["não", "é", "um", "objeto"])
    original_bytes = draft_path.read_bytes()
    enricher = _SpyEnricher()

    with pytest.raises(InvalidDraftError):
        suggest_manifest(str(draft_path), enricher)

    assert enricher.calls == []
    assert draft_path.read_bytes() == original_bytes


@pytest.mark.parametrize(
    "missing_key",
    ["target", "applicable_layers", "risk_parameters"],
)
def test_draft_com_estrutura_inesperada_levanta_invalid_draft(
    tmp_path: Path, missing_key: str
) -> None:
    """Falta de chave obrigatória → ``InvalidDraftError``, enricher NÃO invocado,
    Draft intacto e a mensagem nomeia a chave ausente (Req 6.5)."""
    incomplete = {k: v for k, v in _VALID_DRAFT.items() if k != missing_key}
    draft_path = _write_draft(tmp_path, incomplete)
    original_bytes = draft_path.read_bytes()
    enricher = _SpyEnricher()

    with pytest.raises(InvalidDraftError) as exc_info:
        suggest_manifest(str(draft_path), enricher)

    # A mensagem nomeia a chave ofensora.
    assert missing_key in str(exc_info.value)
    assert enricher.calls == []
    # Bytes do Draft de entrada preservados.
    assert draft_path.read_bytes() == original_bytes


# ---------------------------------------------------------------------------- #
# Req 6.6 — enricher que levanta / estoura timeout → erro propagado.            #
# ---------------------------------------------------------------------------- #


def test_enricher_que_levanta_enrichment_error_propaga_com_draft_intacto(
    tmp_path: Path,
) -> None:
    """Enricher levanta ``EnrichmentError`` → propagado; Draft intacto (Req 6.6)."""
    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    original_bytes = draft_path.read_bytes()
    enricher = _RaisingEnricher(EnrichmentError("provider indisponível"))

    with pytest.raises(EnrichmentError):
        suggest_manifest(str(draft_path), enricher)

    assert enricher.calls == 1
    # Arquivo de Draft de entrada permanece inalterado.
    assert draft_path.read_bytes() == original_bytes


def test_enricher_que_estoura_timeout_propaga_com_draft_intacto(
    tmp_path: Path,
) -> None:
    """Enricher levanta ``EnrichmentTimeoutError`` (simula 120s) → propagado;
    Draft intacto (Req 6.6)."""
    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    original_bytes = draft_path.read_bytes()
    enricher = _RaisingEnricher(
        EnrichmentTimeoutError("enriquecimento excedeu 120s e foi abortado")
    )

    with pytest.raises(EnrichmentTimeoutError):
        suggest_manifest(str(draft_path), enricher)

    assert enricher.calls == 1
    assert draft_path.read_bytes() == original_bytes


def test_falha_de_infra_e_convertida_em_enrichment_error(tmp_path: Path) -> None:
    """Falha genérica do adapter (fora da hierarquia da aplicação) é convertida
    em ``EnrichmentError`` preservando a mensagem (Req 6.6)."""
    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    enricher = _RaisingEnricher(RuntimeError("boom de infra"))

    with pytest.raises(EnrichmentError) as exc_info:
        suggest_manifest(str(draft_path), enricher)

    assert "boom de infra" in str(exc_info.value)


def test_timeout_de_infra_por_nome_de_classe_vira_timeout_da_aplicacao(
    tmp_path: Path,
) -> None:
    """Exceção de infra cujo nome de classe é ``EnrichmentTimeoutError`` (base
    distinta da hierarquia da aplicação) é re-levantada como o
    ``EnrichmentTimeoutError`` da aplicação, preservando a mensagem (Req 6.6)."""

    class InfraEnrichmentTimeoutError(RuntimeError):
        """Simula o timeout da hierarquia de infraestrutura (base distinta).

        O nome de classe coincide com o da infra real para exercitar a distinção
        de timeout feita pelo nome da classe no caso de uso.
        """

    # Renomeia para casar com o discriminador por nome de classe do use case.
    InfraEnrichmentTimeoutError.__name__ = "EnrichmentTimeoutError"

    draft_path = _write_draft(tmp_path, _VALID_DRAFT)
    enricher = _RaisingEnricher(InfraEnrichmentTimeoutError("estouro de 120s"))

    # O use case converte para o EnrichmentTimeoutError da APLICAÇÃO (importado
    # no topo), não para a classe local de infra.
    with pytest.raises(EnrichmentTimeoutError) as exc_info:
        suggest_manifest(str(draft_path), enricher)

    assert "estouro de 120s" in str(exc_info.value)


# ---------------------------------------------------------------------------- #
# EnricherPort satisfeito estruturalmente pelo fake e pelo LLMEnricher.         #
# ---------------------------------------------------------------------------- #


def test_enricher_port_satisfeito_pelo_fake_de_teste() -> None:
    """Um fake de teste satisfaz ``EnricherPort`` estruturalmente."""
    assert isinstance(_SpyEnricher(), EnricherPort)
    assert isinstance(_RaisingEnricher(EnrichmentError("x")), EnricherPort)


def test_enricher_port_satisfeito_estruturalmente_pelo_llm_enricher() -> None:
    """O ``LLMEnricher`` concreto satisfaz ``EnricherPort`` (checagem estrutural,
    sem instanciar o adapter nem tocar em agno/AWS)."""
    from qa_platform.infrastructure.enrichment.llm_enricher import LLMEnricher

    # O Protocol runtime_checkable verifica a presença do método ``enrich``; a
    # classe expõe ``enrich`` com a assinatura esperada, satisfazendo o port.
    assert hasattr(LLMEnricher, "enrich")
    assert callable(LLMEnricher.enrich)
