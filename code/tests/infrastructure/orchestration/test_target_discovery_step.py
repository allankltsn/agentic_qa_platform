"""Teste de integração — ``target_discovery`` como Step válido do Workflow.

Task 6.5 (hybrid-target-discovery). Comprova que ``discover_target`` continua
sendo um **executor de Step válido** do ``Orchestrator_Workflow`` (ADR-001) e que
o Draft produzido, ao trafegar **pela engine da Agno v2**, mantém a forma
consumida pelo fluxo: as chaves ``target``, ``applicable_layers`` e
``risk_parameters`` da Sprint 1, mais o novo bloco ``discovery`` (ADR-004,
Fase 1).

Em vez de chamar ``discover_target`` diretamente, o teste segue o padrão dos
demais testes de orquestração (``test_workflow.py``): monta um ``Workflow`` real
da Agno com um ``Step(executor=...)`` cujo executor invoca ``discover_target`` e
aciona ``workflow.run(...)``. O contrato confirmado da Agno v2 é ``StepInput`` na
entrada e ``StepOutput.content`` como veículo do dado entre steps / no resultado
final (``WorkflowRunOutput.content``) — exatamente como o wiring de produção em
``infrastructure/orchestration/workflow.py``.

A Fase 1 é determinística e **sem rede/LLM/AWS**: o ``target_ref`` aponta para um
arquivo sintético real sob ``tmp_path``, que o ``repo_reader`` lê do filesystem
local (sem moto, sem sockets).

_Requirements: 1.5_
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput

from qa_platform.infrastructure.manifest.target_discovery import (
    PENDING,
    discover_target,
    has_pending_fields,
)

# Nome canônico do primeiro Orchestration_Step do ADR-001 (mesma constante usada
# no wiring de produção). Mantê-lo explícito evita divergência silenciosa.
STEP_TARGET_DISCOVERY = "target_discovery"


def _build_discovery_workflow() -> Workflow:
    """Monta um ``Workflow`` real da Agno com ``discover_target`` como Step.

    Reproduz o wiring de produção: um ``Step`` cujo executor recebe o
    ``target_ref`` da entrada da run e devolve o Draft em ``StepOutput.content``,
    conduzido pela engine da Agno. ``telemetry=False`` mantém o teste offline.
    """

    def _target_discovery(step_input: StepInput) -> StepOutput:
        """Executor do Step: resolve o ``target_ref`` da entrada e produz o Draft."""
        raw_input = step_input.input
        raw_ref = raw_input.get("target_ref") if isinstance(raw_input, dict) else None
        target_ref = raw_ref if isinstance(raw_ref, str) else None
        return StepOutput(content=discover_target(target_ref))

    step = Step(name=STEP_TARGET_DISCOVERY, executor=_target_discovery, max_retries=1)
    return Workflow(name="qa-discovery-only", steps=[step], telemetry=False)


def _write_synthetic_target(tmp_path: Path) -> str:
    """Cria um artefato-alvo sintético (agente Agno) e devolve seu caminho.

    Conteúdo mínimo com um import de framework para exercitar a heurística de
    detecção; permanece determinístico e local (sem rede).
    """
    target = tmp_path / "agent.py"
    target.write_text(
        "from agno.agent import Agent\n\nagent = Agent(name='demo')\n",
        encoding="utf-8",
    )
    return str(target)


def test_discover_target_e_step_valido_do_workflow_e_produz_forma_consumida(
    tmp_path: Path,
) -> None:
    """Rodar o Step pela engine produz um Draft com a forma que o fluxo consome.

    Aciona ``discover_target`` como executor de um ``Step`` real da Agno via
    ``workflow.run(...)`` e afirma que o ``content`` do resultado é o Draft com as
    chaves da Sprint 1 (``target``/``applicable_layers``/``risk_parameters``) e o
    bloco ``discovery`` do ADR-004 (Req 1.5).
    """
    # Arrange — alvo sintético real sob tmp_path (Fase 1 lê o filesystem local).
    target_ref = _write_synthetic_target(tmp_path)
    workflow = _build_discovery_workflow()

    # Act — o Step é conduzido pela engine da Agno; o Draft volta em .content.
    output = workflow.run(input={"target_ref": target_ref})
    draft = output.content

    # Assert — o resultado é o Draft (dict) consumido pelo fluxo, não um evento.
    assert isinstance(draft, dict)

    # Forma da Sprint 1 preservada: as três chaves de topo que o fluxo consome.
    assert set(draft) >= {"target", "applicable_layers", "risk_parameters", "discovery"}
    assert draft["target"]["ref"] == target_ref
    assert isinstance(draft["applicable_layers"], list)
    assert draft["applicable_layers"]  # não vazio (identidades de camada)
    assert isinstance(draft["risk_parameters"], dict)
    # Cada camada aplicável tem entrada correspondente em risk_parameters.
    for layer_id in draft["applicable_layers"]:
        assert layer_id in draft["risk_parameters"]

    # Bloco discovery (ADR-004, Fase 1): forma documental/derivada esperada.
    discovery = draft["discovery"]
    assert isinstance(discovery, dict)
    assert set(discovery) >= {
        "framework",
        "frameworks_detected",
        "ambiguous",
        "tools",
        "prompts",
        "rag",
        "fragility_note",
    }
    # A nota de fragilidade é sempre preenchida (Req 3.5).
    assert isinstance(discovery["fragility_note"], str)
    assert discovery["fragility_note"].strip()

    # Draft (não manifesto completo): ainda contém campos PENDING (Req 1.2).
    assert has_pending_fields(draft)
    assert draft["target"]["version"] == PENDING


def test_step_produz_draft_identico_ao_discover_target_direto(
    tmp_path: Path,
) -> None:
    """O Draft via engine é igual ao de ``discover_target`` chamado diretamente.

    Garante que passar pelo Step da Agno não transforma nem reordena o Draft: o
    ``StepOutput.content`` é exatamente o dicionário determinístico produzido pela
    Fase 1, preservando o contrato de saída consumido pelo fluxo (Req 1.5).
    """
    # Arrange
    target_ref = _write_synthetic_target(tmp_path)
    workflow = _build_discovery_workflow()

    # Act
    via_engine: Any = workflow.run(input={"target_ref": target_ref}).content
    direct = discover_target(target_ref)

    # Assert — determinismo da Fase 1 preservado ponta a ponta.
    assert via_engine == direct
