"""AILayerStub: camada de IA mínima que implementa o QA_Layer_Contract (infra).

A ``AILayerStub`` prova a extensibilidade do roteamento sem integrar ferramentas
reais de avaliação ou red teaming (Requisito 7.2). Expõe uma identidade única e
imutável (Requisito 7.1) e produz ``LayerEvidence`` de forma **determinística**,
derivada apenas do par ``(plan, manifest)`` recebido — sem chamadas de rede, sem
LLM, sem relógio nem aleatoriedade (Requisitos 7.2, 7.4).

O provider de modelo é resolvido por variável de ambiente (``MODEL_PROVIDER``) na
**inicialização**, reusando o ``SecretResolver`` do bootstrap: nenhum provider é
fixado no código e a ausência/vazio da env interrompe a inicialização nomeando a
env (fail-fast, Requisitos 12.5, 12.6).

Qualquer tipo de framework de agentes eventualmente usado por esta camada fica
confinado a este módulo de infraestrutura — nunca vaza para o domínio
(Requisito 7.3). Nesta fase a evidência é derivada deterministicamente e nenhum
agente real é instanciado.
"""

from __future__ import annotations

from qa_platform.domain.entities.execution_plan import ExecutionPlan
from qa_platform.domain.entities.manifest import QATargetManifest
from qa_platform.domain.value_objects.evidence import Finding, LayerEvidence
from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.domain.value_objects.severity import Severity
from qa_platform.infrastructure.secrets.resolver import (
    MissingSecretError,
    SecretResolver,
)

#: Nome da variável de ambiente que define o provider de modelo (Req 12.5, 12.6).
MODEL_PROVIDER_ENV = "MODEL_PROVIDER"


class AILayerStubError(RuntimeError):
    """Base dos erros da ``AILayerStub`` (infraestrutura).

    Não carrega valores de segredo; descreve apenas a condição de falha da
    camada.
    """


class InvalidLayerInputError(AILayerStubError):
    """Entrada inválida (plano/manifest ausente ou malformado) — Requisito 7.5.

    Sinaliza que a camada se absteve de produzir ``LayerEvidence`` porque a
    entrada não corresponde ao contrato esperado.
    """


class LayerExecutionError(AILayerStubError):
    """Falha durante a execução da camada — Requisito 7.6.

    Sinaliza uma falha interna sem retornar ``LayerEvidence`` parcial.
    """


class ModelProviderNotConfiguredError(AILayerStubError):
    """``MODEL_PROVIDER`` ausente/vazia na inicialização — Requisito 12.6.

    Interrompe a inicialização da camada nomeando a env ausente, sem selecionar
    um provider padrão fixado no código.
    """


class AILayerStub:
    """QA_Layer de IA mínima, determinística e sem ferramentas externas.

    Identidade única e imutável (Requisito 7.1). Implementa estruturalmente o
    ``QALayerContract``: expõe ``layer_id`` e ``execute(plan, manifest)``,
    retornando ``LayerEvidence`` — nunca um veredito pass/fail.

    O provider é resolvido por env na construção (Requisitos 12.5, 12.6); a
    execução não usa o provider para chamar nada externo nesta fase — a
    evidência é derivada apenas de ``(plan, manifest)`` (Requisitos 7.2, 7.4).
    """

    #: Identidade fixa, única e imutável desta camada (Requisito 7.1).
    _LAYER_ID = LayerId("ai")

    def __init__(self, resolver: SecretResolver | None = None) -> None:
        """Resolve o provider por env na inicialização (fail-fast).

        Args:
            resolver: ``SecretResolver`` opcional para testabilidade. Sem ele,
                usa um ``SecretResolver`` que consulta apenas variáveis de
                ambiente.

        Raises:
            ModelProviderNotConfiguredError: se ``MODEL_PROVIDER`` estiver
                ausente ou vazia em todas as fontes; nomeia a env sem selecionar
                um provider padrão (Requisitos 12.5, 12.6).
        """
        resolver = resolver or SecretResolver()  # sem provider: usa só env
        try:
            provider = resolver.resolve(MODEL_PROVIDER_ENV, required=True)
        except MissingSecretError as exc:
            # Fail-fast nomeando a env, sem provider default (Req 12.6).
            raise ModelProviderNotConfiguredError(
                f"Provider de modelo não configurado: a variável de ambiente "
                f"'{MODEL_PROVIDER_ENV}' está ausente ou vazia. Defina-a antes de "
                f"inicializar a camada; nenhum provider padrão é fixado no código."
            ) from exc
        # provider nunca é None aqui (required=True sem default garante isso).
        self._provider: str = provider  # type: ignore[assignment]

    @property
    def layer_id(self) -> LayerId:
        """Identidade única e imutável da camada (Requisito 7.1)."""
        return self._LAYER_ID

    @property
    def provider(self) -> str:
        """Provider de modelo resolvido por env na inicialização (Req 12.5)."""
        return self._provider

    def execute(self, plan: ExecutionPlan, manifest: QATargetManifest) -> LayerEvidence:
        """Produz ``LayerEvidence`` determinística derivada de ``(plan, manifest)``.

        Valida a entrada (Requisito 7.5) e, em sucesso, retorna uma evidência
        cujos campos dependem **apenas** de ``(plan, manifest)`` — sem invocar
        ferramentas externas de avaliação/red teaming (Requisito 7.2) e sem
        qualquer fonte de não-determinismo (relógio, rede, aleatoriedade). O
        mesmo par produz ``LayerEvidence`` igual em valor a cada chamada
        (Requisito 7.4). A evidência inclui a identidade da camada e uma
        referência estável ao ``ExecutionPlan`` recebido.

        Args:
            plan: plano de execução aplicável.
            manifest: manifesto de alvo de QA.

        Returns:
            ``LayerEvidence`` determinística com a identidade da camada, métricas
            derivadas e um ``Finding`` que referencia o plano recebido.

        Raises:
            InvalidLayerInputError: se ``plan`` ou ``manifest`` for ausente ou
                não for do tipo esperado (Requisito 7.5).
            LayerExecutionError: se ocorrer uma falha interna durante a derivação
                da evidência; nenhuma evidência parcial é retornada (Requisito 7.6).
        """
        self._validate_inputs(plan, manifest)

        try:
            plan_reference = self._plan_reference(plan)
            metrics: dict[str, float] = {
                "planned_layers": float(len(plan.layers)),
                "applicable_layers": float(len(manifest.applicable_layers)),
            }
            findings = (
                Finding(
                    code="ai.stub.plan_reference",
                    severity=Severity.INFO,
                    detail=(
                        f"target={manifest.target_ref}@{manifest.target_version}; "
                        f"plan={plan_reference}"
                    ),
                ),
            )
        except Exception as exc:  # falha interna → erro sem evidência parcial
            raise LayerExecutionError(
                f"Falha na execução da camada '{self._LAYER_ID.value}' ao derivar "
                f"a evidência."
            ) from exc

        return LayerEvidence(
            layer_id=self._LAYER_ID,
            metrics=metrics,
            findings=findings,
            reduced_mode=False,
        )

    @staticmethod
    def _validate_inputs(plan: ExecutionPlan, manifest: QATargetManifest) -> None:
        """Valida presença e tipo de ``plan``/``manifest`` (Requisito 7.5).

        Levanta ``InvalidLayerInputError`` nomeando a entrada inválida, sem
        produzir qualquer evidência.
        """
        invalid: list[str] = []
        if plan is None or not isinstance(plan, ExecutionPlan):
            invalid.append("plan")
        if manifest is None or not isinstance(manifest, QATargetManifest):
            invalid.append("manifest")
        if invalid:
            raise InvalidLayerInputError(
                "Entrada inválida para a AILayerStub: "
                f"{', '.join(invalid)} ausente(s) ou malformado(s)."
            )

    @staticmethod
    def _plan_reference(plan: ExecutionPlan) -> str:
        """Codifica uma referência estável e determinística ao plano recebido.

        Deriva uma string ordenada e reprodutível a partir das camadas
        planejadas (``layer_id`` + ``priority`` + ``reduced_mode``), servindo de
        referência ao ``ExecutionPlan`` na evidência (Requisito 7.2). Função
        pura: o mesmo plano produz sempre a mesma referência (Requisito 7.4).
        """
        parts = [
            f"{layer.layer_id.value}:{layer.priority}:{int(layer.reduced_mode)}"
            for layer in plan.layers
        ]
        return "[" + ",".join(parts) + "]"
