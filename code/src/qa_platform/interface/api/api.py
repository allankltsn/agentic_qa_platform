"""Factory da app FastAPI e aplicação da segurança de borda (camada interface).

Expõe ``apply_security`` — que encadeia os controles de borda (trusted host,
CORS restritivo, cabeçalhos de segurança, tratadores de erro neutros e os stubs
seguros de rate limit e redirect HTTPS) — e ``create_app`` — que monta a
``FastAPI`` com as docs públicas desabilitadas, injeta o caso de uso
``GetHealthStatus`` e inclui o router de saúde. Toda a resolução de configuração
acontece antes (composition_root); aqui só recebemos os valores já resolvidos
(Requisitos 1.1, 1.2, 1.5, 3.4, 5.5).
"""

from __future__ import annotations

from fastapi import FastAPI

from qa_platform.application.get_health_status import GetHealthStatus
from qa_platform.infrastructure.security.cors import add_cors
from qa_platform.infrastructure.security.error_handlers import (
    register_error_handlers,
)
from qa_platform.infrastructure.security.headers import add_security_headers
from qa_platform.infrastructure.security.https_redirect import add_https_redirect
from qa_platform.infrastructure.security.rate_limit import add_rate_limit
from qa_platform.infrastructure.security.trusted_host import add_trusted_host
from qa_platform.interface.api.health_routes import build_health_router


def apply_security(
    app: FastAPI, *, allowed_hosts: list[str], cors_origins: list[str]
) -> None:
    """Aplica os controles de segurança de borda à app, na ordem do design.

    Encadeia os controles FUNCIONAIS (trusted host, CORS sem ``"*"``, cabeçalhos
    de segurança e erro neutro) seguidos dos STUBS SEGUROS (rate limit e redirect
    HTTPS), ambos desligados por env por padrão no bootstrap — nunca "aprovam
    tudo" silenciosamente (Requisitos 1.1, 1.5).
    """
    add_trusted_host(app, allowed_hosts)  # allowed hosts (funcional)
    add_cors(app, cors_origins)  # CORS restritivo, sem "*" (funcional)
    add_security_headers(app)  # nosniff/HSTS/X-Frame/CSP (funcional)
    register_error_handlers(app)  # erro neutro, sem stack (funcional)
    add_rate_limit(app)  # stub: no-op enquanto RATE_LIMIT_ENABLED=false
    add_https_redirect(app)  # stub: no-op enquanto HTTPS_REDIRECT_ENABLED=false


def create_app(
    *,
    service_version: str,
    allowed_hosts: list[str],
    cors_origins: list[str],
) -> FastAPI:
    """Monta a app FastAPI do serviço com segurança e a rota de saúde.

    As docs públicas ficam desabilitadas por padrão (``docs_url``, ``redoc_url``
    e ``openapi_url`` em ``None``) para reduzir a superfície de exposição. Aplica
    a segurança de borda, injeta ``GetHealthStatus`` com a versão já resolvida e
    inclui o router de ``GET /health`` (Requisitos 1.1, 1.2, 3.4, 5.5).
    """
    # docs públicas desabilitadas por padrão (skill agno-security).
    app = FastAPI(
        title="QA Platform",
        version=service_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    apply_security(app, allowed_hosts=allowed_hosts, cors_origins=cors_origins)
    use_case = GetHealthStatus(service_version=service_version)
    app.include_router(build_health_router(use_case))
    return app
