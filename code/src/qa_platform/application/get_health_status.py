"""Caso de uso GetHealthStatus: produz o HealthStatus da camada domain.

Recebe a versão do serviço já resolvida por injeção e monta o value object
``HealthStatus``. Não lê variável de ambiente nem conhece FastAPI: a resolução
de configuração acontece na infraestrutura/composition_root, e a tradução para
HTTP acontece na interface (Requisitos 1.2, 1.3, 5.2).
"""

from qa_platform.domain.value_objects.health import HealthStatus


class GetHealthStatus:
    """Caso de uso que constrói o ``HealthStatus`` saudável do serviço.

    A versão do serviço é injetada no construtor (já resolvida por quem monta a
    aplicação), mantendo a camada application livre de leitura de ambiente e de
    dependências de framework web.
    """

    def __init__(self, service_version: str) -> None:
        self._service_version = service_version

    def execute(self) -> HealthStatus:
        """Retorna um ``HealthStatus`` saudável com a versão injetada."""
        return HealthStatus.healthy(version=self._service_version)
