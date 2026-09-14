"""Composition root — montagem/injeção das dependências da aplicação.

Único lugar que monta o :class:`SecretResolver`, resolve a configuração
(``Settings``) com falha rápida na inicialização, configura a observabilidade
(logging JSON + tracing OTel) e monta a app FastAPI via ``create_app``. A
``MissingConfigError``/``MissingSecretError`` sobe aqui, antes de qualquer
requisição, garantindo que o serviço nunca aceite tráfego meio-configurado
(Requisitos 1.3, 1.4, 3.1, 7.1, 7.2).

Nota: o Secrets Manager é **opcional** no bootstrap — só é cabeado quando há uso
de AWS (``AWS_ENDPOINT_URL`` presente). ``build_app`` é o ponto de composição
estável consumido pelos pontos de entrada (Lambda e CLI); marcos futuros de QA
expandem este wiring (providers adicionais, políticas de observabilidade) sem
alterar essa fronteira.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi import FastAPI

from qa_platform.application.feedback_dispatcher import FeedbackSink
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.entities.run_result import RunResult
from qa_platform.infrastructure.config import load_settings
from qa_platform.infrastructure.enrichment.llm_enricher import LLMEnricher
from qa_platform.infrastructure.layers.ai_layer_stub import AILayerStub
from qa_platform.infrastructure.observability.logging import build_json_logger
from qa_platform.infrastructure.observability.tracing import configure_tracing
from qa_platform.infrastructure.orchestration.registry import LayerRegistry
from qa_platform.infrastructure.orchestration.workflow import run_orchestration
from qa_platform.infrastructure.persistence.run_store_factory import build_run_store
from qa_platform.infrastructure.secrets.aws_secrets_manager import (
    AWSSecretsManagerProvider,
)
from qa_platform.infrastructure.secrets.resolver import SecretResolver
from qa_platform.interface.api.api import create_app

if TYPE_CHECKING:
    from collections.abc import Callable


def _build_secret_resolver() -> SecretResolver:
    """Monta o ``SecretResolver`` com o pipe de fallback ``env -> Secrets Manager``.

    O Secrets Manager é opcional no bootstrap: liga o adapter apenas quando há
    uso de AWS (``AWS_ENDPOINT_URL`` definido). Sem ele, o resolver consulta
    somente as variáveis de ambiente (Requisitos 7.1, 7.2).
    """
    provider = (
        AWSSecretsManagerProvider() if os.environ.get("AWS_ENDPOINT_URL") else None
    )
    return SecretResolver(secrets_provider=provider)


def _split_csv(raw: str) -> list[str]:
    """Divide um valor CSV de env, descartando entradas vazias/whitespace."""
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_app() -> FastAPI:
    """Resolve a configuração, configura a observabilidade e monta a app FastAPI.

    A resolução de ``Settings`` ocorre aqui (fail-fast): se uma variável
    obrigatória estiver ausente/vazia, a exceção sobe na montagem e o serviço
    não sobe (Requisitos 1.4, 7.1, 7.2). Em seguida configura o logging JSON e o
    tracing OTel (no-op quando desligado por env) e delega a ``create_app`` a
    construção da app, com ``allowed_hosts``/``cors_origins`` vindos de env
    (defaults sensatos) (Requisitos 1.3, 3.1).
    """
    settings = load_settings(_build_secret_resolver())  # fail-fast na init
    build_json_logger("qa-platform", level=settings.log_level)
    configure_tracing("qa-platform")  # no-op se desligado por env

    allowed_hosts = _split_csv(os.environ.get("ALLOWED_HOSTS", "*")) or ["*"]
    cors_origins = _split_csv(os.environ.get("CORS_ALLOWED_ORIGINS", ""))

    return create_app(
        service_version=settings.service_version,
        allowed_hosts=allowed_hosts,
        cors_origins=cors_origins,
    )


class LoggingFeedbackSink:
    """``FeedbackSink`` default in-memory/log (Requisito 2.1).

    Destino plugável default do feedback nesta fase: guarda o último
    ``RunResult`` recebido em memória e registra a emissão no logger JSON
    estruturado, sem nenhuma integração externa real. Satisfaz o ``FeedbackSink``
    do domínio estruturalmente; integrações concretas entram em marcos futuros
    sem alterar esta fronteira.
    """

    def __init__(self) -> None:
        """Inicializa o sink sem nenhum resultado emitido."""
        self.last_result: RunResult | None = None

    def emit(self, result: RunResult) -> None:
        """Registra o ``RunResult`` recebido (in-memory/log), sem integração externa."""
        self.last_result = result


def build_orchestrator_runner(
    *,
    feedback_sink: FeedbackSink | None = None,
) -> Callable[[QATargetManifest, dict[str, object]], RunResult]:
    """Monta as dependências do orquestrador e devolve o runner que executa uma run.

    Ponto de composição do núcleo de orquestração (ADR-001), análogo a ``build_app``
    para a app FastAPI e sem alterá-lo. Resolve a configuração via ``SecretResolver``
    com falha rápida, configura a observabilidade (logging JSON + tracing OTel), monta
    o ``RunStateStore`` via ``build_run_store`` (seleção do adapter por env, consumido
    apenas pelo port), o ``LayerRegistry`` com a ``AILayerStub`` registrada e um
    ``FeedbackSink`` default in-memory/log (Requisitos 1.1, 4.4, 6.3, 12.5).

    Como ``build_orchestrator`` monta o ``Workflow`` da Agno por execução (o manifesto e
    o ``RunId`` só existem em tempo de run), este composition root devolve um **runner**:
    uma função ``(manifest, raw_manifest) -> RunResult`` que aciona ``run_orchestration``
    com as dependências já cabeadas. O ``RunStateStore`` (adapter selecionado por env via
    ``build_run_store``, default in-memory) persiste entre chamadas do runner e é a fonte
    de verdade do histórico (sem ``db=`` da Agno).

    Reusa integralmente os helpers do bootstrap (``_build_secret_resolver``,
    ``load_settings``, ``build_json_logger``, ``configure_tracing``); a ``AILayerStub``
    resolve o provider de modelo por env via o mesmo ``SecretResolver`` (fail-fast quando
    ausente) (Requisitos 12.5, 12.6).

    Args:
        feedback_sink: destino plugável opcional do feedback; por padrão usa o
            ``LoggingFeedbackSink`` in-memory/log.

    Returns:
        Um runner ``(manifest, raw_manifest) -> RunResult`` com store/registry/sink já
        cabeados.
    """
    resolver = _build_secret_resolver()
    settings = load_settings(resolver)  # fail-fast na init (Req 7.1, 7.2)
    build_json_logger("qa-platform", level=settings.log_level)
    configure_tracing("qa-platform")  # no-op se desligado por env

    # A seleção do adapter (durável vs in-memory) é resolvida por env na factory;
    # aqui o store é consumido exclusivamente pelo port RunStateStore (Req 4.4).
    store = build_run_store()
    # A AILayerStub resolve MODEL_PROVIDER por env via o mesmo SecretResolver
    # (fail-fast se ausente) — nenhum provider é fixado no código (Req 12.5, 12.6).
    registry = LayerRegistry([AILayerStub(resolver=resolver)])
    sink: FeedbackSink = feedback_sink or LoggingFeedbackSink()

    def _run(manifest: QATargetManifest, raw_manifest: dict[str, object]) -> RunResult:
        """Executa uma run do orquestrador com as dependências cabeadas."""
        return run_orchestration(
            manifest=manifest,
            raw_manifest=raw_manifest,
            store=store,
            registry=registry,
            feedback_sink=sink,
        )

    return _run


def build_enricher() -> LLMEnricher:
    """Monta o ``LLMEnricher`` (adapter Agno) da Fase 2, advisory e opt-in.

    Ponto de composição do enriquecimento por LLM (ADR-004), análogo a
    ``build_app`` e ``build_orchestrator_runner`` e sem alterá-los. Reusa o helper
    ``_build_secret_resolver`` para montar o ``SecretResolver`` com o pipe de
    fallback ``env -> Secrets Manager`` e o injeta no ``LLMEnricher`` (Requisitos
    6.1, 9.1).

    Este é o **único** ponto que "cola" a interface (CLI ``suggest-manifest``) ao
    adapter Agno ``LLMEnricher``, preservando a fronteira do import-linter
    (``agno-confinado`` com ``allow_indirect_imports=True``): a CLI alcança o
    ``agno`` apenas indiretamente, por meio deste composition root. Diferente dos
    demais builders, ``build_enricher`` **não** resolve ``Settings`` nem configura
    observabilidade: a resolução do ``MODEL_PROVIDER`` (fail-fast) acontece dentro
    do próprio enricher, na chamada de ``enrich`` e antes de qualquer uso de
    ``agno`` (Req 9.1).

    Returns:
        Um ``LLMEnricher`` com o ``SecretResolver`` já cabeado, pronto para ser
        injetado no caso de uso ``suggest_manifest``.
    """
    return LLMEnricher(_build_secret_resolver())
