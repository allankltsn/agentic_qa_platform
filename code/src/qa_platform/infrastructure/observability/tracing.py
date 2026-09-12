"""Tracing OpenTelemetry ligado/desligado por variável de ambiente.

Quando o tracing está desligado, :func:`configure_tracing` é um NO-OP total:
nenhum exporter é criado e nenhuma dependência de OTel é importada (import
tardio), de modo que não há overhead em runtime. É ligado apenas por
``TRACING_ENABLED=true`` ou pela presença de ``OTEL_EXPORTER_OTLP_ENDPOINT``
(Requisitos 1.2, 1.3).
"""

from __future__ import annotations

import os


def _tracing_enabled() -> bool:
    """Indica se o tracing deve ser ligado a partir do ambiente.

    Liga por env: ``TRACING_ENABLED=true`` OU ``OTEL_EXPORTER_OTLP_ENDPOINT``
    definido.
    """
    return os.environ.get("TRACING_ENABLED", "false").lower() == "true" or bool(
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    )


def configure_tracing(service_name: str = "qa-platform") -> bool:
    """Configura o tracing OTel se habilitado por env; caso contrário é NO-OP.

    Retorna ``True`` se ligou, ``False`` se ficou como no-op. Sem custo em
    runtime quando desligado.
    """
    if not _tracing_enabled():
        return False  # no-op: nenhum exporter, nenhum overhead
    # Import tardio: dependências de OTel só carregam quando o tracing está ligado.
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return True
