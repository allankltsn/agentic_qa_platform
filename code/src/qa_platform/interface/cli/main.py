"""Ponto de entrada CLI fino da QA Platform.

Adapter de entrada mínimo, sem regra de negócio: apenas parseia um subcomando e
delega. Segue a skill ``agno-project-architecture-solid`` — o CLI não contém
lógica de QA, só formata a saída e escolhe como subir o serviço.

Subcomandos:

- ``serve``: sobe o QA_Platform_Service localmente via ``uvicorn`` (Requisito
  6.2). O app ASGI é referenciado pela import string
  ``qa_platform.interface.api.main:app`` e importado tardiamente por dentro do
  ramo ``serve``, mantendo o comando ``health`` funcional mesmo que a montagem
  completa do app (composition_root) ainda não esteja disponível. Host e porta
  são configuráveis por variável de ambiente (``HOST``/``PORT``) com defaults.
- ``health`` (default): resolve a configuração via ``load_settings`` e produz o
  ``HealthStatus`` pelo caso de uso ``GetHealthStatus``, imprimindo o status em
  JSON e retornando exit code ``0`` (Requisito 6.2). Não precisa do app completo,
  reduzindo o acoplamento com o composition_root.
"""

from __future__ import annotations

import json
import os
import sys

from qa_platform.application.get_health_status import GetHealthStatus
from qa_platform.infrastructure.config import load_settings
from qa_platform.infrastructure.secrets.resolver import SecretResolver

# App ASGI servido localmente pelo uvicorn e na Lambda pelo Mangum. Importado
# como string para o ramo ``serve`` carregar a app tardiamente (evita falha de
# import na montagem completa quando só se quer o comando ``health``).
_APP_IMPORT_STRING = "qa_platform.interface.api.main:app"

_HOST_ENV = "HOST"
_PORT_ENV = "PORT"
# Bind em todas as interfaces é o default esperado para o servidor rodando
# dentro de um container/ambiente gerenciado, onde o isolamento de rede é
# imposto pela plataforma (não pelo processo). Bandit sinaliza B104 — falso
# positivo neste contexto, suprimido pontualmente.
_DEFAULT_HOST = "0.0.0.0"  # nosec B104
_DEFAULT_PORT = 8000


def _serve() -> int:
    """Sobe o serviço localmente via uvicorn (host/porta configuráveis por env)."""
    import uvicorn  # import tardio: só é necessário para ``serve``

    host = os.environ.get(_HOST_ENV) or _DEFAULT_HOST
    port_raw = os.environ.get(_PORT_ENV)
    port = int(port_raw) if port_raw and port_raw.strip() else _DEFAULT_PORT
    uvicorn.run(_APP_IMPORT_STRING, host=host, port=port)
    return 0


def _health() -> int:
    """Imprime o health status em JSON e retorna exit code 0 (Requisito 6.2)."""
    settings = load_settings(SecretResolver())
    status = GetHealthStatus(service_version=settings.service_version).execute()
    print(
        json.dumps(
            {"status": status.status, "version": status.version},
            ensure_ascii=False,
        )
    )
    return 0


def _suggest_manifest(argv: list[str]) -> int:
    """Enriquece um Draft (Fase 2, opt-in) e imprime o AnnotatedDraft em JSON.

    Adapter fino: parseia o caminho do Draft, monta o enricher via composition
    root e delega ao caso de uso ``suggest_manifest``. Não contém regra de
    negócio nem importa ``agno``/``infrastructure`` diretamente — o
    ``LLMEnricher`` é alcançado apenas por ``composition_root.build_enricher()``
    (contrato ``agno-confinado``).

    Os imports do caso de uso e do builder são **tardios** (dentro da função)
    para manter o comando ``health`` funcional sem exigir a montagem completa e
    para não puxar a cadeia do enricher quando o subcomando não é usado.

    Exit codes (design.md, "Subcomando CLI ``suggest-manifest``"):

    - ``0``: sucesso — imprime ``annotated.to_json()`` no stdout (Req 6.4).
    - ``2``: :class:`InvalidDraftError` (inclui Draft ausente) — erro em JSON no
      stderr, sem stack trace (Req 6.5).
    - ``3``: :class:`EnrichmentError` (inclui timeout/provider ausente/blank via
      ``EnrichmentTimeoutError``, subclasse) — erro em JSON no stderr, sem stack
      trace (Req 6.6, 9.2).

    Todo erro é emitido como ``{"error": str(exc)}`` no stderr, nunca stack trace.
    """
    # Import tardio: mantém ``health`` leve e a CLI sem importar ``agno`` direto.
    from qa_platform.application.suggest_manifest import (
        EnrichmentError,
        InvalidDraftError,
        suggest_manifest,
    )
    from qa_platform.composition_root import build_enricher

    if not argv or not argv[0].strip():
        # Draft ausente: alinhado a InvalidDraftError como "Draft ausente" (exit 2).
        print(
            json.dumps(
                {"error": "caminho do Draft ausente"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    draft_path = argv[0]
    try:
        annotated = suggest_manifest(draft_path, build_enricher())
    except InvalidDraftError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except EnrichmentError as exc:
        # Cobre também EnrichmentTimeoutError (subclasse) e provider ausente/blank.
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3

    print(annotated.to_json())
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parseia o subcomando e delega. Retorna o exit code (0 em caso de sucesso)."""
    argv = argv if argv is not None else sys.argv[1:]
    command = argv[0] if argv else "health"
    if command == "serve":
        return _serve()
    if command == "health":
        return _health()
    if command == "suggest-manifest":
        return _suggest_manifest(argv[1:])
    print(
        json.dumps(
            {
                "error": f"comando desconhecido: {command!r}",
                "usage": "serve | health | suggest-manifest",
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
