"""HealthStatus: value object puro da camada domain.

Representa a resposta de saúde do serviço. É código de domínio puro: sem
qualquer import de framework web ou de infraestrutura (Requisito 5.2).
"""

from dataclasses import dataclass

STATUS_OK = "ok"


@dataclass(frozen=True)
class HealthStatus:
    """Value object imutável que descreve a saúde do serviço.

    Campos:
        status: sempre ``"ok"`` quando o serviço está de pé (Requisito 1.2).
        version: versão do serviço, vinda da configuração (Requisito 1.3).
    """

    status: str
    version: str

    @classmethod
    def healthy(cls, version: str) -> "HealthStatus":
        """Constrói um ``HealthStatus`` saudável para a versão informada."""
        return cls(status=STATUS_OK, version=version)
