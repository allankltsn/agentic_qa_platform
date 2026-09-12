"""RunStoreFactory: seleção do adapter de ``RunStateStore`` por variável de ambiente.

Constrói o adapter concreto do port ``RunStateStore`` a partir da configuração de
ambiente, retornando sempre um valor consumido apenas pelo contrato (port) — o
composition root nunca conhece a implementação escolhida (Req 4.4).

Seleção por ``RUN_STORE_BACKEND`` (default explícito ``in_memory``): o backend
in-memory usa o ``InMemoryRunStateStore`` já existente; o backend ``dynamodb``
usa o ``DynamoDBRunStateStore`` durável, exigindo ``RUN_TABLE_NAME``. Quando o
durável é pedido sem a tabela, a factory faz *fail-fast* com
``RunStoreConfigError`` nomeando o parâmetro ausente, **sem** cair no in-memory
(Req 4.3) — um laudo durável nunca é silenciosamente degradado para memória.

O ``import`` do adapter durável (e, por tabela, do ``boto3``) é **tardio**: só
acontece quando o backend ``dynamodb`` é de fato selecionado. Assim, importar
esta factory — e o pacote — permanece possível sem o SDK instalado quando apenas
o backend in-memory é usado (Req 6.4). O endpoint e a região reusam o mesmo
bootstrap AWS dos demais adapters (``AWS_ENDPOINT_URL`` / ``AWS_REGION``).
"""

import os

from qa_platform.domain.ports.run_state_store import RunStateStore
from qa_platform.infrastructure.persistence.in_memory_run_store import (
    InMemoryRunStateStore,
)

# Variáveis de ambiente que governam a seleção do adapter (Req 4.1, 4.2).
BACKEND_ENV = "RUN_STORE_BACKEND"  # "dynamodb" | "in_memory" (default)
TABLE_ENV = "RUN_TABLE_NAME"  # obrigatória quando backend == "dynamodb"
DEFAULT_BACKEND = "in_memory"  # default explícito (Req 4.2)


class RunStoreConfigError(Exception):
    """Backend durável selecionado sem parâmetros obrigatórios (Req 4.3).

    Sinaliza *fail-fast* de configuração: o backend ``dynamodb`` foi pedido sem
    ``RUN_TABLE_NAME``. A mensagem nomeia o parâmetro ausente e a factory não cai
    no in-memory — o chamador precisa corrigir a configuração antes de prosseguir.
    """


def build_run_store() -> RunStateStore:
    """Constrói o adapter de ``RunStateStore`` conforme o ambiente (Req 4.1, 4.2).

    Lê ``RUN_STORE_BACKEND`` (default ``in_memory``) e retorna sempre um valor
    consumível apenas pelo port ``RunStateStore`` (Req 4.4):

    - ``in_memory`` (ou ausente/default): ``InMemoryRunStateStore`` (Req 4.1).
    - ``dynamodb``: exige ``RUN_TABLE_NAME``; ausente → ``RunStoreConfigError``
      nomeando o parâmetro, **sem** cair no in-memory (Req 4.3). O
      ``DynamoDBRunStateStore`` é importado de forma **tardia** aqui, mantendo a
      factory e o pacote importáveis sem ``boto3`` quando só o in-memory é usado
      (Req 6.4). ``endpoint_url``/``region`` reusam ``AWS_ENDPOINT_URL`` /
      ``AWS_REGION``.

    Returns:
        Um adapter que satisfaz estruturalmente o port ``RunStateStore``.

    Raises:
        RunStoreConfigError: backend ``dynamodb`` selecionado sem ``RUN_TABLE_NAME``.
    """
    backend = (os.environ.get(BACKEND_ENV) or DEFAULT_BACKEND).strip().lower()
    if backend == "dynamodb":
        table_name = os.environ.get(TABLE_ENV)
        if not table_name:
            raise RunStoreConfigError(
                f"backend 'dynamodb' exige a variável de ambiente: {TABLE_ENV}"
            )  # Req 4.3 — fail-fast, sem cair no in-memory
        # Import tardio: boto3 só é exigido quando o durável é de fato usado (Req 6.4).
        from qa_platform.infrastructure.persistence.dynamodb_run_store import (
            DynamoDBRunStateStore,
        )

        return DynamoDBRunStateStore(
            table_name=table_name,
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None,
            region=os.environ.get("AWS_REGION") or None,
        )
    return InMemoryRunStateStore()  # default in-memory (Req 4.1, 4.2)
