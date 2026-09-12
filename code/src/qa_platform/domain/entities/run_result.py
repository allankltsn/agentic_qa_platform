"""RunResult, RunState e SkippedWork: value objects puros do resultado de run.

Representam o estado e o resultado consolidado de uma execução do orquestrador.
São código de domínio puro: sem qualquer import de framework de orquestração
(Agno), parser de YAML ou de infraestrutura (Requisitos 6.5, 12.1). Todos são
value objects imutáveis com igualdade por valor, usando ``tuple`` para as
coleções para garantir imutabilidade e comparação determinística.
"""

from dataclasses import dataclass, replace

from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.value_objects.ids import RunId


@dataclass(frozen=True)
class SkippedWork:
    """Trabalho pulado por decisão de custo, com o motivo do salto.

    Value object imutável e comparável por valor (Requisitos 5.2, 5.5).

    Campos:
        layer_id: identidade da camada cujo trabalho foi pulado.
        reason: motivo não-vazio do salto.
    """

    layer_id: str
    reason: str


@dataclass(frozen=True)
class StepFailure:
    """Falha de um passo do workflow, identificando o passo e a causa.

    Value object imutável e comparável por valor. Não carrega valores de
    segredo nem detalhes de infraestrutura (Requisitos 4.3, 12.1).

    Campos:
        step: nome do passo que falhou.
        cause: descrição da causa da falha (nunca um valor de segredo).
    """

    step: str
    cause: str


@dataclass(frozen=True)
class RunState:
    """Estado imutável de uma execução em andamento (Requisitos 4.3, 5.2).

    Value object puro e comparável por valor. As transições são funcionais:
    métodos retornam um novo ``RunState`` em vez de mutar o atual, preservando
    a imutabilidade e o determinismo.

    Campos:
        run_id: identidade da execução.
        skipped: trabalho pulado por decisão de custo, na ordem registrada.
        failures: falhas de passo registradas, na ordem de ocorrência.
    """

    run_id: RunId
    skipped: tuple[SkippedWork, ...] = ()
    failures: tuple[StepFailure, ...] = ()

    def with_failure(self, step: str, cause: str) -> "RunState":
        """Registra a falha de ``step`` com ``cause`` e retorna novo estado.

        Transição pura e imutável (Requisito 4.3): não altera ``self``; devolve
        um ``RunState`` novo com a falha acrescentada ao final de ``failures``.
        """
        return replace(
            self,
            failures=(*self.failures, StepFailure(step=step, cause=cause)),
        )

    def with_skipped(self, layer_id: str, reason: str) -> "RunState":
        """Registra trabalho pulado e retorna um novo estado (Requisito 5.2).

        Transição pura e imutável: não altera ``self``; devolve um ``RunState``
        novo com o salto acrescentado ao final de ``skipped``.
        """
        return replace(
            self,
            skipped=(*self.skipped, SkippedWork(layer_id=layer_id, reason=reason)),
        )


@dataclass(frozen=True)
class RunResult:
    """Resultado consolidado de uma execução (Requisitos 2.4, 6.5).

    Value object imutável e comparável por valor. Preserva a identidade de
    origem das evidências (Requisito 2.4). As coleções são ``tuple`` para
    garantir imutabilidade e comparação determinística.

    Carrega a identidade do alvo avaliado (``target_ref`` + ``target_version``)
    para que os laudos sejam atribuíveis e comparáveis por alvo ao longo do
    tempo (Requisito 8.1). Apenas a referência e a versão do alvo entram aqui;
    os detalhes internos do agente alvo (prompts, tools) permanecem no
    ``qa-target.yaml`` de entrada (Requisito 8.3).

    Campos:
        run_id: identidade da execução.
        target_ref: referência do alvo avaliado (Requisito 8.1); obrigatório.
        target_version: versão do alvo avaliado (Requisito 8.1); obrigatório.
        plan: plano de execução usado na run.
        evidences: evidências consolidadas de todas as camadas.
        prioritized: evidências ordenadas pelo Advisory_Judge (Requisito 10.1);
            nunca descarta evidências de origem.
        skipped: trabalho pulado por decisão de custo (Requisito 5.2).
        failures: nomes/descrições das camadas ou passos que falharam
            (Requisito 4.3).
    """

    run_id: RunId
    target_ref: str
    target_version: str
    plan: ExecutionPlan
    evidences: tuple[LayerEvidence, ...] = ()
    prioritized: tuple[LayerEvidence, ...] = ()
    skipped: tuple[SkippedWork, ...] = ()
    failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Rejeita laudo órfão: sem alvo atribuível não há o que comparar.

        Um ``RunResult`` sem ``target_ref`` ou ``target_version`` (ausente ou
        vazio) não é atribuível a nenhum alvo e não deve ser consolidado nem
        persistido (Requisito 8.5).
        """
        if not self.target_ref or not str(self.target_ref).strip():
            raise ValueError("RunResult.target_ref obrigatório")
        if not self.target_version or not str(self.target_version).strip():
            raise ValueError("RunResult.target_version obrigatório")
