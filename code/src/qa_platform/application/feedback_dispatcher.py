"""Feedback_Dispatcher: Executor_Function pura que encaminha o resultado.

Dispara o ``RunResult`` consolidado ao motor de feedback por meio de um
contrato plugável (``FeedbackSink``), sem realizar nenhuma integração externa
real nesta fase. O ``dispatch`` apenas encaminha o resultado ao sink recebido —
o sink default (in-memory/log) e quaisquer integrações concretas vivem na
infraestrutura e são injetados de fora (Requisito 2.1).

Executor_Function pura em rede/token: não invoca modelos de linguagem, não abre
conexões de rede e não importa framework de orquestração (Agno), parser de YAML
ou infraestrutura (Requisito 2.1). Depende exclusivamente do ``domain``.
"""

from typing import Protocol, runtime_checkable

from qa_platform.domain.entities.run_result import RunResult


@runtime_checkable
class FeedbackSink(Protocol):
    """Contrato estrutural do destino plugável do feedback (Requisito 2.1).

    ``Protocol`` puro e ``runtime_checkable``: nenhuma dependência de framework
    ou infraestrutura vaza para o domínio/application. As implementações
    concretas (in-memory/log nesta fase, integrações reais no futuro) vivem na
    infraestrutura e satisfazem este contrato estruturalmente.
    """

    def emit(self, result: RunResult) -> None:
        """Encaminha o ``RunResult`` ao destino de feedback (Requisito 2.1)."""
        ...


def dispatch(result: RunResult, sink: FeedbackSink) -> None:
    """Encaminha o ``RunResult`` ao ``sink`` plugável (Requisito 2.1).

    Executor_Function pura em rede/token: sem LLM, sem rede e sem integração
    externa real nesta fase (Requisito 2.1). A responsabilidade se limita a
    delegar a entrega ao sink injetado; a natureza do destino (in-memory/log
    nesta fase) é decidida na composição, fora desta função.

    Args:
        result: resultado consolidado da execução a ser disparado.
        sink: destino plugável que recebe o resultado.
    """
    sink.emit(result)
