"""Testes do RunRecordSerializer (round-trip + schema incompatível).

Cobre a fronteira de (de)serialização do ``RunResult`` na infraestrutura:

- Property 1 (round-trip sem perda): ``from_item(to_item(...)) == RunResult``
  original — tarefa 2.3 (teste de propriedade com Hypothesis).
- Property 4 (schema incompatível recusado): item com ``schema_version``
  ausente/desconhecido ou malformado → ``RunRecordSerializationError`` nomeando
  o ``run_id`` e o motivo, sem retornar um ``RunResult`` parcial — tarefa 2.4
  (testes por exemplo, abaixo).
"""

from typing import Any

import pytest

from qa_platform.domain.entities.run_result import RunResult
from qa_platform.domain.exceptions import RunRecordSerializationError
from qa_platform.domain.value_objects.severity import Severity
from qa_platform.infrastructure.persistence.run_record_model import SCHEMA_VERSION
from qa_platform.infrastructure.persistence.run_record_serializer import (
    from_item,
    to_item,
)

# --------------------------------------------------------------------------- #
# Property 4 — schema_version incompatível é recusado (tarefa 2.4)
# Feature: durable-run-state-store, Property 4
# Validates: Requirements 3.4, 3.5
# --------------------------------------------------------------------------- #

_RUN_ID = "run-schema-check"


def _valid_item() -> dict[str, Any]:
    """Item persistível válido de referência para os testes de schema.

    Produzido a partir de um ``RunResult`` real (com identidade de alvo e uma
    evidência com achado) para que só o cenário sob teste (schema/malformação)
    seja a causa do erro — nunca um item trivialmente inválido.
    """
    from qa_platform.domain.entities.execution_plan import (
        ExecutionPlan,
        PlannedLayer,
    )
    from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
    from qa_platform.domain.value_objects.ids import LayerId, RunId

    result = RunResult(
        run_id=RunId(_RUN_ID),
        target_ref="repo/alvo",
        target_version="v1.2.3",
        plan=ExecutionPlan(
            layers=(PlannedLayer(layer_id=LayerId("unit"), priority=50),)
        ),
        evidences=(
            LayerEvidence(
                layer_id=LayerId("unit"),
                metrics={"coverage": 0.9},
                findings=(
                    Finding(code="C001", severity=Severity.HIGH, detail="detalhe"),
                ),
            ),
        ),
    )
    return to_item(_RUN_ID, result, created_at="2024-01-15T10:30:00Z")


def test_valid_item_round_trips_as_baseline() -> None:
    """O item de referência é válido: from_item reconstrói o RunResult.

    Garante que os testes negativos abaixo falham pelo motivo pretendido
    (schema/malformação) e não por um item já inválido de saída.
    """
    result = from_item(_valid_item())
    assert isinstance(result, RunResult)
    assert result.run_id.value == _RUN_ID


def test_from_item_missing_schema_version_raises_naming_run_id() -> None:
    """schema_version ausente → RunRecordSerializationError nomeando o run_id.

    Validates: Requirements 3.4, 3.5
    """
    item = _valid_item()
    del item["schema_version"]

    with pytest.raises(RunRecordSerializationError) as exc_info:
        from_item(item)

    error = exc_info.value
    assert error.run_id == _RUN_ID
    assert "schema_version" in error.reason
    # Sem RunResult parcial: apenas o erro é sinalizado.
    assert not isinstance(exc_info.value, RunResult)


def test_from_item_unknown_schema_version_raises_naming_run_id() -> None:
    """schema_version desconhecido (999) → erro nomeando run_id e motivo.

    Validates: Requirements 3.4, 3.5
    """
    item = _valid_item()
    item["schema_version"] = 999
    assert item["schema_version"] != SCHEMA_VERSION

    with pytest.raises(RunRecordSerializationError) as exc_info:
        from_item(item)

    error = exc_info.value
    assert error.run_id == _RUN_ID
    assert "999" in error.reason


def test_from_item_malformed_missing_required_field_raises() -> None:
    """Item malformado (campo obrigatório ausente) → erro nomeando run_id.

    Remove ``target_ref`` (obrigatório no RunRecordModel), disparando o
    ValidationError do Pydantic traduzido para RunRecordSerializationError, sem
    retornar um RunResult parcial.

    Validates: Requirements 3.4, 3.5
    """
    item = _valid_item()
    del item["target_ref"]

    with pytest.raises(RunRecordSerializationError) as exc_info:
        from_item(item)

    error = exc_info.value
    assert error.run_id == _RUN_ID
    assert "malformado" in error.reason


def test_from_item_malformed_wrong_type_raises() -> None:
    """Item malformado (tipo errado em campo) → erro de serialização.

    ``plan`` deve ser uma lista de registros; um valor escalar dispara o
    ValidationError do Pydantic, traduzido para RunRecordSerializationError.

    Validates: Requirements 3.4, 3.5
    """
    item = _valid_item()
    item["plan"] = "não-é-uma-lista"

    with pytest.raises(RunRecordSerializationError) as exc_info:
        from_item(item)

    error = exc_info.value
    assert error.run_id == _RUN_ID
    assert "malformado" in error.reason


def test_from_item_non_dict_raises_with_placeholder_run_id() -> None:
    """Item que nem é dict → erro com run_id placeholder, sem RunResult parcial.

    Um item completamente malformado (não-dict) não expõe run_id; o erro ainda
    é sinalizado nomeando a run com o placeholder, sem retorno parcial.

    Validates: Requirements 3.4, 3.5
    """
    with pytest.raises(RunRecordSerializationError):
        from_item("lixo")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Property 1 — round-trip do serializer sem perda (tarefa 2.3)
# Feature: durable-run-state-store, Property 1
# Validates: Requirements 3.2, 3.3, 8.4
# --------------------------------------------------------------------------- #

from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from qa_platform.domain.entities.execution_plan import (  # noqa: E402
    PRIORITY_MAX,
    PRIORITY_MIN,
    ExecutionPlan,
    PlannedLayer,
)
from qa_platform.domain.entities.run_result import SkippedWork  # noqa: E402
from qa_platform.domain.value_objects.evidence import (  # noqa: E402
    Finding,
    LayerEvidence,
)
from qa_platform.domain.value_objects.ids import LayerId, RunId  # noqa: E402

# Texto não-vazio (após strip) para campos de identidade obrigatórios.
_non_empty_text = st.text(min_size=1, max_size=16).filter(lambda v: v.strip() != "")
# Texto livre (pode ser vazio) para campos sem restrição de vazio.
_free_text = st.text(min_size=0, max_size=24)
# Floats finitos: NaN/inf quebrariam a igualdade por valor no round-trip, e o
# Pydantic coage ints para float em ``dict[str, float]`` — por isso só floats.
_finite_floats = st.floats(allow_nan=False, allow_infinity=False, width=64)


@st.composite
def _findings(draw: st.DrawFn) -> Finding:
    """Gera um ``Finding`` com severity de enum válido (persistida pelo nome)."""
    return Finding(
        code=draw(_free_text),
        severity=draw(st.sampled_from(list(Severity))),
        detail=draw(_free_text),
    )


@st.composite
def _layer_evidences(draw: st.DrawFn) -> LayerEvidence:
    """Gera uma ``LayerEvidence`` com métricas, achados e modo reduzido variados."""
    metrics = draw(
        st.dictionaries(keys=_non_empty_text, values=_finite_floats, max_size=4)
    )
    findings = tuple(draw(st.lists(_findings(), max_size=4)))
    return LayerEvidence(
        layer_id=LayerId(draw(_non_empty_text)),
        metrics=metrics,
        findings=findings,
        reduced_mode=draw(st.booleans()),
    )


@st.composite
def _planned_layers(draw: st.DrawFn) -> PlannedLayer:
    """Gera uma ``PlannedLayer`` com prioridade no intervalo válido."""
    return PlannedLayer(
        layer_id=LayerId(draw(_non_empty_text)),
        priority=draw(st.integers(min_value=PRIORITY_MIN, max_value=PRIORITY_MAX)),
        reduced_mode=draw(st.booleans()),
    )


@st.composite
def _skipped_work(draw: st.DrawFn) -> SkippedWork:
    """Gera um ``SkippedWork`` com layer_id e motivo."""
    return SkippedWork(layer_id=draw(_free_text), reason=draw(_free_text))


@st.composite
def _run_results(draw: st.DrawFn) -> RunResult:
    """Gera ``RunResult`` variados, com identidade de alvo e coleções aninhadas."""
    return RunResult(
        run_id=RunId(draw(_non_empty_text)),
        target_ref=draw(_non_empty_text),
        target_version=draw(_non_empty_text),
        plan=ExecutionPlan(layers=tuple(draw(st.lists(_planned_layers(), max_size=4)))),
        evidences=tuple(draw(st.lists(_layer_evidences(), max_size=4))),
        prioritized=tuple(draw(st.lists(_layer_evidences(), max_size=4))),
        skipped=tuple(draw(st.lists(_skipped_work(), max_size=4))),
        failures=tuple(draw(st.lists(_free_text, max_size=4))),
    )


# Feature: durable-run-state-store, Property 1
# Property 1: round-trip do serializer sem perda (Req 3.2, 3.3, 8.4).
# Validates: Requirements 3.2, 3.3, 8.4; Property 1
@settings(max_examples=100)
@given(result=_run_results(), created_at=_non_empty_text)
def test_round_trip_serializer_sem_perda(result: RunResult, created_at: str) -> None:
    """from_item(to_item(...)) reconstrói o RunResult igual em valor ao original.

    Para qualquer RunResult válido, o round-trip preserva a identidade do alvo
    (``target_ref``/``target_version``) e todas as coleções aninhadas (plano,
    evidências, achados, trabalho pulado, falhas) em ordem e identidade
    (Req 3.2, 3.3, 8.4).
    """
    item = to_item(result.run_id.value, result, created_at)
    reconstructed = from_item(item)

    assert reconstructed == result
