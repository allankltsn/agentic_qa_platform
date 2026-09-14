"""GoldenCase: value object puro de um caso candidato do golden set.

É código de domínio puro: sem qualquer import de framework de orquestração
(Agno), parser de YAML, Pydantic ou de infraestrutura/interface (Requisitos
5.3, 10.5). Value object imutável, comparado por valor.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenCase:
    """Caso candidato do golden set (Requisito 5.3). VO puro, imutável.

    Value object imutável e comparável por valor.

    Campos:
        input: entrada do caso de teste.
        expected: saída esperada para a entrada.
        note: nota opcional descrevendo o caso.
    """

    input: str
    expected: str
    note: str = ""
