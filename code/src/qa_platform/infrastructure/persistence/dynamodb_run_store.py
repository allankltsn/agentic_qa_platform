"""DynamoDBRunStateStore: adapter durável do contrato ``RunStateStore``.

Implementa estruturalmente o port ``RunStateStore`` sobre DynamoDB, persistindo
o ``RunResult`` final de cada execução de modo durável (sobrevive ao
encerramento do processo). Segue o padrão do adapter de Secrets Manager: o
``import boto3``/``botocore.config.Config`` é **tardio** (feito no ponto de uso),
de modo que este módulo — e o pacote — permanecem importáveis e testáveis sem o
SDK instalado quando apenas o backend in-memory é usado (Requisito 6.4).

Semânticas do contrato preservadas:

- ``save_result`` usa escrita condicional ``attribute_not_exists(run_id)``: um
  ``run_id`` já persistido resulta em ``RunIdConflictError`` sem sobrescrever o
  resultado anterior; duas escritas concorrentes do mesmo id resultam em
  exatamente uma persistida e a outra sinalizada como conflito (Req 2.1, 2.4).
- ``get`` de um ``run_id`` nunca persistido resulta em ``RunNotFoundError``
  (Req 2.2).
- ``run_id`` ausente/nulo/vazio é rejeitado ao construir o ``RunId`` de domínio,
  antes de qualquer acesso ao storage (Req 2.3).
- Falha de infraestrutura (indisponibilidade, timeout, tabela inexistente) é
  traduzida para ``RunStorageError`` nomeando a operação e o ``run_id``, distinta
  de conflito e de ausência, sem vazar credenciais ou detalhes internos do SDK
  (Req 7.2, 7.3).

Resiliência: o cliente é criado com ``botocore.config.Config`` definindo
timeouts explícitos de conexão e de leitura, além de retries, sem depender de
valores padrão implícitos do SDK (Requisito 7.1). Chave de partição = ``run_id``.

Nesta fase, ``start`` e ``record_failure`` são no-op durável (estado
intermediário fora de escopo): a validade do ``run_id`` já é garantida na
construção do ``RunId`` de domínio, e os métodos retornam sem persistir estado
intermediário, mantendo a compatibilidade do contrato do port (Req 1.3).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Optional

from qa_platform.domain.entities.run_result import RunResult, RunState
from qa_platform.domain.exceptions import (
    RunIdConflictError,
    RunNotFoundError,
    RunStorageError,
)
from qa_platform.domain.value_objects.ids import RunId
from qa_platform.infrastructure.persistence.run_record_serializer import (
    from_item,
    to_item,
)

# Timeouts explícitos (segundos) das chamadas ao storage durável (Req 7.1).
_CONNECT_TIMEOUT_SECONDS = 3
_READ_TIMEOUT_SECONDS = 5
_MAX_ATTEMPTS = 3

# Nome do atributo usado como chave de partição da tabela (= run_id).
_PARTITION_KEY = "run_id"


def _utcnow_iso() -> str:
    """Instante atual em ISO-8601 (UTC), usado como ``created_at`` do registro."""
    return datetime.now(timezone.utc).isoformat()


def _to_dynamo_numbers(value: Any) -> Any:
    """Converte ``float`` em ``Decimal`` recursivamente para o resource DynamoDB.

    O resource de alto nível do boto3 recusa ``float`` (exige ``Decimal``) ao
    (de)serializar o número para o tipo ``N`` do DynamoDB. As métricas do
    ``RunResult`` são ``float`` (ex.: cobertura), então o item persistível é
    percorrido em profundidade convertendo cada ``float`` para ``Decimal`` — via
    ``str`` para evitar imprecisão binária — antes do ``put_item``. ``bool`` é
    preservado (subtipo de ``int``, mas nunca deve virar número).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamo_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamo_numbers(v) for v in value]
    return value


def _from_dynamo_numbers(value: Any) -> Any:
    """Converte ``Decimal`` de volta para número nativo recursivamente.

    O resource do boto3 devolve números como ``Decimal``. O ``RunRecordModel``
    (Pydantic) espera ``float`` em ``metrics`` e ``int`` no ``schema_version``/
    ``priority``; o item lido é percorrido em profundidade traduzindo cada
    ``Decimal`` para ``int`` (quando integral) ou ``float``, de modo que o
    ``from_item`` reconstrua o ``RunResult`` igual em valor ao persistido.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {k: _from_dynamo_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_dynamo_numbers(v) for v in value]
    return value


class DynamoDBRunStateStore:
    """Adapter durável de ``RunStateStore`` sobre DynamoDB (Req 1, 2, 7).

    O ``table_name`` é obrigatório (a factory garante sua presença; Req 4.3). O
    ``endpoint_url`` e a ``region`` são opcionais e reusam a configuração do
    bootstrap AWS (LocalStack em dev, região do cliente). O recurso/tabela do
    boto3 é resolvido de forma preguiçosa no primeiro uso, com ``import boto3``
    tardio, preservando a importabilidade sem o SDK (Req 6.4).
    """

    def __init__(
        self,
        table_name: str,
        *,
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        """Configura o adapter sem tocar no SDK (import tardio no 1º uso).

        Args:
            table_name: nome da tabela DynamoDB do histórico de runs (obrigatório).
            endpoint_url: endpoint do serviço (ex.: LocalStack em dev); opcional.
            region: região do cliente DynamoDB; opcional.
            clock: função que produz o ``created_at`` ISO-8601; injetável para
                testes determinísticos. Default: ``_utcnow_iso`` (UTC).
        """
        self._table_name = table_name
        self._endpoint_url = endpoint_url
        self._region = region
        self._clock = clock or _utcnow_iso
        self._table: Any = None  # resolvido no 1º uso (import tardio)

    def _get_table(self) -> Any:
        """Resolve (e cacheia) o recurso ``Table`` do boto3 com timeouts (Req 7.1).

        O ``import boto3``/``Config`` é tardio: o módulo permanece importável sem
        o SDK; o boto3 só é exigido quando uma operação real toca o storage
        (Req 6.4). O cliente recebe timeouts explícitos de conexão/leitura e
        retries, sem depender de defaults implícitos do SDK (Req 7.1).
        """
        if self._table is None:
            import boto3  # import tardio: sem SDK, só falha se o storage for usado
            from botocore.config import Config

            config = Config(
                connect_timeout=_CONNECT_TIMEOUT_SECONDS,  # Req 7.1
                read_timeout=_READ_TIMEOUT_SECONDS,  # Req 7.1
                retries={"max_attempts": _MAX_ATTEMPTS, "mode": "standard"},
            )
            resource = boto3.resource(
                "dynamodb",
                endpoint_url=self._endpoint_url,
                region_name=self._region,
                config=config,
            )
            self._table = resource.Table(self._table_name)
        return self._table

    def save_result(self, run_id: RunId, result: RunResult) -> None:
        """Persiste o resultado final de ``run_id`` de forma durável (Req 1.1).

        Usa escrita condicional ``attribute_not_exists(run_id)`` para nunca
        sobrescrever um resultado já persistido: um ``run_id`` em conflito
        levanta ``RunIdConflictError`` nomeando o id (Req 2.1, 2.4). Uma falha
        de infraestrutura é traduzida para ``RunStorageError`` nomeando a
        operação e o ``run_id``, distinta do conflito, sem vazar segredos
        (Req 7.2, 7.3). O ``run_id`` inválido já foi rejeitado ao construir o
        ``RunId`` de domínio (Req 2.3).
        """
        item = _to_dynamo_numbers(
            {
                _PARTITION_KEY: run_id.value,
                **to_item(run_id.value, result, self._clock()),
            }
        )
        try:
            self._get_table().put_item(
                Item=item,
                ConditionExpression=f"attribute_not_exists({_PARTITION_KEY})",  # Req 2.1, 2.4
            )
        except Exception as exc:  # noqa: BLE001 — classificado abaixo por código
            if _is_conditional_check_failed(exc):
                raise RunIdConflictError(run_id.value) from exc  # Req 2.1
            raise RunStorageError(
                "save_result", run_id.value, _safe_reason(exc)
            ) from exc  # Req 7.2, 7.3

    def get(self, run_id: RunId) -> RunResult:
        """Recupera o ``RunResult`` durável de ``run_id`` (Req 1.2).

        Um ``run_id`` nunca persistido resulta em ``RunNotFoundError`` nomeando
        o id (Req 2.2). Uma falha de infraestrutura é traduzida para
        ``RunStorageError`` nomeando a operação e o ``run_id``, distinta da
        ausência, sem vazar segredos (Req 7.2, 7.3). O ``run_id`` inválido já
        foi rejeitado ao construir o ``RunId`` de domínio (Req 2.3).
        """
        try:
            response = self._get_table().get_item(Key={_PARTITION_KEY: run_id.value})
        except Exception as exc:  # noqa: BLE001 — classificado abaixo por código
            raise RunStorageError(
                "get", run_id.value, _safe_reason(exc)
            ) from exc  # Req 7.2, 7.3
        item = response.get("Item")
        if item is None:
            raise RunNotFoundError(run_id.value)  # Req 2.2
        return from_item(_from_dynamo_numbers(item))  # Req 1.2, 3.3

    def start(self, run_id: RunId, state: RunState) -> None:
        """Registra o estado inicial de ``run_id`` — no-op durável (Req 1.3).

        A persistência do estado intermediário está fora de escopo nesta fase;
        o método honra a assinatura do port (``start(run_id, state)``) e retorna
        sem persistir, preservando o contrato para o orquestrador. A validade do
        ``run_id`` já foi garantida ao construir o ``RunId`` de domínio, de modo
        que nenhuma validação adicional é necessária aqui.
        """

    def record_failure(self, run_id: RunId, step: str, cause: str) -> None:
        """Registra a falha de ``step`` em ``run_id`` — no-op durável (Req 1.3).

        A persistência do estado intermediário está fora de escopo nesta fase;
        o método honra a assinatura do port (``record_failure(run_id, step,
        cause)``) e retorna sem persistir, preservando o contrato para o
        orquestrador. A ``cause`` nomeia o motivo da falha, nunca um valor de
        segredo. A validade do ``run_id`` já foi garantida ao construir o
        ``RunId`` de domínio.
        """


def _is_conditional_check_failed(exc: Exception) -> bool:
    """Indica se ``exc`` é a falha de escrita condicional do DynamoDB.

    Reconhece o ``ClientError`` do botocore com código
    ``ConditionalCheckFailedException`` — o sinal de que a escrita condicional
    ``attribute_not_exists(run_id)`` recusou por o id já existir (Req 2.1). A
    inspeção é tolerante à ausência de ``response`` para não mascarar o erro.
    """
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    error = response.get("Error")
    if not isinstance(error, dict):
        return False
    return error.get("Code") == "ConditionalCheckFailedException"


def _safe_reason(exc: Exception) -> str:
    """Extrai um motivo textual seguro de ``exc``, sem vazar segredos (Req 7.2).

    Para um ``ClientError`` do botocore usa o código do erro (ex.:
    ``ResourceNotFoundException``), que descreve a condição de infraestrutura
    sem carregar credenciais, endpoints ou valores de segredo. Para outros
    erros usa apenas o nome da classe da exceção — nunca a mensagem crua, que
    poderia conter detalhes internos do SDK.
    """
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            code = error.get("Code")
            if isinstance(code, str) and code:
                return code
    return type(exc).__name__
