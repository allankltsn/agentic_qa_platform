"""InMemoryRunStateStore: adapter in-memory do contrato ``RunStateStore``.

Implementa estruturalmente o port ``RunStateStore`` (Requisito 11.1) sem
qualquer persistência externa (Requisito 11.7): o estado e o resultado de cada
execução vivem em dicionários em memória enquanto o processo estiver ativo. É
um adapter de infraestrutura puro — depende apenas do domínio e da biblioteca
padrão, sem import de framework de orquestração (Agno), parser de YAML ou SDK
de nuvem (Requisito 12.1).
"""

from qa_platform.domain.exceptions import RunIdConflictError, RunNotFoundError
from qa_platform.domain.value_objects.ids import RunId
from qa_platform.domain.entities.run_result import RunResult, RunState


class InMemoryRunStateStore:
    """Adapter in-memory de ``RunStateStore`` (Requisitos 11.1, 11.7).

    Guarda o estado e o resultado de cada execução em dicionários indexados por
    ``run_id.value``. Preserva as semânticas de conflito (Requisito 11.3) e de
    ausência (Requisito 11.5) definidas no contrato. Não há persistência
    externa: os dados existem apenas enquanto o processo estiver em execução
    (Requisito 11.7).
    """

    def __init__(self) -> None:
        """Inicializa os armazenamentos internos vazios (Requisito 11.7)."""
        self._states: dict[str, RunState] = {}
        self._results: dict[str, RunResult] = {}

    def start(self, run_id: RunId, state: RunState) -> None:
        """Registra o estado inicial de ``run_id`` (Requisito 11.2).

        Persiste o estado inicial associado a ``run_id`` antes do primeiro passo
        do workflow, indexando o armazenamento interno por ``run_id.value``.
        """
        self._states[run_id.value] = state

    def record_failure(self, run_id: RunId, step: str, cause: str) -> None:
        """Registra a falha de ``step`` com ``cause`` na run ``run_id``.

        Aplica a transição pura ``RunState.with_failure`` sobre o estado atual,
        substituindo-o pelo novo estado. Se nenhum estado foi iniciado para
        ``run_id``, a operação é um no-op — os requisitos não exigem erro aqui.
        A ``cause`` nomeia o motivo da falha, nunca um valor de segredo
        (Requisitos 4.3, 12.1).
        """
        current = self._states.get(run_id.value)
        if current is not None:
            self._states[run_id.value] = current.with_failure(step, cause)

    def save_result(self, run_id: RunId, result: RunResult) -> None:
        """Persiste o resultado final de ``run_id`` (Requisito 11.4).

        Se já existir um resultado persistido para ``run_id``, NÃO sobrescreve e
        sinaliza conflito com ``RunIdConflictError`` nomeando o id
        (Requisito 11.3).
        """
        if run_id.value in self._results:
            raise RunIdConflictError(run_id.value)  # Req 11.3
        self._results[run_id.value] = result

    def get(self, run_id: RunId) -> RunResult:
        """Recupera o resultado persistido de ``run_id`` (Requisito 11.4).

        Se ``run_id`` nunca foi persistido, sinaliza ausência com
        ``RunNotFoundError`` nomeando o id (Requisito 11.5).
        """
        result = self._results.get(run_id.value)
        if result is None:
            raise RunNotFoundError(run_id.value)  # Req 11.5
        return result
