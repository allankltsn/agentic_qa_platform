"""QALayerContract: port puro (Protocol) do contrato de uma QA_Layer.

Define o contrato que toda QA_Layer deve satisfazer para participar da
orquestração (Requisitos 6.1, 6.2, 6.3). É código de domínio puro: sem qualquer
import de framework de orquestração (Agno), de ferramentas de avaliação ou de
infraestrutura (Requisito 12.1). O contrato é ``runtime_checkable`` para permitir
verificação de conformidade estrutural em tempo de execução (ex.: no
LayerRegistry), sem acoplar o domínio a implementações concretas.

Princípio advisory: a camada recebe o plano e o manifesto e produz
``LayerEvidence`` — evidência estruturada, nunca um veredito pass/fail
(Requisito 6.6).
"""

from typing import Protocol, runtime_checkable

from qa_platform.domain.value_objects.evidence import LayerEvidence
from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.domain.entities.manifest import QATargetManifest


@runtime_checkable
class QALayerContract(Protocol):
    """Contrato estrutural de uma QA_Layer (Requisitos 6.1, 6.2, 6.3).

    Toda implementação deve expor uma identidade estável e imutável e um método
    ``execute`` que, dado o plano e o manifesto, produz ``LayerEvidence``. É um
    ``Protocol`` puro: nenhuma dependência de Agno, ferramentas de avaliação ou
    infraestrutura vaza para o domínio (Requisito 12.1).
    """

    @property
    def layer_id(self) -> LayerId:
        """Identidade única e imutável da camada (Requisito 6.1)."""
        ...

    def execute(self, plan: ExecutionPlan, manifest: QATargetManifest) -> LayerEvidence:
        """Executa a camada e produz evidência estruturada (Requisitos 6.2, 6.3).

        Recebe o ``ExecutionPlan`` e o ``QATargetManifest`` e retorna
        ``LayerEvidence`` — evidência, nunca veredito pass/fail (Requisito 6.6).
        """
        ...
