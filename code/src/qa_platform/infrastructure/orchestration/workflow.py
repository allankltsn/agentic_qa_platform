"""Orchestrator_Workflow: adapter raiz da Agno v2 (infra) que executa pela engine.

Este módulo é o núcleo de orquestração do ADR-001 (Workflow-first). Diferente da
versão inicial (que usava executores ``_noop`` e um runner sequencial paralelo), esta
implementação **executa de fato pela engine da Agno**: cada ``Step`` tem um executor
real e a engine conduz a ordem canônica do ADR-001. Os tipos da Agno ficam **confinados
a este módulo de infraestrutura** — nunca vazam para o domínio (Requisito 12.2).

Entrega dois artefatos complementares:

- ``build_orchestrator``: monta o ``Workflow`` raiz da Agno na ordem definida do
  ADR-001 (Target_Discovery -> Risk_Planner -> [Router/Cost_Condition/execução de
  camadas] -> Evidence_Consolidator -> Advisory_Judge -> Feedback_Dispatcher), com
  ``Step(executor=fn)`` reais. Os dados de domínio (``ExecutionPlan``, ``RunResult``)
  trafegam entre steps via ``StepOutput.content`` (contrato confirmado da Agno v2). O
  ``manifest`` e o ``run_id`` são fixados por **closure** no wiring (não fluem pela
  cadeia da Agno).

- ``run_orchestration``: o wrapper fino que aciona ``workflow.run(...)`` e é responsável
  pelas responsabilidades transversais que a engine não cobre — validação do manifesto
  antes do 1º step (Req 8.2/8.3/8.5), atribuição de ``RunId`` e ``store.start`` com
  aborto sem steps se a persistência inicial falhar (Req 1.3/1.4), isolamento de falha
  de step com ``record_failure`` (Req 1.5) e ``save_result`` ao concluir (Req 11.2).

Decisão de concorrência: **caminho B (ADR-002)**. A execução concorrente das camadas é
um único ``Step`` cujo executor é ``run_layers`` (``ThreadPoolExecutor``, máx 8, timeout
300s), garantindo Req 4.1/4.4 que o ``Parallel`` nativo não expõe diretamente.

Persistência: o ``RunStateStore`` é a **fonte de verdade** do histórico; o ``db=`` da
Agno **não** é usado (ADR-001 — domínio independente de framework).

O controle de fluxo é determinístico e **não** consulta modelo de linguagem
(Requisito 1.6): a ordem e a seleção dos steps derivam apenas do manifesto e do plano.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace
from typing import Any, NoReturn

from agno.workflow import Step, Workflow  # tipos da Agno CONFINADOS à infra
from agno.workflow.types import StepInput, StepOutput

from qa_platform.application.advisory_judge import prioritize
from qa_platform.application.evidence_consolidator import consolidate
from qa_platform.application.feedback_dispatcher import FeedbackSink, dispatch
from qa_platform.application.risk_planner import plan_by_risk
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.entities.run_result import RunResult, RunState, SkippedWork
from qa_platform.domain.exceptions import OrchestrationDomainError
from qa_platform.domain.ports.run_state_store import RunStateStore
from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.value_objects.ids import RunId
from qa_platform.infrastructure.manifest.schema import validate_manifest
from qa_platform.infrastructure.orchestration.cost_condition import (
    should_skip_expensive,
)
from qa_platform.infrastructure.orchestration.parallel import run_layers
from qa_platform.infrastructure.orchestration.registry import LayerRegistry
from qa_platform.infrastructure.orchestration.router import select_layers

#: Nomes canônicos dos Orchestration_Steps na ordem do ADR-001 (Requisito 1.1).
STEP_TARGET_DISCOVERY = "target_discovery"
STEP_RISK_PLANNER = "risk_planner"
STEP_LAYERS = "layers"
STEP_EVIDENCE_CONSOLIDATOR = "evidence_consolidator"
STEP_ADVISORY_JUDGE = "advisory_judge"
STEP_FEEDBACK_DISPATCHER = "feedback_dispatcher"

#: Falha de registro do estado inicial no store, antes de qualquer step (Req 1.4).
INITIAL_STATE_STEP = "initial_state"

#: Sem retry no orquestrador determinístico: uma falha de step deve propagar de
#: imediato para o wrapper isolar/registrar (Req 1.5), sem novas tentativas.
_NO_RETRY = 1


class OrchestrationError(OrchestrationDomainError):
    """Falha na execução do Orchestrator_Workflow identificando o step afetado.

    Propaga a interrupção nomeando o Orchestration_Step que falhou e a causa,
    sem carregar valores de segredo (Requisitos 1.4, 1.5). É um erro de domínio
    de orquestração: a interface o traduz para a resposta apropriada.
    """

    def __init__(self, step: str, cause: str) -> None:
        self.step = step
        self.cause = cause
        super().__init__(f"Falha no step '{step}': {cause}")


def build_orchestrator(
    manifest: QATargetManifest,
    run_id: RunId,
    store: RunStateStore,
    registry: LayerRegistry,
    feedback_sink: FeedbackSink,
) -> Workflow:
    """Monta o ``Workflow`` raiz da Agno com executores REAIS (Requisito 1.1).

    A engine da Agno conduz a ordem canônica do ADR-001. Cada ``Step`` embrulha um
    componente do orquestrador num executor ``(StepInput) -> StepOutput``, trafegando
    value objects de domínio via ``StepOutput.content``. O ``manifest`` e o ``run_id``
    são fixados por closure (não fluem pela cadeia da Agno).

    O controle de fluxo é determinístico e não consulta modelo de linguagem: a seleção
    de camadas deriva do ``ExecutionPlan`` (Router) e a condição de custo depende apenas
    do manifesto (Requisitos 1.6, 3.4, 5.3). A execução concorrente das camadas é o
    executor ``run_layers`` (caminho B do ADR-002: máx 8, timeout 300s; Req 4.1/4.4).

    Os tipos da Agno (``Workflow``/``Step``) ficam confinados a este módulo
    (Requisito 12.2).

    Args:
        manifest: manifesto de alvo já parseado (VO puro do domínio).
        run_id: identidade da execução (fixada por closure na consolidação).
        store: contrato de persistência (usado pelo wrapper, não pelos steps).
        registry: registro de ``QA_Layer`` elegíveis (ponto de extensão).
        feedback_sink: destino plugável do feedback (in-memory/log nesta fase).

    Returns:
        O ``Workflow`` da Agno configurado com steps reais na ordem do ADR-001.
    """

    def _target_discovery(step_input: StepInput) -> StepOutput:
        """Descoberta mínima/determinística: valida a referência do alvo (Req 9.x).

        Nesta fase o manifesto já vem parseado; o step confirma que o alvo tem uma
        referência resolvível e repassa o manifesto adiante. Sem LLM/rede.
        """
        if not manifest.target_ref or not str(manifest.target_ref).strip():
            raise ValueError("referência de alvo ausente no manifesto")
        return StepOutput(content=manifest)

    def _risk_planner(_step_input: StepInput) -> StepOutput:
        """Risk_Planner: manifesto -> ExecutionPlan (Executor_Function puro, Req 2.x)."""
        return StepOutput(content=plan_by_risk(manifest))

    def _run_layers(step_input: StepInput) -> StepOutput:
        """Router + Cost_Condition + execução concorrente das camadas (caminho B).

        Seleciona deterministicamente as camadas do plano (Router, Req 3.x), aplica a
        Cost_Condition por camada (Req 5.x) e executa as restantes concorrentemente com
        ``run_layers`` (máx 8, timeout 300s; Req 4.1–4.4). Emite no ``content`` a tupla
        ``(plan, evidences, failures, skipped)`` para a consolidação.
        """
        plan = step_input.previous_step_content
        if not isinstance(plan, ExecutionPlan):
            raise TypeError("Layers step: ExecutionPlan ausente do step anterior")
        selected = select_layers(plan, registry)  # Req 3.x (UnknownLayerError se n/reg)

        to_run = []
        skipped: list[SkippedWork] = []
        for layer_id in selected:
            skip, reason = should_skip_expensive(manifest, layer_id)  # Req 5.x
            if skip:
                skipped.append(SkippedWork(layer_id=layer_id.value, reason=reason))
            else:
                to_run.append(layer_id)

        raw_evidences, parallel_failures = run_layers(to_run, registry, plan, manifest)

        # Contrato de camada (Req 6.3/6.4): filtra retornos não conformes; cada não
        # conformidade é nomeada como falha, preservando as demais evidências.
        evidences: list[LayerEvidence] = []
        contract_failures: list[str] = []
        for evidence in raw_evidences:
            violation = _contract_violation_reason(evidence)
            if violation is None:
                evidences.append(evidence)
                continue
            layer_name = _evidence_layer_name(evidence)
            contract_failures.append(f"{layer_name}: {violation}")

        failures = tuple(parallel_failures) + tuple(contract_failures)
        return StepOutput(content=(plan, tuple(evidences), failures, tuple(skipped)))

    def _consolidate(step_input: StepInput) -> StepOutput:
        """Evidence_Consolidator: agrega as evidências num RunResult (Req 2.4)."""
        content = step_input.previous_step_content
        if not isinstance(content, tuple) or len(content) != 4:
            raise TypeError("Consolidate step: conteúdo ausente do step anterior")
        plan, evidences, failures, skipped = content
        consolidated = consolidate(run_id, manifest, plan, evidences)
        # Preserva trabalho pulado e falhas de camada no RunResult (Req 5.2, 6.4),
        # mantendo a identidade do alvo já preenchida pela consolidação (Req 8.1/8.2).
        return StepOutput(
            content=replace(consolidated, skipped=skipped, failures=failures)
        )

    def _advisory_judge(step_input: StepInput) -> StepOutput:
        """Advisory_Judge: priorização determinística sem veredito (Req 10.x)."""
        result = step_input.previous_step_content
        if not isinstance(result, RunResult):
            raise TypeError("Advisory step: RunResult ausente do step anterior")
        return StepOutput(content=prioritize(result))

    def _feedback(step_input: StepInput) -> StepOutput:
        """Feedback_Dispatcher: encaminha o resultado ao sink plugável (Req 2.1)."""
        result = step_input.previous_step_content
        if not isinstance(result, RunResult):
            raise TypeError("Feedback step: RunResult ausente do step anterior")
        dispatch(result, feedback_sink)
        return StepOutput(content=result)

    steps: list[Any] = [
        Step(
            name=STEP_TARGET_DISCOVERY,
            executor=_target_discovery,
            max_retries=_NO_RETRY,
        ),
        Step(name=STEP_RISK_PLANNER, executor=_risk_planner, max_retries=_NO_RETRY),
        Step(name=STEP_LAYERS, executor=_run_layers, max_retries=_NO_RETRY),
        Step(
            name=STEP_EVIDENCE_CONSOLIDATOR,
            executor=_consolidate,
            max_retries=_NO_RETRY,
        ),
        Step(name=STEP_ADVISORY_JUDGE, executor=_advisory_judge, max_retries=_NO_RETRY),
        Step(name=STEP_FEEDBACK_DISPATCHER, executor=_feedback, max_retries=_NO_RETRY),
    ]
    return Workflow(name="qa-orchestrator", steps=steps, telemetry=False)


def run_orchestration(
    manifest: QATargetManifest,
    raw_manifest: dict[str, object],
    store: RunStateStore,
    registry: LayerRegistry,
    feedback_sink: FeedbackSink,
    *,
    run_id_factory: Callable[[], RunId] | None = None,
) -> RunResult:
    """Aciona a execução determinística do orquestrador pela engine da Agno.

    Wrapper fino em volta de ``workflow.run(...)`` responsável pelo que a engine não
    cobre, na ordem:

    1. Valida ``raw_manifest`` contra o schema **antes** do 1º step; se não conforme,
       encerra nomeando cada campo problemático via ``InvalidManifestError`` (sem
       executar step) e valida a correspondência de ids no registry (Req 8.2/8.3/8.5).
    2. Atribui um ``RunId`` único e chama ``store.start(...)``; se a persistência inicial
       falhar, aborta **sem** iniciar nenhum step (Req 1.3/1.4).
    3. Monta o ``Workflow`` (executores reais) e aciona ``workflow.run(...)``; a engine
       da Agno executa os steps na ordem do ADR-001 (Req 1.1). Se um step falhar, a
       exceção propaga: o wrapper chama ``record_failure`` e levanta ``OrchestrationError``
       identificando o step, preservando os concluídos (Req 1.5).
    4. Ao concluir, persiste o ``RunResult`` com ``store.save_result`` (Req 11.2).

    O controle de fluxo é determinístico e não consulta modelo de linguagem (Req 1.6).
    O ``RunStateStore`` é a fonte de verdade do histórico — o ``db=`` da Agno não é usado.

    Args:
        manifest: manifesto de alvo já parseado (VO puro do domínio).
        raw_manifest: manifesto parseado como ``dict`` para validação de schema.
        store: contrato de persistência de estado/resultado de run.
        registry: registro de ``QA_Layer`` elegíveis.
        feedback_sink: destino plugável do feedback.
        run_id_factory: fábrica opcional de ``RunId`` (para testes determinísticos);
            por padrão gera um ``RunId`` único via ``uuid4``.

    Returns:
        O ``RunResult`` consolidado, priorizado e persistido da execução.

    Raises:
        InvalidManifestError: se o manifesto não estiver conforme o schema.
        UnknownLayerError: se o manifesto referenciar camada não registrada.
        OrchestrationError: se a persistência inicial falhar (Req 1.4) ou se um step
            falhar durante a execução (Req 1.5).
    """
    # (1) Validação ANTES do 1º step (Req 8.2/8.3/8.5).
    validate_manifest(raw_manifest)
    registry.validate_manifest(manifest)

    # (2) RunId único + estado inicial ANTES de qualquer step; falha aqui aborta sem
    # iniciar step algum (Req 1.3/1.4).
    factory = run_id_factory or _default_run_id_factory
    run_id = factory()
    try:
        store.start(run_id, RunState(run_id=run_id))
    except Exception as exc:
        raise OrchestrationError(
            INITIAL_STATE_STEP,
            f"falha ao registrar o estado inicial: {type(exc).__name__}",
        ) from exc

    # (3) Executa pela engine da Agno (Req 1.1). Falha de step propaga como exceção:
    # isolamos, registramos e re-propagamos identificando o step (Req 1.5).
    workflow = build_orchestrator(
        manifest=manifest,
        run_id=run_id,
        store=store,
        registry=registry,
        feedback_sink=feedback_sink,
    )
    try:
        output = workflow.run(input={"target_ref": manifest.target_ref})
    except Exception as exc:  # noqa: BLE001 - falha durante a execução dos steps
        step = _failed_step_name(exc)
        _fail_step(store, run_id, step, exc)

    result = output.content
    if not isinstance(result, RunResult):
        _fail_step(
            store,
            run_id,
            STEP_FEEDBACK_DISPATCHER,
            TypeError(f"resultado final não é RunResult: {type(result).__name__}"),
        )

    # (4) Persiste o RunResult ao concluir (Req 11.2).
    store.save_result(run_id, result)
    return result


def _failed_step_name(exc: Exception) -> str:
    """Melhor esforço para nomear o step que falhou a partir da exceção da Agno.

    A Agno propaga a exceção do executor; quando não é possível derivar o nome do
    step da mensagem, usa-se um marcador estável (nunca um segredo).
    """
    text = str(exc).lower()
    for step in (
        STEP_TARGET_DISCOVERY,
        STEP_RISK_PLANNER,
        STEP_LAYERS,
        STEP_EVIDENCE_CONSOLIDATOR,
        STEP_ADVISORY_JUDGE,
        STEP_FEEDBACK_DISPATCHER,
    ):
        if step in text:
            return step
    return STEP_LAYERS


def _fail_step(
    store: RunStateStore, run_id: RunId, step: str, exc: Exception
) -> NoReturn:
    """Registra a falha de ``step`` e propaga ``OrchestrationError`` (Req 1.5).

    Interrompe a execução: registra a falha (step + causa) no store, preservando os
    concluídos, e propaga um erro que identifica o step afetado. A causa nomeia o tipo
    do erro, nunca um valor de segredo.
    """
    cause = f"{type(exc).__name__}: {exc}"
    store.record_failure(run_id, step, cause)
    raise OrchestrationError(step, cause) from exc


def _default_run_id_factory() -> RunId:
    """Gera um ``RunId`` único entre execuções via ``uuid4`` (Requisito 1.3)."""
    return RunId(str(uuid.uuid4()))


def _contract_violation_reason(evidence: object) -> str | None:
    """Retorna a razão da não conformidade de ``evidence`` ao contrato, ou ``None``.

    Verifica o retorno de uma camada contra o ``QA_Layer_Contract`` (Requisito 6.4):
    deve ser uma ``LayerEvidence`` que carrega a identidade da camada e os campos
    estruturados de métricas e achados. Retorna ``None`` quando conforme.
    """
    if not isinstance(evidence, LayerEvidence):
        return f"retorno não é LayerEvidence (obtido {type(evidence).__name__})"
    if evidence.layer_id is None or not evidence.layer_id.value.strip():
        return "identidade de camada ausente"
    if evidence.metrics is None:
        return "métricas ausentes"
    if evidence.findings is None:
        return "achados ausentes"
    return None


def _evidence_layer_name(evidence: object) -> str:
    """Nome legível da camada de uma evidência para mensagens de não conformidade.

    Extrai a identidade quando disponível; caso o retorno seja tão malformado que nem
    exponha identidade, usa um marcador estável (nunca um segredo).
    """
    layer_id = getattr(evidence, "layer_id", None)
    value = getattr(layer_id, "value", None)
    if isinstance(value, str) and value.strip():
        return value
    return "<camada desconhecida>"
