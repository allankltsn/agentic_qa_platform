"""Testes da rota de saúde (``GET /health``) via ``TestClient`` (camada interface).

Cobre, por exemplo, que ``GET /health`` responde ``200`` com o corpo
``{"status": "ok", "version": ...}`` e com os cabeçalhos de segurança de borda
presentes, e que caminhos/métodos não definidos retornam o comportamento de
"não encontrado"/"não permitido" do FastAPI. Inclui também a Property 1 (a
versão do serviço injetada flui íntegra para o campo ``version`` da resposta).

Validates: Requirements 1.1, 1.2, 1.3, 1.5, 3.5
"""

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.interface.api.api import create_app

# TrustedHostMiddleware precisa aceitar o host usado pelo TestClient
# ("testserver"); usamos ["*"] para não bloquear a requisição em memória.
_ALLOWED_HOSTS = ["*"]
_CORS_ORIGINS: list[str] = []


def _build_client(service_version: str) -> TestClient:
    """Constrói a app com a versão dada e um ``TestClient`` sobre ela."""
    app = create_app(
        service_version=service_version,
        allowed_hosts=_ALLOWED_HOSTS,
        cors_origins=_CORS_ORIGINS,
    )
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Testes por exemplo
# --------------------------------------------------------------------------- #


def test_get_health_retorna_200_e_corpo_esperado() -> None:
    """``GET /health`` → ``200`` com corpo ``{"status": "ok", "version": ...}``
    contendo exatamente a versão injetada (Req 1.1, 1.2, 1.3)."""
    client = _build_client(service_version="1.2.3")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.2.3"}


def test_get_health_inclui_cabecalhos_de_seguranca() -> None:
    """A resposta de ``/health`` carrega os cabeçalhos de segurança de borda
    (nosniff, X-Frame-Options, HSTS e CSP) (Req 1.5)."""
    client = _build_client(service_version="1.0.0")

    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
    assert response.headers["Content-Security-Policy"] == "default-src 'none'"


def test_caminho_nao_definido_retorna_404() -> None:
    """Um caminho não definido (``GET /nope``) retorna ``404`` (Req 3.5)."""
    client = _build_client(service_version="1.0.0")

    response = client.get("/nope")

    assert response.status_code == 404


def test_metodo_nao_definido_em_health_retorna_405() -> None:
    """Um método não definido em ``/health`` (``POST /health``) retorna ``405``.

    O FastAPI/Starlette conhece o caminho ``/health`` (registrado para ``GET``),
    então um método não suportado resulta em ``405 Method Not Allowed`` — o
    comportamento de "não permitido" para uma rota existente (Req 3.5)."""
    client = _build_client(service_version="1.0.0")

    response = client.post("/health")

    assert response.status_code == 405


# --------------------------------------------------------------------------- #
# Teste de propriedade
# --------------------------------------------------------------------------- #

# Gerador de strings de versão não-vazias: descarta valores vazios ou compostos
# apenas por espaços em branco, restringindo ao espaço de entrada válido.
_non_empty_versions = st.text().filter(lambda v: v.strip() != "")


# Feature: executable-environment-bootstrap, Property 1
# Property 1: Versão da configuração flui íntegra para a resposta de saúde
# Validates: Requirements 1.1, 1.2, 1.3
# Nota: construir uma app + TestClient por exemplo é custoso; mantemos o trabalho
# mínimo (create_app + TestClient dentro do teste) e limitamos a 100 exemplos.
@settings(max_examples=100)
@given(service_version=_non_empty_versions)
def test_versao_flui_integra_para_a_resposta_de_saude(service_version: str) -> None:
    """Para qualquer versão não-vazia injetada na app, ``GET /health`` retorna
    ``200`` e o campo ``version`` do corpo é exatamente a versão injetada, com
    ``status == "ok"`` (Req 1.1, 1.2, 1.3)."""
    client = _build_client(service_version=service_version)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == service_version
    assert body["status"] == "ok"
