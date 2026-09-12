"""RunRecordModel: model Pydantic do registro persistido do ``RunResult``.

Persistência é fronteira externa (steering ``12-organizacao-dataclasses``):
o registro persistido é descrito por models Pydantic ``BaseModel`` na camada de
infraestrutura, enquanto o domínio permanece ``@dataclass`` puro. Estes models
descrevem apenas a **forma** do item persistido — não importam ``boto3`` nem
qualquer SDK, e não conhecem os tipos de domínio (a conversão fica a cargo do
``RunRecordSerializer``).

O registro carrega ``schema_version`` para que o formato evolua sem afetar o
domínio (Requisito 3.5), e a identidade do alvo (``target_ref`` +
``target_version``) para que o laudo seja atribuível/comparável por alvo
(Requisito 8.4). ``Severity`` é persistida pelo **nome** do enum (ex.:
``"HIGH"``) no ``FindingRecord`` (Requisito 3.2), mantendo o registro
independente do valor numérico interno.
"""

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1
"""Versão atual do formato do registro persistido (Requisito 3.5)."""


class FindingRecord(BaseModel):
    """Registro persistido de um ``Finding`` de domínio.

    Campos:
        code: código estável do tipo de achado.
        severity: severidade pelo **nome** do enum ``Severity`` (ex.: ``"HIGH"``).
        detail: descrição legível do achado.
    """

    code: str
    severity: str
    detail: str


class LayerEvidenceRecord(BaseModel):
    """Registro persistido de uma ``LayerEvidence`` de domínio.

    Preserva a identidade da camada de origem e a ordem dos achados. Não há
    campo de veredito (o domínio é advisory, Requisito 6.6).

    Campos:
        layer_id: identidade da camada de origem.
        metrics: métricas numéricas nomeadas produzidas pela camada.
        findings: achados estruturados, na ordem produzida.
        reduced_mode: evidência produzida em modo reduzido (Requisito 5.2).
    """

    layer_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    findings: list[FindingRecord] = Field(default_factory=list)
    reduced_mode: bool = False


class PlannedLayerRecord(BaseModel):
    """Registro persistido de uma ``PlannedLayer`` de domínio.

    Campos:
        layer_id: identidade da camada planejada.
        priority: prioridade inteira determinística (Requisito 2.2).
        reduced_mode: camada planejada para rodar em modo reduzido (Requisito 5.2).
    """

    layer_id: str
    priority: int
    reduced_mode: bool = False


class SkippedWorkRecord(BaseModel):
    """Registro persistido de um ``SkippedWork`` de domínio.

    Campos:
        layer_id: identidade da camada cujo trabalho foi pulado.
        reason: motivo do salto.
    """

    layer_id: str
    reason: str


class RunRecordModel(BaseModel):
    """Registro persistido do ``RunResult`` (Requisitos 3.1, 3.5, 6.1, 8.4).

    Representa o item durável de um resultado de run. Carrega ``schema_version``
    para evolução de formato sem afetar o domínio (Requisito 3.5) e a identidade
    do alvo avaliado (``target_ref`` + ``target_version``) para que o laudo seja
    atribuível e comparável por alvo (Requisito 8.4). As coleções aninhadas
    preservam a ordem de origem das evidências, achados e trabalho pulado.

    Campos:
        schema_version: versão do formato do registro (default: ``SCHEMA_VERSION``).
        run_id: identidade da execução.
        target_ref: referência do alvo avaliado (Requisito 8.4).
        target_version: versão/commit do alvo avaliado (Requisito 8.4).
        created_at: instante de criação do registro em ISO-8601.
        plan: plano de execução serializado (camadas planejadas).
        evidences: evidências consolidadas de todas as camadas.
        prioritized: evidências ordenadas pelo Advisory_Judge.
        skipped: trabalho pulado por decisão de custo.
        failures: nomes/descrições de camadas ou passos que falharam.
    """

    schema_version: int = SCHEMA_VERSION
    run_id: str
    target_ref: str
    target_version: str
    created_at: str
    plan: list[PlannedLayerRecord] = Field(default_factory=list)
    evidences: list[LayerEvidenceRecord] = Field(default_factory=list)
    prioritized: list[LayerEvidenceRecord] = Field(default_factory=list)
    skipped: list[SkippedWorkRecord] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
