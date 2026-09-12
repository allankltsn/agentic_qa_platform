"""Identidades de domínio: value objects puros ``LayerId`` e ``RunId``.

São código de domínio puro: sem qualquer import de framework de orquestração
(Agno), parser de YAML ou de infraestrutura. Ambos são value objects imutáveis
com igualdade por valor.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerId:
    """Identidade única e não-vazia de uma QA_Layer (Requisitos 6.1, 7.1).

    Campos:
        value: identificador da camada; rejeita ausente/vazio/só-espaços.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("LayerId não pode ser vazio")


@dataclass(frozen=True)
class RunId:
    """Identificador único de uma execução (Requisitos 1.3, 11.6).

    Campos:
        value: identificador da execução; rejeita ausente/nulo/vazio.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("RunId inválido: ausente ou vazio")  # Req 11.6
