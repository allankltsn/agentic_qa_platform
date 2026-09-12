"""RunRecordSerializer: round-trip ``RunResult`` ↔ ``RunRecordModel``/item.

Confina a validação e a (de)serialização do resultado de run à camada de
infraestrutura (steering ``12-organizacao-dataclasses``): converte o value
object de domínio ``RunResult`` no model Pydantic ``RunRecordModel`` (e no item
persistível) e de volta, sem vazar tipos de infraestrutura para o domínio e sem
importar ``boto3``.

Regras (Requisitos 3.2, 3.3, 3.4, 3.5):

- ``Severity`` é persistida pelo **nome** do enum (ex.: ``"HIGH"``) e
  reconstruída via ``Severity[nome]``, mantendo o registro independente do valor
  numérico interno (Requisito 3.2).
- O round-trip é sem perda: ``from_item(to_item(run_id, result, created_at))``
  produz um ``RunResult`` igual em valor ao original, com a identidade do alvo e
  todas as coleções aninhadas preservadas em ordem e identidade (Requisitos 3.2,
  3.3, 8.4).
- Um item com ``schema_version`` ausente/não suportado, ou malformado
  (``ValidationError`` do Pydantic), é traduzido para
  ``RunRecordSerializationError`` nomeando o ``run_id`` e o motivo, sem retornar
  um ``RunResult`` parcial ou silenciosamente incorreto (Requisitos 3.4, 3.5).
"""

from typing import Any

from pydantic import ValidationError

from qa_platform.domain.entities.execution_plan import ExecutionPlan, PlannedLayer
from qa_platform.domain.entities.run_result import RunResult, SkippedWork
from qa_platform.domain.exceptions import RunRecordSerializationError
from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId
from qa_platform.domain.value_objects.severity import Severity
from qa_platform.infrastructure.persistence.run_record_model import (
    SCHEMA_VERSION,
    FindingRecord,
    LayerEvidenceRecord,
    PlannedLayerRecord,
    RunRecordModel,
    SkippedWorkRecord,
)

_UNKNOWN_RUN_ID = "<desconhecido>"
"""Placeholder de ``run_id`` quando o item malformado não o expõe."""


# --------------------------------------------------------------------------- #
# Domínio -> registro (RunResult -> RunRecordModel)
# --------------------------------------------------------------------------- #


def _finding_to_record(finding: Finding) -> FindingRecord:
    """Converte um ``Finding`` de domínio, serializando severity pelo nome."""
    return FindingRecord(
        code=finding.code,
        severity=finding.severity.name,  # nome do enum (Req 3.2)
        detail=finding.detail,
    )


def _evidence_to_record(evidence: LayerEvidence) -> LayerEvidenceRecord:
    """Converte uma ``LayerEvidence``, preservando ordem dos achados."""
    return LayerEvidenceRecord(
        layer_id=evidence.layer_id.value,
        metrics=dict(evidence.metrics),
        findings=[_finding_to_record(f) for f in evidence.findings],
        reduced_mode=evidence.reduced_mode,
    )


def _planned_layer_to_record(layer: PlannedLayer) -> PlannedLayerRecord:
    """Converte uma ``PlannedLayer`` do plano de execução."""
    return PlannedLayerRecord(
        layer_id=layer.layer_id.value,
        priority=layer.priority,
        reduced_mode=layer.reduced_mode,
    )


def _skipped_to_record(skipped: SkippedWork) -> SkippedWorkRecord:
    """Converte um ``SkippedWork`` de domínio."""
    return SkippedWorkRecord(layer_id=skipped.layer_id, reason=skipped.reason)


def to_model(run_id: str, result: RunResult, created_at: str) -> RunRecordModel:
    """Converte um ``RunResult`` de domínio no ``RunRecordModel`` (Req 3.2).

    Serializa a identidade do alvo (``target_ref``/``target_version``, Req 8.4)
    e as coleções aninhadas preservando a ordem de origem. A ``Severity`` de
    cada achado é persistida pelo nome do enum (Req 3.2). O ``schema_version``
    corrente é gravado no registro (Req 3.5).
    """
    return RunRecordModel(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        target_ref=result.target_ref,
        target_version=result.target_version,
        created_at=created_at,
        plan=[_planned_layer_to_record(layer) for layer in result.plan.layers],
        evidences=[_evidence_to_record(e) for e in result.evidences],
        prioritized=[_evidence_to_record(e) for e in result.prioritized],
        skipped=[_skipped_to_record(s) for s in result.skipped],
        failures=list(result.failures),
    )


def to_item(run_id: str, result: RunResult, created_at: str) -> dict[str, Any]:
    """Converte um ``RunResult`` no item persistível (dict) do registro.

    Delega a ``to_model`` e serializa via ``model_dump``, produzindo um ``dict``
    pronto para persistência (item DynamoDB) sem importar ``boto3``.
    """
    return to_model(run_id, result, created_at).model_dump()


# --------------------------------------------------------------------------- #
# Registro -> domínio (item -> RunResult)
# --------------------------------------------------------------------------- #


def _record_to_finding(record: FindingRecord, run_id: str) -> Finding:
    """Reconstrói um ``Finding``, remapeando severity pelo nome do enum.

    Um nome de severity desconhecido é traduzido para
    ``RunRecordSerializationError`` nomeando o ``run_id`` e o motivo (Req 3.4).
    """
    try:
        severity = Severity[record.severity]  # nome -> enum (Req 3.2)
    except KeyError as exc:
        raise RunRecordSerializationError(
            run_id, f"severity desconhecida: {record.severity!r}"
        ) from exc
    return Finding(code=record.code, severity=severity, detail=record.detail)


def _record_to_evidence(record: LayerEvidenceRecord, run_id: str) -> LayerEvidence:
    """Reconstrói uma ``LayerEvidence`` preservando ordem/identidade (Req 3.3)."""
    return LayerEvidence(
        layer_id=LayerId(record.layer_id),
        metrics=dict(record.metrics),
        findings=tuple(_record_to_finding(f, run_id) for f in record.findings),
        reduced_mode=record.reduced_mode,
    )


def _record_to_planned_layer(record: PlannedLayerRecord) -> PlannedLayer:
    """Reconstrói uma ``PlannedLayer`` do plano de execução."""
    return PlannedLayer(
        layer_id=LayerId(record.layer_id),
        priority=record.priority,
        reduced_mode=record.reduced_mode,
    )


def _record_to_skipped(record: SkippedWorkRecord) -> SkippedWork:
    """Reconstrói um ``SkippedWork`` de domínio."""
    return SkippedWork(layer_id=record.layer_id, reason=record.reason)


def from_item(item: dict[str, Any]) -> RunResult:
    """Reconstrói o ``RunResult`` a partir de um item persistido (Req 3.2, 3.3).

    Valida o item contra o ``RunRecordModel`` e reconstrói integralmente as
    coleções aninhadas (plano, evidências, priorizadas, trabalho pulado e
    falhas), preservando ordem e identidade de origem. A ``Severity`` é
    remapeada pelo nome do enum.

    Sinaliza ``RunRecordSerializationError`` nomeando o ``run_id`` e o motivo,
    sem retornar um ``RunResult`` parcial, quando:

    - o ``schema_version`` está ausente ou não é suportado pela implementação
      corrente (Req 3.5); ou
    - o item é malformado e o Pydantic levanta ``ValidationError`` (Req 3.4); ou
    - a construção do value object de domínio rejeita o dado (ex.: severity
      desconhecida, id inválido).
    """
    run_id_hint = _extract_run_id_hint(item)

    # schema_version ausente/não suportado -> erro explícito (Req 3.5).
    schema_version = item.get("schema_version") if isinstance(item, dict) else None
    if schema_version is None:
        raise RunRecordSerializationError(run_id_hint, "schema_version ausente")
    if schema_version != SCHEMA_VERSION:
        raise RunRecordSerializationError(
            run_id_hint,
            f"schema_version não suportado: {schema_version!r} "
            f"(suportado: {SCHEMA_VERSION})",
        )

    # Item malformado -> ValidationError traduzida (Req 3.4).
    try:
        model = RunRecordModel.model_validate(item)
    except ValidationError as exc:
        raise RunRecordSerializationError(
            run_id_hint, f"item malformado: {exc.error_count()} erro(s) de validação"
        ) from exc

    # Reconstrução do domínio; rejeições do VO viram erro de serialização.
    try:
        return RunResult(
            run_id=RunId(model.run_id),
            target_ref=model.target_ref,
            target_version=model.target_version,
            plan=ExecutionPlan(
                layers=tuple(_record_to_planned_layer(p) for p in model.plan)
            ),
            evidences=tuple(
                _record_to_evidence(e, model.run_id) for e in model.evidences
            ),
            prioritized=tuple(
                _record_to_evidence(e, model.run_id) for e in model.prioritized
            ),
            skipped=tuple(_record_to_skipped(s) for s in model.skipped),
            failures=tuple(model.failures),
        )
    except RunRecordSerializationError:
        raise
    except (ValueError, KeyError) as exc:
        raise RunRecordSerializationError(
            model.run_id, f"reconstrução do domínio falhou: {exc}"
        ) from exc


def _extract_run_id_hint(item: object) -> str:
    """Extrai o ``run_id`` do item para nomear o erro, com fallback seguro.

    Um item malformado pode não ser um ``dict`` ou não expor ``run_id``; nesses
    casos usa-se um placeholder para que o erro ainda nomeie a run (Req 3.4).
    """
    if isinstance(item, dict):
        candidate = item.get("run_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return _UNKNOWN_RUN_ID
