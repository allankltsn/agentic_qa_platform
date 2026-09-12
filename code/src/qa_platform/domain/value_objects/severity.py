"""Severity: ordem total de severidade para priorização determinística.

É código de domínio puro: sem qualquer import de framework de orquestração
(Agno), parser de YAML ou de infraestrutura.
"""

from enum import IntEnum


class Severity(IntEnum):
    """Ordem total para priorização determinística (Requisito 10.1).

    Maior valor = mais severo: ``INFO < LOW < MEDIUM < HIGH < CRITICAL``.
    """

    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
