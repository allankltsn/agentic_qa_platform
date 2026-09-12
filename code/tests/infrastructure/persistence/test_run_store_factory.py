"""Testes da RunStoreFactory (seleção por env + fail-fast) — tarefa 4.2.

Cobre ``build_run_store`` no ponto de composição, exercitando a seleção do
adapter pelas variáveis de ambiente e o *fail-fast* de configuração, sempre
isolando o ambiente com ``monkeypatch``:

- Default (sem ``RUN_STORE_BACKEND``) → ``InMemoryRunStateStore`` (Req 4.1, 4.2).
- ``RUN_STORE_BACKEND=in_memory`` explícito → ``InMemoryRunStateStore`` (Req 4.2).
- ``RUN_STORE_BACKEND=dynamodb`` + ``RUN_TABLE_NAME`` → ``DynamoDBRunStateStore``
  durável (Req 4.1). A construção do adapter é tardia (import de ``boto3`` no
  ponto de uso), então este teste não exige ``boto3``/``moto``.
- ``RUN_STORE_BACKEND=dynamodb`` sem ``RUN_TABLE_NAME`` → ``RunStoreConfigError``
  nomeando o parâmetro ausente, **sem** cair no in-memory (Req 4.3, fail-fast).
"""

import pytest

from qa_platform.infrastructure.persistence.dynamodb_run_store import (
    DynamoDBRunStateStore,
)
from qa_platform.infrastructure.persistence.in_memory_run_store import (
    InMemoryRunStateStore,
)
from qa_platform.infrastructure.persistence.run_store_factory import (
    BACKEND_ENV,
    TABLE_ENV,
    RunStoreConfigError,
    build_run_store,
)


def test_build_run_store_default_returns_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem ``RUN_STORE_BACKEND``, o default explícito é o in-memory (Req 4.1, 4.2)."""
    monkeypatch.delenv(BACKEND_ENV, raising=False)
    monkeypatch.delenv(TABLE_ENV, raising=False)

    store = build_run_store()

    assert isinstance(store, InMemoryRunStateStore)


def test_build_run_store_in_memory_explicit_returns_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``RUN_STORE_BACKEND=in_memory`` explícito → ``InMemoryRunStateStore`` (Req 4.2)."""
    monkeypatch.setenv(BACKEND_ENV, "in_memory")
    monkeypatch.delenv(TABLE_ENV, raising=False)

    store = build_run_store()

    assert isinstance(store, InMemoryRunStateStore)


def test_build_run_store_dynamodb_with_table_returns_durable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``dynamodb`` + ``RUN_TABLE_NAME`` → adapter durável (Req 4.1).

    A construção é tardia (``boto3`` só é importado no uso), portanto instanciar
    o ``DynamoDBRunStateStore`` aqui não requer ``boto3``/``moto``.
    """
    monkeypatch.setenv(BACKEND_ENV, "dynamodb")
    monkeypatch.setenv(TABLE_ENV, "qa-platform-runs")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    store = build_run_store()

    assert isinstance(store, DynamoDBRunStateStore)


def test_build_run_store_dynamodb_without_table_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``dynamodb`` sem ``RUN_TABLE_NAME`` → ``RunStoreConfigError`` (Req 4.3).

    A mensagem nomeia o parâmetro ausente e a factory **não** cai no in-memory:
    um laudo durável nunca é silenciosamente degradado para memória.
    """
    monkeypatch.setenv(BACKEND_ENV, "dynamodb")
    monkeypatch.delenv(TABLE_ENV, raising=False)

    with pytest.raises(RunStoreConfigError) as exc_info:
        build_run_store()

    # A mensagem nomeia o parâmetro ausente (fail-fast acionável).
    assert TABLE_ENV in str(exc_info.value)
