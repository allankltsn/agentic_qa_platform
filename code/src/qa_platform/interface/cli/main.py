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
from typing import Optional

from qa_platform.application.get_health_status import GetHealthStatus
from qa_platform.infrastructure.config import load_settings
from qa_platform.infrastructure.secrets.resolver import SecretResolver

# App ASGI servido localmente pelo uvicorn e na Lambda pelo Mangum. Importado
# como string para o ramo ``serve`` carregar a app tardiamente (evita falha de
# import na montagem completa quando só se quer o comando ``health``).
_APP_IMPORT_STRING = "qa_platform.interface.api.main:app"

_HOST_ENV = "HOST"
_PORT_ENV = "PORT"
_DEFAULT_HOST = "0.0.0.0"
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


def main(argv: Optional[list[str]] = None) -> int:
    """Parseia o subcomando e delega. Retorna o exit code (0 em caso de sucesso)."""
    argv = argv if argv is not None else sys.argv[1:]
    command = argv[0] if argv else "health"
    if command == "serve":
        return _serve()
    if command == "health":
        return _health()
    print(
        json.dumps(
            {"error": f"comando desconhecido: {command!r}", "usage": "serve | health"},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
