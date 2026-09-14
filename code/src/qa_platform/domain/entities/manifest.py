"""QATargetManifest: value object puro do manifesto de alvo de QA.

Representa o ``qa-target.yaml`` já parseado e validado, na forma de um value
object imutável do domínio. É código de domínio puro: sem qualquer import de
framework de orquestração (Agno), parser de YAML ou de infraestrutura
(Requisitos 6.2, 8.1, 12.1). O parser YAML vive na infraestrutura e produz
esta estrutura; os tipos do parser não vazam para o domínio.
"""

from dataclasses import dataclass, field

from qa_platform.domain.value_objects.discovery import DiscoveryInfo
from qa_platform.domain.value_objects.golden_case import GoldenCase
from qa_platform.domain.value_objects.ids import LayerId


@dataclass(frozen=True)
class RiskParameters:
    """Parâmetros de risco de uma camada, usados para derivar prioridade.

    Value object imutável e comparável por valor. Puro: nenhum tipo de
    framework. ``weight`` expressa a importância relativa da camada no
    planejamento por risco (Requisito 2.2).

    Campos:
        weight: peso de risco não-negativo da camada.
    """

    weight: float = 0.0


@dataclass(frozen=True)
class CostParameters:
    """Parâmetros de custo de uma camada, usados pela Cost_Condition.

    Value object imutável e comparável por valor. Puro: nenhum tipo de
    framework. Expõe um acessor puro que decide se o trabalho caro se
    justifica, sem qualquer efeito colateral (Requisitos 5.1, 5.4).

    Campos:
        risk_threshold: limiar de risco a partir do qual o trabalho caro se
            justifica.
        estimated_risk: risco estimado da camada para comparação com o limiar.
    """

    risk_threshold: float = 0.0
    estimated_risk: float = 0.0

    def justifies_expensive_work(self) -> bool:
        """Indica se o risco estimado justifica o trabalho caro (Req 5.1).

        Retorna ``True`` quando o risco estimado atinge ou supera o limiar.
        Função pura: não altera estado nem depende de fontes externas.
        """
        return self.estimated_risk >= self.risk_threshold


@dataclass(frozen=True)
class QATargetManifest:
    """Manifesto de alvo de QA, parseado e validado (Requisitos 6.2, 8.1).

    Value object imutável e comparável por valor. Puro: sem tipos de framework
    nem de parser YAML. Descreve o alvo a ser avaliado, as camadas aplicáveis
    e os parâmetros de risco/custo por camada.

    Campos:
        target_ref: referência do alvo (ex.: identificador do artefato).
        target_version: versão do alvo avaliado.
        applicable_layers: camadas de QA aplicáveis, na ordem declarada.
        risk_parameters: parâmetros de risco por ``LayerId``.
        cost_parameters: parâmetros de custo por ``LayerId``.
        discovery: resultado documental/derivado da inspeção estática (Fase 1).
            Advisory: não altera o roteamento das camadas (Requisitos 4.5, 4.6,
            5.1). Ausente no manifesto → ``DiscoveryInfo.empty()``.
        expected_domain: domínio esperado do alvo (campo de julgamento).
            Opcional; ``None`` quando ausente (Requisito 5.2).
        golden_set: casos candidatos do golden set, na ordem declarada.
            Opcional; tupla vazia quando ausente (Requisito 5.3).
    """

    target_ref: str
    target_version: str
    applicable_layers: tuple[LayerId, ...] = ()
    risk_parameters: dict[LayerId, RiskParameters] = field(default_factory=dict)
    cost_parameters: dict[LayerId, CostParameters] = field(default_factory=dict)
    discovery: DiscoveryInfo = field(default_factory=DiscoveryInfo.empty)
    expected_domain: str | None = None
    golden_set: tuple[GoldenCase, ...] = ()

    def risk_parameters_for(self, layer_id: LayerId) -> RiskParameters | None:
        """Retorna os parâmetros de risco de ``layer_id`` ou ``None``.

        Acessor puro: apenas consulta o mapa, sem efeitos colaterais.
        """
        return self.risk_parameters.get(layer_id)

    def cost_parameters_for(self, layer_id: LayerId) -> CostParameters | None:
        """Retorna os parâmetros de custo de ``layer_id`` ou ``None``.

        Acessor puro usado pela Cost_Condition (Requisito 5.3): apenas consulta
        o mapa, sem efeitos colaterais. Ausência de parâmetros é ``None``.
        """
        return self.cost_parameters.get(layer_id)
