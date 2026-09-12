"""Testes do DynamoDBRunStateStore (adapter durável) com ``moto``.

Cobre o adapter durável do contrato ``RunStateStore`` sobre DynamoDB, usando
``moto`` (``@mock_aws``) para simular o serviço em memória, sem rede:

- Property 2 (round-trip persistir→recuperar): ``save_result`` → ``get`` retorna
  um ``RunResult`` igual ao persistido — tarefa 3.3 (teste de propriedade com
  Hypothesis).
- Property 3 + exemplos (tarefa 3.4, seção delimitada abaixo): conflito de
  ``run_id`` não sobrescreve; ausência sinaliza ``RunNotFoundError``; falha de
  infraestrutura sinaliza ``RunStorageError`` distinto de conflito/ausência;
  ``run_id`` vazio é rejeitado na construção do ``RunId`` de domínio.

Os helpers compartilhados (criação da tabela + construção de ``RunResult``) são
reusados por ambas as tarefas.
"""

from typing import Any

import boto3
import pytest
from moto import mock_aws

from qa_platform.domain.entities.execution_plan import ExecutionPlan, PlannedLayer
from qa_platform.domain.entities.run_result import RunResult, SkippedWork
from qa_platform.domain.exceptions import (
    RunIdConflictError,
    RunNotFoundError,
    RunStorageError,
)
from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId, RunId
from qa_platform.domain.value_objects.severity import Severity
from qa_platform.infrastructure.persistence.dynamodb_run_store import (
    DynamoDBRunStateStore,
)

# --------------------------------------------------------------------------- #
# Helpers compartilhados (tabela + fábrica de RunResult)
# --------------------------------------------------------------------------- #

_REGION = "us-east-1"
_TABLE_NAME = "qa-platform-run-history-test"
_PARTITION_KEY = "run_id"


def _create_table(table_name: str = _TABLE_NAME) -> Any:
    """Cria a tabela DynamoDB do histórico com PK ``run_id`` (padrão da spec).

    Espelha o provisionamento: chave de partição ``run_id`` (S), cobrança sob
    demanda. Deve rodar dentro de um contexto ``@mock_aws``.
    """
    resource = boto3.resource("dynamodb", region_name=_REGION)
    return resource.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": _PARTITION_KEY, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": _PARTITION_KEY, "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


def _make_store(table_name: str = _TABLE_NAME) -> DynamoDBRunStateStore:
    """Instancia o adapter durável com clock determinístico para os testes."""
    return DynamoDBRunStateStore(
        table_name=table_name,
        region=_REGION,
        clock=lambda: "2024-01-15T10:30:00Z",
    )


def _make_run_result(
    run_id: str = "run-001",
    *,
    target_ref: str = "repo/alvo",
    target_version: str = "v1.2.3",
) -> RunResult:
    """Constrói um ``RunResult`` completo (plano, evidências, achados, etc.).

    Inclui identidade do alvo, uma camada planejada, uma evidência com achado
    (severity persistida pelo nome), priorizadas, trabalho pulado e falhas, para
    exercitar o round-trip de forma representativa.
    """
    evidence = LayerEvidence(
        layer_id=LayerId("unit"),
        metrics={"coverage": 0.92},
        findings=(Finding(code="C001", severity=Severity.HIGH, detail="detalhe"),),
        reduced_mode=False,
    )
    return RunResult(
        run_id=RunId(run_id),
        target_ref=target_ref,
        target_version=target_version,
        plan=ExecutionPlan(
            layers=(PlannedLayer(layer_id=LayerId("unit"), priority=50),)
        ),
        evidences=(evidence,),
        prioritized=(evidence,),
        skipped=(SkippedWork(layer_id="e2e", reason="custo"),),
        failures=("smoke: timeout",),
    )


# =========================================================================== #
# Tarefa 3.4 — testes por exemplo do adapter (conflito, ausência,
# storage-error, run_id inválido)
# Feature: durable-run-state-store, Property 3
# Validates: Requirements 2.1, 2.2, 2.3, 2.4, 7.2, 7.3
# =========================================================================== #


@mock_aws
def test_save_result_conflito_nao_sobrescreve_e_mantem_original() -> None:
    """Segundo save_result do mesmo id → RunIdConflictError; get mantém original.

    Property 3: um ``run_id`` já persistido rejeita a segunda escrita com
    ``RunIdConflictError`` nomeando o id, sem sobrescrever; um ``get`` posterior
    retorna o ``RunResult`` original, inalterado.

    Validates: Requirements 2.1, 2.4; Property 3
    """
    _create_table()
    store = _make_store()
    run_id = RunId("run-conflict")
    original = _make_run_result("run-conflict", target_version="v1.0.0")

    store.save_result(run_id, original)

    # Uma segunda escrita com o MESMO id, mas conteúdo diferente, deve conflitar.
    outro = _make_run_result("run-conflict", target_version="v2.0.0")
    with pytest.raises(RunIdConflictError) as exc_info:
        store.save_result(run_id, outro)

    assert exc_info.value.run_id == "run-conflict"

    # O resultado persistido permanece o ORIGINAL, sem sobrescrita (Req 2.4).
    recuperado = store.get(run_id)
    assert recuperado == original
    assert recuperado.target_version == "v1.0.0"


@mock_aws
def test_get_id_nunca_salvo_sinaliza_run_not_found() -> None:
    """get de um id nunca persistido → RunNotFoundError nomeando o id.

    Validates: Requirements 2.2
    """
    _create_table()
    store = _make_store()

    with pytest.raises(RunNotFoundError) as exc_info:
        store.get(RunId("run-inexistente"))

    assert exc_info.value.run_id == "run-inexistente"


@mock_aws
def test_get_id_ausente_nao_retorna_resultado_de_outra_run() -> None:
    """get de id ausente sinaliza ausência sem devolver o RunResult de outra run.

    Persiste uma run e consulta OUTRO id: a ausência é sinalizada com
    ``RunNotFoundError``, jamais retornando o resultado da run existente.

    Validates: Requirements 2.2
    """
    _create_table()
    store = _make_store()
    store.save_result(RunId("run-existente"), _make_run_result("run-existente"))

    with pytest.raises(RunNotFoundError):
        store.get(RunId("run-outra"))


@mock_aws
def test_save_result_erro_de_infra_vira_run_storage_error_distinto() -> None:
    """Falha de infra (tabela inexistente) em save_result → RunStorageError.

    Aponta o store para uma tabela NÃO criada: o ``put_item`` falha por erro de
    infraestrutura, traduzido para ``RunStorageError`` nomeando a operação e o
    ``run_id``, distinto de conflito/ausência e sem vazar detalhes internos.

    Validates: Requirements 7.2, 7.3
    """
    store = _make_store(table_name="tabela-inexistente")
    run_id = RunId("run-infra-save")

    with pytest.raises(RunStorageError) as exc_info:
        store.save_result(run_id, _make_run_result("run-infra-save"))

    error = exc_info.value
    assert error.operation == "save_result"
    assert error.run_id == "run-infra-save"
    # Distinto de conflito e de ausência (Req 7.3).
    assert not isinstance(error, (RunIdConflictError, RunNotFoundError))


@mock_aws
def test_get_erro_de_infra_vira_run_storage_error_distinto() -> None:
    """Falha de infra (tabela inexistente) em get → RunStorageError distinto.

    O erro nomeia a operação (``get``) e o ``run_id``, e é distinto de
    ``RunNotFoundError`` (ausência de item) — uma falha de infraestrutura não
    pode ser confundida com um id inexistente (Req 7.3).

    Validates: Requirements 7.2, 7.3
    """
    store = _make_store(table_name="tabela-inexistente")
    run_id = RunId("run-infra-get")

    with pytest.raises(RunStorageError) as exc_info:
        store.get(run_id)

    error = exc_info.value
    assert error.operation == "get"
    assert error.run_id == "run-infra-get"
    assert not isinstance(error, (RunIdConflictError, RunNotFoundError))


def test_run_id_vazio_e_rejeitado_como_id_invalido() -> None:
    """run_id vazio → erro de id inválido, sem persistir nem retornar (Req 2.3).

    O ``RunId`` de domínio rejeita valor ausente/vazio/só-espaços na construção,
    de modo que o adapter nunca recebe um id inválido: nenhuma operação de
    storage chega a ser tentada.

    Validates: Requirements 2.3
    """
    with pytest.raises(ValueError):
        RunId("")
    with pytest.raises(ValueError):
        RunId("   ")


# =========================================================================== #
# Tarefa 3.3 — teste de propriedade do round-trip persistir → recuperar
# Feature: durable-run-state-store, Property 2
# Validates: Requirements 1.1, 1.2; Property 2
#
# Reusa os helpers compartilhados acima (``_create_table``/``_make_store``) e um
# gerador Hypothesis de ``RunResult`` variados (com identidade de alvo e coleções
# aninhadas), no mesmo padrão da Property 1 do serializer. Uma única tabela é
# criada por execução do teste (dentro do contexto ``@mock_aws``); cada exemplo
# do Hypothesis usa um ``run_id`` único para não colidir na tabela compartilhada
# (o conflito em si é coberto pela Property 3, acima).
# =========================================================================== #

from itertools import count  # noqa: E402

from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from qa_platform.domain.entities.execution_plan import (  # noqa: E402
    PRIORITY_MAX,
    PRIORITY_MIN,
)

# Texto não-vazio (após strip) para campos de identidade obrigatórios.
_non_empty_text = st.text(min_size=1, max_size=16).filter(lambda v: v.strip() != "")
# Texto livre (pode ser vazio) para campos sem restrição de vazio.
_free_text = st.text(min_size=0, max_size=24)
# Métricas: floats finitos dentro da faixa e precisão que o DynamoDB Number
# representa exatamente. O DynamoDB armazena números como Decimal (magnitude
# ~1E-130..9.9E+125, ~38 dígitos significativos): floats extremos (subnormais
# como 1e-308 ou 1e+127) estouram esse contexto (Under/Overflow) — um limite do
# backend, fora do escopo desta feature. Restringimos a uma faixa realista de
# métrica e a 6 casas decimais para que o round-trip float→Decimal→float seja
# exato e o teste exercite o contrato de persistência, não os limites numéricos
# do DynamoDB.
_finite_floats = st.floats(
    min_value=-1e9,
    max_value=1e9,
    allow_nan=False,
    allow_infinity=False,
    width=64,
).map(lambda v: round(v, 6))

# Contador de run_ids únicos entre exemplos do Hypothesis (mesmo contexto moto).
_RUN_ID_COUNTER = count()


def _ensure_table() -> None:
    """Cria a tabela do histórico de forma idempotente (reusa ``_create_table``).

    Todos os exemplos do teste de propriedade compartilham o mesmo backend
    ``@mock_aws``: a tabela é criada no primeiro exemplo e, nos seguintes, a
    tentativa de recriar é ignorada (``ResourceInUseException``), evitando um
    flag de estado frágil entre execuções.
    """
    try:
        _create_table()
    except Exception as exc:  # noqa: BLE001 — só ignora "tabela já existe"
        response = getattr(exc, "response", None)
        error = response.get("Error") if isinstance(response, dict) else None
        error_code = error.get("Code") if isinstance(error, dict) else None
        if error_code != "ResourceInUseException":
            raise


@st.composite
def _prop2_findings(draw: st.DrawFn) -> Finding:
    """Gera um ``Finding`` com severity de enum válido (persistida pelo nome)."""
    return Finding(
        code=draw(_free_text),
        severity=draw(st.sampled_from(list(Severity))),
        detail=draw(_free_text),
    )


@st.composite
def _prop2_layer_evidences(draw: st.DrawFn) -> LayerEvidence:
    """Gera uma ``LayerEvidence`` com métricas, achados e modo reduzido variados."""
    metrics = draw(
        st.dictionaries(keys=_non_empty_text, values=_finite_floats, max_size=4)
    )
    findings = tuple(draw(st.lists(_prop2_findings(), max_size=4)))
    return LayerEvidence(
        layer_id=LayerId(draw(_non_empty_text)),
        metrics=metrics,
        findings=findings,
        reduced_mode=draw(st.booleans()),
    )


@st.composite
def _prop2_planned_layers(draw: st.DrawFn) -> PlannedLayer:
    """Gera uma ``PlannedLayer`` com prioridade no intervalo válido."""
    return PlannedLayer(
        layer_id=LayerId(draw(_non_empty_text)),
        priority=draw(st.integers(min_value=PRIORITY_MIN, max_value=PRIORITY_MAX)),
        reduced_mode=draw(st.booleans()),
    )


@st.composite
def _prop2_skipped_work(draw: st.DrawFn) -> SkippedWork:
    """Gera um ``SkippedWork`` com layer_id e motivo."""
    return SkippedWork(layer_id=draw(_free_text), reason=draw(_free_text))


@st.composite
def _prop2_run_results(draw: st.DrawFn) -> RunResult:
    """Gera ``RunResult`` variados (com identidade de alvo e coleções aninhadas).

    O ``run_id`` real é reatribuído no teste (contador único) para não colidir
    na tabela ``moto`` compartilhada entre exemplos.
    """
    return RunResult(
        run_id=RunId("placeholder"),
        target_ref=draw(_non_empty_text),
        target_version=draw(_non_empty_text),
        plan=ExecutionPlan(
            layers=tuple(draw(st.lists(_prop2_planned_layers(), max_size=4)))
        ),
        evidences=tuple(draw(st.lists(_prop2_layer_evidences(), max_size=4))),
        prioritized=tuple(draw(st.lists(_prop2_layer_evidences(), max_size=4))),
        skipped=tuple(draw(st.lists(_prop2_skipped_work(), max_size=4))),
        failures=tuple(draw(st.lists(_free_text, max_size=4))),
    )


# Feature: durable-run-state-store, Property 2
# Property 2: round-trip persistir → recuperar no adapter durável (Req 1.1, 1.2).
# Validates: Requirements 1.1, 1.2; Property 2
@mock_aws
@settings(
    max_examples=100,
    # deadline=None: a criação única da tabela e a inicialização do moto/boto3
    # tornam o 1º exemplo bem mais lento que os demais — variabilidade de tempo,
    # não falha de correção. O round-trip em si é determinístico.
    deadline=None,
)
@given(generated=_prop2_run_results())
def test_round_trip_persistir_recuperar_durable(generated: RunResult) -> None:
    """save_result → get retorna um RunResult igual em valor ao persistido.

    Para qualquer RunId válido e RunResult, persistir e recuperar pelo adapter
    durável (DynamoDB simulado por moto) preserva o resultado por igualdade de
    valor — incluindo a identidade do alvo e todas as coleções aninhadas
    (Req 1.1, 1.2). Uma única tabela é criada por execução do teste; cada
    exemplo usa um run_id único para não colidir na tabela compartilhada.
    """
    # Garante a tabela de forma idempotente: todos os exemplos deste teste
    # compartilham um único backend @mock_aws, então a tabela é criada só no 1º
    # exemplo; nos seguintes a criação é ignorada (ResourceInUseException).
    _ensure_table()

    # run_id único por exemplo (o conflito é coberto pela Property 3 acima).
    run_id = RunId(f"run-prop2-{next(_RUN_ID_COUNTER)}")
    persisted = RunResult(
        run_id=run_id,
        target_ref=generated.target_ref,
        target_version=generated.target_version,
        plan=generated.plan,
        evidences=generated.evidences,
        prioritized=generated.prioritized,
        skipped=generated.skipped,
        failures=generated.failures,
    )

    store = _make_store()
    store.save_result(run_id, persisted)
    recovered = store.get(run_id)

    assert recovered == persisted
