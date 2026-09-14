"""Configuração da aplicação (``Settings``) consumindo o ``SecretResolver``.

``load_settings`` consome o :class:`SecretResolver` para obter cada valor pelo
pipe de fallback ``env -> Secrets Manager`` e mantém a **falha rápida agregada**:
coleta *todas* as variáveis obrigatórias ausentes ou vazias em uma única passada
e levanta um único ``MissingConfigError`` nomeando cada uma (Requisitos 7.2, 7.3).
Variáveis opcionais recebem o default predefinido e ficam inspecionáveis no
objeto ``Settings`` (Requisito 7.4). ``SERVICE_VERSION`` permanece obrigatória
(Requisitos 1.3, 1.4).
"""

from __future__ import annotations

from dataclasses import dataclass

from qa_platform.infrastructure.secrets.resolver import (
    MissingSecretError,
    SecretResolver,
)


class MissingConfigError(RuntimeError):
    """Uma ou mais variáveis obrigatórias ausentes/vazias em TODAS as fontes.

    Impede o serviço de subir. Nomeia TODAS as variáveis com problema em uma
    única emissão — nunca valores (Requisitos 7.2, 7.3).
    """


@dataclass(frozen=True)
class Settings:
    """Configuração efetiva resolvida na inicialização.

    ``service_version`` é obrigatória (Requisitos 1.3, 1.4). ``log_level`` e
    ``environment`` são opcionais e recebem o default predefinido quando
    ausentes ou vazias (Requisito 7.4).
    """

    service_version: str  # obrigatória (Req 1.3, 1.4)
    log_level: str  # opcional, default "INFO" (Req 7.4)
    environment: str  # opcional, default "local" (Req 7.4)


_REQUIRED = ("SERVICE_VERSION",)
_OPTIONAL = {"LOG_LEVEL": "INFO", "ENVIRONMENT": "local"}


def load_settings(resolver: SecretResolver | None = None) -> Settings:
    """Resolve a configuração da aplicação com falha rápida agregada.

    Sem ``resolver``, usa um :class:`SecretResolver` que consulta apenas as
    variáveis de ambiente. Coleta TODAS as variáveis obrigatórias ausentes ou
    vazias em uma única passada e, havendo qualquer uma, levanta um único
    ``MissingConfigError`` nomeando cada uma em ordem (Requisitos 7.2, 7.3). As
    variáveis opcionais recebem o default predefinido em ``_OPTIONAL``
    (Requisito 7.4).
    """
    resolver = resolver or SecretResolver()  # sem provider: usa só env

    # Fail-fast agregado: coleta TODAS as obrigatórias ausentes em uma passada.
    missing: list[str] = []
    values: dict[str, str] = {}
    for name in _REQUIRED:
        try:
            values[name] = resolver.resolve(name, required=True)  # type: ignore[assignment]
        except MissingSecretError:
            missing.append(name)
    if missing:
        joined = ", ".join(sorted(missing))  # nomes, nunca valores (Req 7.3)
        raise MissingConfigError(
            f"Configuração obrigatória ausente ou vazia: {joined}. "
            f"Defina cada variável e reinicie o serviço."
        )

    return Settings(
        service_version=values["SERVICE_VERSION"],
        log_level=resolver.resolve(  # type: ignore[arg-type]
            "LOG_LEVEL", required=False, default=_OPTIONAL["LOG_LEVEL"]
        ),
        environment=resolver.resolve(  # type: ignore[arg-type]
            "ENVIRONMENT", required=False, default=_OPTIONAL["ENVIRONMENT"]
        ),
    )
