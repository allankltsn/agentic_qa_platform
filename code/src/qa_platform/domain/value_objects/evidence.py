"""LayerEvidence e Finding: value objects puros de evidência de camada.

Representam a saída estruturada de uma QA_Layer. São código de domínio puro:
sem qualquer import de framework de orquestração (Agno), parser de YAML ou de
infraestrutura (Requisitos 6.5, 12.1). Ambos são value objects imutáveis com
igualdade por valor.

Princípio advisory (Requisito 6.6): ``LayerEvidence`` NÃO contém nenhum campo
de veredito (``passed``/``failed``/``verdict``). A camada produz evidência,
nunca sentença; a priorização e a leitura advisory ficam a cargo do
Advisory_Judge, sem emitir pass/fail.
"""

from dataclasses import dataclass, field

from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.domain.value_objects.severity import Severity


@dataclass(frozen=True)
class Finding:
    """Achado individual produzido por uma camada de QA.

    Value object imutável e comparável por valor.

    Campos:
        code: código estável que identifica o tipo de achado.
        severity: severidade do achado, para priorização (Requisito 10.1).
        detail: descrição legível do achado.
    """

    code: str
    severity: Severity
    detail: str


@dataclass(frozen=True)
class LayerEvidence:
    """Evidência estruturada de uma QA_Layer, SEM veredito (Requisito 6.6).

    Value object imutável e comparável por valor. Preserva a identidade da
    camada de origem (Requisito 2.4). Usa contêineres imutáveis: ``tuple`` para
    ``findings`` e ``dict`` para ``metrics`` (via ``default_factory``).

    Não existe — por design — nenhum campo ``passed``/``failed``/``verdict``:
    a camada não sentencia, apenas reporta evidência (Requisito 6.6).

    Campos:
        layer_id: identidade da camada de origem.
        metrics: métricas numéricas nomeadas produzidas pela camada.
        findings: achados estruturados, na ordem produzida.
        reduced_mode: indica que a evidência foi produzida em modo reduzido
            (economia de custo, Requisito 5.2).
    """

    layer_id: LayerId
    metrics: dict[str, float] = field(default_factory=dict)
    findings: tuple[Finding, ...] = ()
    reduced_mode: bool = False
