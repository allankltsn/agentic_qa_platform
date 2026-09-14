"""RunStateStore: port puro (Protocol) do contrato de persistência de run.

Define o contrato de armazenamento do estado e do resultado de uma execução do
orquestrador (Requisito 11.1). É código de domínio puro: sem qualquer import de
framework de orquestração (Agno), parser de YAML ou de infraestrutura
(Requisito 12.1). Adapters concretos (ex.: in-memory) vivem na infraestrutura e
implementam este contrato estruturalmente.

As semânticas de erro fazem parte do contrato e são nomeadas pelas exceções de
domínio: ``save_result`` sinaliza conflito ao persistir um ``RunId`` já
existente (Requisito 11.3) e ``get`` sinaliza ausência de um ``RunId`` nunca
persistido (Requisito 11.5).
"""

from typing import Protocol

from qa_platform.domain.entities.run_result import RunResult, RunState
from qa_platform.domain.value_objects.ids import RunId


class RunStateStore(Protocol):
    """Contrato estrutural de persistência de run (Requisitos 11.1, 12.1).

    ``Protocol`` puro: nenhuma dependência de framework ou infraestrutura vaza
    para o domínio. As implementações devem preservar as semânticas de conflito
    (Requisito 11.3) e de ausência (Requisito 11.5) descritas nos métodos.
    """

    def start(self, run_id: RunId, state: RunState) -> None:
        """Registra o estado inicial de uma execução (Requisito 11.2).

        Chamado antes do primeiro passo do workflow para persistir o estado
        inicial associado a ``run_id``.
        """
        ...

    def record_failure(self, run_id: RunId, step: str, cause: str) -> None:
        """Registra a falha de ``step`` com ``cause`` na run ``run_id``.

        A causa nomeia o passo/motivo da falha, nunca um valor de segredo
        (Requisitos 4.3, 12.1).
        """
        ...

    def save_result(self, run_id: RunId, result: RunResult) -> None:
        """Persiste o resultado final de uma execução (Requisito 11.4).

        Se já existir um resultado para ``run_id``, a implementação NÃO
        sobrescreve e sinaliza conflito com ``RunIdConflictError`` nomeando o id
        (Requisito 11.3).
        """
        ...

    def get(self, run_id: RunId) -> RunResult:
        """Recupera o resultado persistido de ``run_id`` (Requisito 11.4).

        Se ``run_id`` nunca foi persistido, a implementação sinaliza ausência
        com ``RunNotFoundError`` nomeando o id (Requisito 11.5).
        """
        ...
