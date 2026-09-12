"""Rota de saúde (``GET /health``) da camada interface.

Expõe o ``HealthResponse`` (contrato HTTP em Pydantic) e a factory
``build_health_router`` que monta o ``APIRouter`` a partir do caso de uso
``GetHealthStatus`` injetado. A rota vive exclusivamente na camada interface: o
domain não conhece nem depende dessa definição (Requisitos 1.1, 1.2, 1.3, 5.5).
"""

from fastapi import APIRouter
from pydantic import BaseModel

from qa_platform.application.get_health_status import GetHealthStatus


class HealthResponse(BaseModel):
    """Corpo JSON da resposta de saúde.

    ``status`` reporta a liveness do serviço (``"ok"`` quando de pé) e
    ``version`` é a versão do serviço obtida da configuração (Requisitos 1.2, 1.3).
    """

    status: str
    version: str


def build_health_router(use_case: GetHealthStatus) -> APIRouter:
    """Monta o ``APIRouter`` com a rota ``GET /health``.

    Recebe o caso de uso ``GetHealthStatus`` por injeção e traduz o
    ``HealthStatus`` de domínio para o contrato HTTP ``HealthResponse``, sem que
    a interface conheça a resolução de configuração (feita no composition_root).
    """
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        result = use_case.execute()
        return HealthResponse(status=result.status, version=result.version)

    return router
