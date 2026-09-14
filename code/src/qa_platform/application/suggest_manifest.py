"""Caso de uso ``suggest_manifest``: orquestra a Fase 2 (advisory, opt-in).

Este módulo vive na camada ``application`` e orquestra o enriquecimento por LLM
da descoberta de alvo (Fase 2) **sem** conhecer a CLI nem o ``agno`` concreto.
Recebe o enricher por injeção através de um port estrutural (:class:`EnricherPort`),
lê e valida o ``Draft`` determinístico e devolve um ``AnnotatedDraft`` ou levanta
um erro tipado da aplicação (Requisitos 6.1, 6.5, 6.6).

Fronteira de camadas (import-linter, design.md "Error Handling"):

- ``application`` permanece **livre de** ``agno`` e, em runtime, **livre de**
  ``infrastructure``. O único tipo de infra referenciado é ``AnnotatedDraft``,
  usado apenas como anotação de tipo sob :data:`typing.TYPE_CHECKING` (string
  annotation via ``from __future__ import annotations``) — não há import de
  ``infrastructure`` em tempo de execução.
- Os erros da aplicação (:class:`InvalidDraftError`, :class:`EnrichmentError`,
  :class:`EnrichmentTimeoutError`) são uma hierarquia **independente** da de
  ``infrastructure.enrichment.errors``. A fronteira de camadas proíbe a CLI
  (``interface``) de importar ``infrastructure`` para capturar seus erros;
  portanto este caso de uso **converte** qualquer falha vinda do enricher em um
  erro da aplicação, preservando a mensagem. A CLI (tarefa 10) captura somente
  ``application.InvalidDraftError`` (exit 2) e ``application.EnrichmentError``
  (exit 3, inclui timeout/provider ausente) — ver design.md, seção
  "Subcomando CLI ``suggest-manifest``".

Semântica de "propaga falha/timeout" (Req 6.6): a falha do enricher **resulta
num erro visível à CLI**. Como as hierarquias de erro de ``infrastructure`` e de
``application`` são distintas (fronteira de camadas), o caso de uso re-levanta a
falha como :class:`EnrichmentError`/:class:`EnrichmentTimeoutError` da aplicação
em vez de deixar vazar o tipo de infra — a distinção de timeout é feita pelo
**nome da classe** da exceção original (as hierarquias não compartilham base).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:  # Import só em tempo de checagem de tipos — sem acoplar runtime.
    from qa_platform.infrastructure.enrichment.annotated_draft import AnnotatedDraft

__all__ = [
    "EnricherPort",
    "EnrichmentError",
    "EnrichmentTimeoutError",
    "InvalidDraftError",
    "suggest_manifest",
]

#: Chaves obrigatórias que caracterizam a estrutura de um Draft determinístico
#: produzido pelo Static_Inspector (design.md, "Static_Inspector"). A ausência de
#: qualquer uma torna o Draft inválido para enriquecimento (Req 6.5).
_REQUIRED_DRAFT_KEYS: tuple[str, ...] = (
    "target",
    "applicable_layers",
    "risk_parameters",
)


class InvalidDraftError(RuntimeError):
    """Draft ausente, ilegível ou com estrutura inesperada (Req 6.5).

    Levantado **antes** de invocar o enricher quando o Draft não pode ser lido do
    ``draft_path`` (arquivo ausente/ilegível/JSON inválido) ou quando não tem a
    estrutura de um Draft determinístico (faltam chaves obrigatórias). Nomeia a
    natureza da invalidez sem vazar stack trace nem valores de segredo. O Draft
    de entrada permanece inalterado e o enricher **não** é chamado.
    """


class EnrichmentError(RuntimeError):
    """Falha do enriquecimento por LLM, vista pela CLI como recusa (Req 6.6).

    Hierarquia da aplicação, **independente** da de ``infrastructure.enrichment.
    errors`` (fronteira de camadas). O caso de uso converte qualquer falha vinda
    do enricher — incluindo provider ausente/blank e fonte de segredo
    indisponível — nesta classe, preservando a mensagem, para que a CLI capture
    um único tipo (exit 3). Não carrega valores de segredo.
    """


class EnrichmentTimeoutError(EnrichmentError):
    """O enricher excedeu o timeout duro e foi abortado (Req 6.6).

    Subclasse de :class:`EnrichmentError`: a CLI que captura ``EnrichmentError``
    também captura o timeout (mesmo exit 3), mas o tipo específico preserva a
    natureza "estouro de tempo" para quem quiser distingui-la. Sem
    ``AnnotatedDraft`` parcial; o Draft de entrada permanece inalterado.
    """


@runtime_checkable
class EnricherPort(Protocol):
    """Port estrutural do enricher da Fase 2 (sem import de infra/``agno``).

    Contrato estrutural mínimo que o caso de uso exige do enricher, injetado pela
    composition root. Mantém ``application`` desacoplada do adapter concreto
    (``LLMEnricher``) e de ``agno``: qualquer objeto com um ``enrich(draft)`` que
    devolva um ``AnnotatedDraft`` satisfaz o port.

    ``@runtime_checkable`` permite ``isinstance(obj, EnricherPort)`` em testes
    (verifica apenas a presença do método ``enrich``).
    """

    def enrich(self, draft: dict[str, Any]) -> AnnotatedDraft:
        """Recebe o Draft determinístico e produz um ``AnnotatedDraft``.

        Args:
            draft: Draft determinístico (mapa) produzido pelo Static_Inspector.

        Returns:
            ``AnnotatedDraft`` com o Draft preservado e as sugestões marcadas.
        """
        ...


def suggest_manifest(draft_path: str, enricher: EnricherPort) -> AnnotatedDraft:
    """Orquestra a Fase 2: lê/valida o Draft e delega ao enricher (Req 6.1).

    Fluxo (design.md, "application/suggest_manifest.py"):

    1. Lê o Draft do ``draft_path``. Arquivo ausente/ilegível ou conteúdo que
       não seja um objeto JSON → :class:`InvalidDraftError`, **sem** invocar o
       enricher (Req 6.5).
    2. Valida a estrutura de um Draft determinístico (presença das chaves
       ``target``/``applicable_layers``/``risk_parameters``). Se faltar qualquer
       uma → :class:`InvalidDraftError`, **sem** invocar o enricher e preservando
       o Draft de entrada inalterado (Req 6.5).
    3. Delega a ``enricher.enrich(draft)``. Qualquer falha do enricher (incluindo
       timeout e provider ausente) é convertida num erro da aplicação e
       propagada de forma visível à CLI (Req 6.6): timeout →
       :class:`EnrichmentTimeoutError`; demais →  :class:`EnrichmentError`.

    Args:
        draft_path: caminho para o arquivo JSON do Draft determinístico.
        enricher: implementação de :class:`EnricherPort` injetada pela
            composition root (o ``application`` não conhece o adapter concreto).

    Returns:
        ``AnnotatedDraft`` com ``base_fields`` fiéis ao Draft e as sugestões
        marcadas produzidas pelo enricher.

    Raises:
        InvalidDraftError: Draft ausente/ilegível ou com estrutura inesperada;
            o enricher não é invocado e o Draft de entrada não é alterado
            (Req 6.5).
        EnrichmentTimeoutError: quando o enricher aborta por estouro de tempo
            (Req 6.6).
        EnrichmentError: para qualquer outra falha do enricher, incluindo
            provider ausente/blank e fonte de segredo indisponível (Req 6.6).
    """
    draft = _load_draft(draft_path)
    _validate_draft_structure(draft)
    return _run_enricher(enricher, draft)


def _load_draft(draft_path: str) -> dict[str, Any]:
    """Lê e desserializa o Draft do ``draft_path`` (Req 6.5).

    Import de ``json`` local ao helper (uso pontual). Nomeia a natureza da
    invalidez sem incluir stack trace nem conteúdo sensível.

    Raises:
        InvalidDraftError: arquivo ausente/ilegível, ou conteúdo que não seja um
            objeto JSON (mapa).
    """
    import json

    path = Path(draft_path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InvalidDraftError(
            f"Draft não encontrado no caminho informado: '{draft_path}'."
        ) from exc
    except OSError as exc:
        # Permissão negada, caminho é diretório, erro de I/O, etc.
        raise InvalidDraftError(
            f"Draft ilegível no caminho informado: '{draft_path}'."
        ) from exc

    try:
        parsed: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidDraftError(
            f"Draft em '{draft_path}' não é um JSON válido."
        ) from exc

    if not isinstance(parsed, dict):
        raise InvalidDraftError(
            f"Draft em '{draft_path}' não é um objeto JSON (mapa) válido."
        )
    return parsed


def _validate_draft_structure(draft: dict[str, Any]) -> None:
    """Valida a estrutura de um Draft determinístico (Req 6.5).

    Confere a presença das chaves obrigatórias
    (``target``/``applicable_layers``/``risk_parameters``). Falha → levanta
    :class:`InvalidDraftError` nomeando as chaves ausentes, **sem** invocar o
    enricher e preservando o Draft de entrada inalterado.

    Raises:
        InvalidDraftError: quando faltar ao menos uma chave obrigatória.
    """
    missing = [key for key in _REQUIRED_DRAFT_KEYS if key not in draft]
    if missing:
        nomes = ", ".join(f"'{k}'" for k in missing)
        raise InvalidDraftError(
            "Draft não corresponde à estrutura de um Draft determinístico; "
            f"chave(s) obrigatória(s) ausente(s): {nomes}."
        )


def _run_enricher(enricher: EnricherPort, draft: dict[str, Any]) -> AnnotatedDraft:
    """Invoca o enricher convertendo falhas em erros da aplicação (Req 6.6).

    O enricher de infraestrutura levanta erros de uma hierarquia distinta
    (``infrastructure.enrichment.errors``) que a CLL não pode capturar sem violar
    a fronteira de camadas. Aqui, qualquer exceção da chamada é convertida num
    erro da aplicação, preservando a mensagem: quando o nome da classe original
    indica estouro de tempo (``EnrichmentTimeoutError``), re-levanta como
    :class:`EnrichmentTimeoutError` da aplicação; caso contrário, como
    :class:`EnrichmentError`.

    Raises:
        EnrichmentTimeoutError: falha do enricher por estouro de tempo.
        EnrichmentError: qualquer outra falha do enricher.
    """
    try:
        return enricher.enrich(draft)
    except EnrichmentError:
        # Já é um erro da aplicação (ex.: um enricher fake em teste): propaga tal
        # qual, sem re-embrulhar.
        raise
    except Exception as exc:
        # Falha do adapter concreto (infra): converte para a hierarquia da
        # aplicação, preservando a mensagem. A distinção de timeout é feita pelo
        # NOME da classe, pois as hierarquias não compartilham base comum.
        if type(exc).__name__ == "EnrichmentTimeoutError":
            raise EnrichmentTimeoutError(str(exc)) from exc
        raise EnrichmentError(str(exc)) from exc
