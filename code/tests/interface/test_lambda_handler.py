"""Testes do ponto de entrada Lambda (``main.handler`` via Mangum).

Cobre o Requisito 3.2 — uma requisição API Gateway ``GET /health`` invocando o
``Lambda_Handler`` retorna HTTP 200 com o corpo de saúde em JSON — e o Requisito
3.3 — quando a inicialização falha (config obrigatória ausente), a exceção sobe
no import do módulo (``app = build_app()``), encerrando a init com erro, **sem**
produzir uma resposta HTTP 200.

Como ``main.app``/``main.handler`` são construídos no import do módulo, cada
teste controla ``SERVICE_VERSION`` ANTES de importar e limpa o cache de módulos
(``qa_platform.interface.api.main`` e ``qa_platform.composition_root``) para
evitar contaminação entre testes.

Validates: Requirements 3.2, 3.3
"""

from __future__ import annotations

import importlib
import json
import sys
from types import ModuleType

import pytest

from qa_platform.infrastructure.config import MissingConfigError

_MAIN_MODULE = "qa_platform.interface.api.main"
_ROOT_MODULE = "qa_platform.composition_root"


def _purge_modules() -> None:
    """Remove os módulos construídos no import para forçar reconstrução limpa."""
    sys.modules.pop(_MAIN_MODULE, None)
    sys.modules.pop(_ROOT_MODULE, None)


def _import_main() -> ModuleType:
    """Importa ``main`` do zero, garantindo que ``build_app()`` roda agora."""
    _purge_modules()
    return importlib.import_module(_MAIN_MODULE)


def _api_gateway_v1_health_event() -> dict:
    """Evento API Gateway v1 (REST) para ``GET /health`` que o Mangum roteia.

    Formato mínimo esperado pelo adapter ``Mangum`` para a API REST v1:
    ``httpMethod``/``path`` no topo e um ``requestContext`` com ``stage`` e
    ``http``/``identity`` suficientes para a tradução ASGI.
    """
    return {
        "version": "1.0",
        "resource": "/health",
        "path": "/health",
        "httpMethod": "GET",
        "headers": {"Host": "test.execute-api.local", "Accept": "application/json"},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourceId": "abc123",
            "resourcePath": "/health",
            "httpMethod": "GET",
            "path": "/prod/health",
            "stage": "prod",
            "domainName": "test.execute-api.local",
            "identity": {"sourceIp": "127.0.0.1", "userAgent": "pytest"},
            "requestId": "test-request-id",
        },
        "body": None,
        "isBase64Encoded": False,
    }


class _FakeLambdaContext:
    """Contexto mínimo do Lambda usado pelo Mangum na invocação."""

    function_name = "qa-platform-health"
    memory_limit_in_mb = 512
    invoked_function_arn = (
        "arn:aws:lambda:us-east-1:000000000000:function:qa-platform-health"
    )
    aws_request_id = "test-request-id"


def test_handler_get_health_retorna_200_com_corpo_de_saude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GET /health`` via API Gateway → 200 com ``{"status":"ok","version":...}``.

    Define ``SERVICE_VERSION`` antes de importar o módulo (a app é construída no
    import), invoca ``handler(event, context)`` e verifica o ``statusCode`` e o
    corpo (Req 3.2).
    """
    version = "9.9.9"
    monkeypatch.setenv("SERVICE_VERSION", version)
    # Hosts liberados para o TrustedHostMiddleware aceitar o Host do evento.
    monkeypatch.setenv("ALLOWED_HOSTS", "*")

    try:
        main = _import_main()

        response = main.handler(_api_gateway_v1_health_event(), _FakeLambdaContext())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body == {"status": "ok", "version": version}
    finally:
        _purge_modules()


def test_init_com_config_ausente_falha_sem_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com ``SERVICE_VERSION`` ausente, o import de ``main`` levanta
    ``MissingConfigError`` (falha de init), sem jamais produzir HTTP 200 (Req 3.3).
    """
    monkeypatch.delenv("SERVICE_VERSION", raising=False)

    try:
        # A falha sobe na construção da app (``app = build_app()``) no import,
        # antes de qualquer handler existir — logo, nenhum 200 é produzido.
        with pytest.raises(MissingConfigError):
            _import_main()

        # O módulo não deve ter sido registrado com um handler utilizável.
        assert _MAIN_MODULE not in sys.modules or not hasattr(
            sys.modules[_MAIN_MODULE], "handler"
        )
    finally:
        _purge_modules()
