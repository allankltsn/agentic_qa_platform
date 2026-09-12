"""Hierarquia de erros de domínio da QA Platform.

Erros de domínio são puros: não carregam status HTTP nem detalhes de
infraestrutura. A camada interface é responsável por traduzi-los para a
resposta apropriada.
"""


class DomainError(Exception):
    """Base de todos os erros de domínio da QA Platform.

    Erros de domínio são puros: não carregam status HTTP nem detalhes de
    infraestrutura. A camada interface os traduz para a resposta apropriada.
    """


class ConfigurationDomainError(DomainError):
    """Estado de configuração inválido para o domínio operar.

    Ex.: uma versão de serviço ausente/vazia quando o domínio a exige. NÃO nomeia
    valores de segredo; apenas descreve a condição de domínio violada.
    """


class OrchestrationDomainError(DomainError):
    """Base dos erros de domínio da orquestração de QA.

    Erros de orquestração são puros: nomeiam campos, ids ou steps envolvidos na
    condição de domínio violada, mas nunca carregam valores de segredo.
    """


class InvalidManifestError(OrchestrationDomainError):
    """Manifest inválido: nomeia os campos problemáticos.

    Agrega todos os campos inválidos com o respectivo motivo. Nomeia apenas os
    nomes dos campos e a razão da violação — nunca valores de segredo.
    """

    def __init__(self, invalid_fields: dict[str, str]) -> None:
        self.invalid_fields = dict(invalid_fields)
        super().__init__(
            "; ".join(f"{k}: {v}" for k, v in sorted(self.invalid_fields.items()))
        )


class UnknownLayerError(OrchestrationDomainError):
    """Referências de camada não registradas/não correspondidas.

    Nomeia cada `layer_id` não reconhecido pelo registro de camadas.
    """

    def __init__(self, layer_ids: list[str]) -> None:
        self.layer_ids = sorted(set(layer_ids))
        super().__init__(f"Camadas não registradas: {', '.join(self.layer_ids)}")


class RunIdConflictError(OrchestrationDomainError):
    """Run_Id já persistido: sinaliza conflito sem sobrescrever o resultado."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Run_Id já persistido: {run_id}")


class RunNotFoundError(OrchestrationDomainError):
    """Run_Id inexistente: sinaliza ausência nomeando o id procurado."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Run_Id não encontrado: {run_id}")


class RunStorageError(OrchestrationDomainError):
    """Falha de infraestrutura ao persistir/ler uma run.

    Nomeia a operação e o Run_Id afetado, além de um motivo textual já
    sanitizado pela camada de infraestrutura. Nunca carrega credenciais,
    valores de segredo ou detalhes internos do SDK. Distinto de conflito
    (`RunIdConflictError`) e ausência (`RunNotFoundError`).
    """

    def __init__(self, operation: str, run_id: str, reason: str) -> None:
        self.operation = operation
        self.run_id = run_id
        self.reason = reason
        super().__init__(
            f"Falha de storage em '{operation}' para run '{run_id}': {reason}"
        )


class RunRecordSerializationError(OrchestrationDomainError):
    """Registro persistido malformado ou de schema incompatível.

    Nomeia o Run_Id afetado e o motivo da violação (ex.: `schema_version`
    ausente/desconhecido ou item inválido). Nunca carrega valores de segredo.
    """

    def __init__(self, run_id: str, reason: str) -> None:
        self.run_id = run_id
        self.reason = reason
        super().__init__(f"Registro inválido para run '{run_id}': {reason}")


class LayerContractViolation(OrchestrationDomainError):
    """Camada retornou valor não conforme ao QA_Layer_Contract."""


class TargetResolutionError(OrchestrationDomainError):
    """Referência de alvo ausente/irresolvível durante o Target_Discovery."""
