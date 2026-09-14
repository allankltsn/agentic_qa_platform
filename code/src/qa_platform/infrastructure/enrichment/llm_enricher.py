"""LLMEnricher: adapter Agno-based da Fase 2 (advisory, fora do Workflow).

Este é o **único** módulo novo autorizado a importar ``agno`` (contrato
``agno-confinado``, Req 10.2). Os tipos do framework de agentes ficam
**confinados** a este módulo — nunca vazam para ``domain``/``application``/
``interface``. Por isso o import de ``agno`` é **tardio/lazy**, feito dentro dos
métodos: o módulo importa limpo mesmo sem o framework instalado e a fronteira de
fail-fast (resolução do ``MODEL_PROVIDER``) roda **antes** de qualquer import de
``agno``.

Responsabilidades (Requisitos 6.1, 6.6, 7.3, 7.4, 7.6, 9.1–9.3, 9.5):

- Resolver ``MODEL_PROVIDER`` via :class:`SecretResolver` **antes** de qualquer
  chamada ao provider de LLM (Req 9.1). Ausente/blank/fonte indisponível →
  fail-fast (~5s) com ``MissingSecretError`` nomeando SOMENTE a env, nunca o
  valor de qualquer segredo (Req 9.2, 9.3).
- Montar um Agent Agno (provider por env) com a stack mínima de guardrails do
  baseline do portfólio (PII + prompt-injection + moderação) mais um guardrail
  **customizado de escopo** que rejeita conteúdo fora de "descoberta de alvo de
  QA" (Req 9.5).
- Timeout duro (padrão 120s) → :class:`EnrichmentTimeoutError` (Req 6.6).
- **Nunca sobrescrever** o Draft: ``base_fields`` é cópia fiel do Draft e cada
  saída do LLM vira uma :class:`Suggestion` marcada (``origin``/``state=
  "pendente"``). Valor pré-existente é mantido; a sugestão entra como entrada
  separada (Req 7.3, 7.4, 7.6).
"""

from __future__ import annotations

import copy
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from qa_platform.infrastructure.enrichment.annotated_draft import (
    AnnotatedDraft,
    Suggestion,
)
from qa_platform.infrastructure.enrichment.errors import (
    EnrichmentError,
    EnrichmentTimeoutError,
    ScopeRejectedError,
)
from qa_platform.infrastructure.secrets.resolver import SecretResolver

#: Nome da variável de ambiente que define o provider de modelo (Req 9.1).
#: Mesma convenção do resto da plataforma (ver ``ai_layer_stub.MODEL_PROVIDER_ENV``).
MODEL_PROVIDER_ENV = "MODEL_PROVIDER"

#: Chave da OpenAI usada SOMENTE pelo ``OpenAIModerationGuardrail`` (não pelo
#: modelo). A moderação chama a API da OpenAI e exige esta chave; quando ausente,
#: o guardrail de moderação é omitido da stack (os demais — escopo, injeção, PII
#: — são locais e continuam ativos). Isso permite rodar com providers locais
#: (ex.: Ollama) sem rede externa nem credencial da OpenAI.
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

#: Timeout duro padrão do enriquecimento, em segundos (Req 6.6).
_DEFAULT_TIMEOUT_S = 120.0

#: Palavras-chave do escopo do enricher: "descoberta de alvo de QA" — sugerir
#: ``expected_domain``/``golden_set`` (Req 9.5). Baseline heurístico do guardrail
#: de escopo; reforça (não substitui) as ``instructions`` do agente.
_SCOPE_KEYWORDS: tuple[str, ...] = (
    "expected_domain",
    "golden_set",
    "golden",
    "domain",
    "domínio",
    "qa",
    "manifest",
    "manifesto",
    "target",
    "alvo",
    "discovery",
    "descoberta",
    "agent",
    "agente",
)


class LLMEnricher:
    """Enricher advisory da Fase 2 (Agno), fora do Workflow determinístico.

    Recebe o ``Draft`` determinístico e produz um :class:`AnnotatedDraft` com
    sugestões marcadas, sem nunca sobrescrever campos do Draft (Req 7). O
    provider de LLM é resolvido por env na chamada de :meth:`enrich`, **antes**
    de instanciar qualquer objeto do ``agno`` (fail-fast, Req 9.1–9.3).
    """

    def __init__(
        self, resolver: SecretResolver, *, timeout_s: float = _DEFAULT_TIMEOUT_S
    ) -> None:
        """Guarda o resolver e o timeout duro; não toca em ``agno`` aqui.

        Args:
            resolver: ``SecretResolver`` usado para resolver ``MODEL_PROVIDER``
                pelo pipe env -> Secrets Manager (fail-fast).
            timeout_s: timeout duro do enriquecimento, em segundos (padrão
                120s). Estouro → :class:`EnrichmentTimeoutError` (Req 6.6).
        """
        self._resolver = resolver
        self._timeout_s = timeout_s

    def enrich(self, draft: dict[str, Any]) -> AnnotatedDraft:
        """Produz o ``AnnotatedDraft`` a partir do ``Draft`` determinístico.

        Fluxo (nesta ordem, Req 9.1):

        1. Resolve ``MODEL_PROVIDER`` via ``SecretResolver`` **antes** de
           qualquer chamada/instanciação de ``agno``. Ausente/blank/fonte
           indisponível → ``MissingSecretError`` (~5s), nomeando só a env.
        2. Monta o Agent Agno (provider por env) com os guardrails do baseline +
           escopo mínimo (Req 9.5).
        3. Invoca o provider com timeout duro; estouro →
           ``EnrichmentTimeoutError`` (Req 6.6).
        4. Copia ``base_fields`` fielmente e anexa cada saída como
           :class:`Suggestion` marcada, sem sobrescrever (Req 7.3, 7.4, 7.6).

        Args:
            draft: Draft determinístico produzido pelo Static_Inspector.

        Returns:
            ``AnnotatedDraft`` com ``base_fields`` intactos e sugestões marcadas.

        Raises:
            MissingSecretError: se ``MODEL_PROVIDER`` estiver ausente/blank ou a
                fonte de segredos estiver indisponível (Req 9.2, 9.3). Nomeia só
                a env; nunca inclui o valor de qualquer segredo.
            EnrichmentTimeoutError: se o enriquecimento exceder ``timeout_s``
                (Req 6.6).
            ScopeRejectedError: se o guardrail de escopo rejeitar o conteúdo
                (Req 9.5).
            EnrichmentError: para outras falhas do enricher, sem ``AnnotatedDraft``
                parcial.
        """
        # 1) Fail-fast do provider ANTES de qualquer import/uso de agno (Req 9.1).
        #    MissingSecretError já nomeia SOMENTE a env — não capturamos para
        #    re-lançar de forma a esconder o nome (Req 9.2, 9.3).
        provider = self._resolve_provider()

        # base_fields é cópia FIEL e independente do Draft: o enricher nunca a
        # altera, remove ou reordena (Req 7.3).
        base_fields: dict[str, object] = copy.deepcopy(dict(draft))

        # 2+3) Invoca o provider sob timeout duro; agno é importado lazy dentro.
        suggestions = self._run_with_timeout(provider, base_fields)

        # 4) Draft intacto + sugestões marcadas como entradas separadas (Req 7.4).
        return AnnotatedDraft(base_fields=base_fields, suggestions=suggestions)

    # ------------------------------------------------------------------ #
    # Passos internos                                                     #
    # ------------------------------------------------------------------ #

    def _resolve_provider(self) -> str:
        """Resolve ``MODEL_PROVIDER`` por env (fail-fast), sem tocar em ``agno``.

        Returns:
            O identificador do provider (string não vazia).

        Raises:
            MissingSecretError: ausente/blank/fonte indisponível (Req 9.2, 9.3).
        """
        # required=True sem default: garante string não vazia ou MissingSecretError.
        provider = self._resolver.resolve(MODEL_PROVIDER_ENV, required=True)
        # required=True sem default nunca retorna None aqui.
        return provider  # type: ignore[return-value]

    def _run_with_timeout(
        self, provider: str, base_fields: dict[str, object]
    ) -> list[Suggestion]:
        """Executa a montagem+invocação do agente sob timeout duro (Req 6.6).

        Usa um worker isolado com deadline: se o enriquecimento não concluir
        dentro de ``timeout_s``, levanta :class:`EnrichmentTimeoutError` sem
        produzir sugestões parciais.
        """
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._enrich_via_agno, provider, base_fields)
            try:
                return future.result(timeout=self._timeout_s)
            except FuturesTimeoutError as exc:
                # Estouro do timeout duro → aborta sem AnnotatedDraft parcial.
                raise EnrichmentTimeoutError(
                    "Enriquecimento excedeu o tempo limite de "
                    f"{self._timeout_s:.0f}s e foi abortado; o Draft de entrada "
                    "permanece inalterado."
                ) from exc

    def _enrich_via_agno(
        self, provider: str, base_fields: dict[str, object]
    ) -> list[Suggestion]:
        """Monta o Agent Agno e coleta as sugestões (import de ``agno`` lazy).

        O import de ``agno`` acontece **aqui** — depois do fail-fast do provider
        — mantendo o módulo importável sem o framework e a fronteira de camadas
        intacta (tipos de ``agno`` nunca escapam deste método).

        Raises:
            ScopeRejectedError: se o guardrail de escopo rejeitar o conteúdo
                (Req 9.5).
            EnrichmentError: em falha de execução do agente, sem sugestões
                parciais.
        """
        try:
            agent = self._build_agent(provider)
        except EnrichmentError:
            raise
        except Exception as exc:  # falha ao montar o agente/guardrails
            raise EnrichmentError(
                "Falha ao inicializar o enriquecimento por LLM."
            ) from exc

        try:
            outputs = self._invoke_agent(agent, base_fields)
        except ScopeRejectedError:
            raise
        except Exception as exc:  # falha durante a invocação do provider
            raise EnrichmentError(
                "Falha durante a invocação do provider de LLM no enriquecimento."
            ) from exc

        return self._to_suggestions(outputs, base_fields)

    def _build_agent(self, provider: str) -> Any:
        """Instancia o Agent Agno com guardrails do baseline + escopo (Req 9.5).

        Import tardio de ``agno``; o objeto retornado é tratado como opaco
        (``Any``) para não vazar tipos do framework fora deste módulo.
        """
        from agno.agent import Agent  # import tardio — confinado a este módulo

        instructions = (
            "Você atua exclusivamente na descoberta de alvo de QA: sugerir "
            "'expected_domain' e casos candidatos de 'golden_set' para o alvo "
            "descrito no Draft. Não responda nada fora desse escopo."
        )
        return Agent(
            name="qa-target-enricher",
            model=self._build_model(provider),
            description="Enricher advisory da Fase 2 (descoberta de alvo de QA).",
            instructions=instructions,
            pre_hooks=self._build_guardrails(),
        )

    @staticmethod
    def _build_model(provider: str) -> Any:
        """Resolve o objeto de modelo do ``agno`` a partir do provider por env.

        O provider **nunca** é fixado no código: vem de ``MODEL_PROVIDER`` (Req
        9.1). Aceita o formato ``"<provider>:<model_id>"`` (ex.:
        ``"aws:claude-3-sonnet"``, ``"ollama:llama3.1"``, ``"gemini:gemini-2.0-flash"``)
        ou apenas ``"<provider>"`` (usa o modelo default do provider). Import
        tardio: o SDK de cada provider só é carregado quando ele é selecionado.

        Providers suportados:

        - ``aws``/``bedrock``: :class:`agno.models.aws.AwsBedrock` (credenciais AWS).
        - ``openai``: :class:`agno.models.openai.OpenAIChat` (``OPENAI_API_KEY``).
        - ``ollama``: :class:`agno.models.ollama.Ollama` — provider local servido
          pelo docker-compose (perfil ``llm``, porta 11434). O endpoint é lido de
          ``OLLAMA_HOST`` (default do cliente: ``http://localhost:11434``); dentro
          da rede do Compose use ``http://ollama:11434``. Sem custo/rede externa.
        - ``gemini``/``google``: :class:`agno.models.google.Gemini` — Gemini
          Developer API. A chave é lida de ``GOOGLE_API_KEY`` pelo próprio SDK.

        Cada SDK é dependência **opcional** (extras ``ollama``/``gemini``/``openai``
        no ``pyproject.toml``) e é importado pelo Agno de forma tardia. Se o SDK
        não estiver instalado, o import levanta ``ImportError``, convertido aqui
        em :class:`EnrichmentError` com uma mensagem acionável (sem stack trace),
        preservando o contrato de erro do enricher.

        Raises:
            EnrichmentError: provider não suportado, ou SDK do provider ausente.
        """
        raw = provider.strip()
        provider_key, _, model_id = raw.partition(":")
        provider_key = provider_key.strip().lower()
        model_id = model_id.strip()

        try:
            if provider_key in ("aws", "bedrock"):
                from agno.models.aws import AwsBedrock

                return AwsBedrock(id=model_id) if model_id else AwsBedrock()
            if provider_key == "openai":
                from agno.models.openai import OpenAIChat

                return OpenAIChat(id=model_id) if model_id else OpenAIChat()
            if provider_key == "ollama":
                from agno.models.ollama import Ollama

                # host=None: o cliente Ollama resolve OLLAMA_HOST do ambiente e,
                # na ausência, usa o default http://localhost:11434.
                return Ollama(id=model_id) if model_id else Ollama()
            if provider_key in ("gemini", "google"):
                from agno.models.google import Gemini

                # api_key=None: o SDK do Gemini resolve GOOGLE_API_KEY do ambiente.
                return Gemini(id=model_id) if model_id else Gemini()
        except ImportError as exc:
            # SDK do provider não instalado (extra opcional ausente). Mensagem
            # acionável, sem vazar o valor bruto do segredo nem stack trace.
            raise EnrichmentError(
                f"SDK do provider de LLM '{provider_key}' não está instalado. "
                f"Instale o extra correspondente (ex.: 'uv sync --extra {provider_key}')."
            ) from exc

        # Provider desconhecido: falha tipada sem vazar o valor bruto do segredo.
        raise EnrichmentError(
            f"Provider de LLM não suportado pelo enricher: '{provider_key}'. "
            "Configure 'MODEL_PROVIDER' com um provider suportado "
            "(aws, openai, ollama, gemini)."
        )

    @staticmethod
    def _build_guardrails() -> list[Any]:
        """Monta a stack mínima do baseline + guardrail de escopo (Req 9.5).

        Ordem: checks baratos/determinísticos primeiro (escopo, injeção, PII),
        provider externo (moderação) por último — falha cedo, gasta menos. A
        lista nunca é vazia (invariante do portfólio). Import tardio de ``agno``.

        O ``OpenAIModerationGuardrail`` chama a API de moderação da OpenAI e
        exige ``OPENAI_API_KEY`` — **independente** do provider do modelo. Para
        não quebrar a premissa de rodar com providers locais (ex.: Ollama do
        docker-compose) sem rede externa nem credencial da OpenAI, a moderação só
        entra na stack quando a chave está presente. Os demais guardrails
        (escopo, injeção, PII) são locais/determinísticos e ficam SEMPRE ativos,
        preservando o invariante de "≥ 1 guardrail".
        """
        from agno.guardrails import (
            OpenAIModerationGuardrail,
            PIIDetectionGuardrail,
            PromptInjectionGuardrail,
        )

        guardrails: list[Any] = [
            _build_scope_guardrail(),  # customizado, determinístico — primeiro
            PromptInjectionGuardrail(),
            PIIDetectionGuardrail(),
        ]
        # Moderação (provider externo) só quando há credencial da OpenAI. Sem a
        # chave, a chamada de moderação falharia com "Missing credentials" mesmo
        # usando um modelo local — por isso é omitida, não forçada.
        openai_api_key = os.environ.get(OPENAI_API_KEY_ENV)
        if openai_api_key and openai_api_key.strip():
            guardrails.append(OpenAIModerationGuardrail())  # por último — externo

        if not guardrails:  # invariante do portfólio: sempre >= 1 guardrail
            raise EnrichmentError(
                "Nenhum guardrail configurado; o enricher exige ao menos um."
            )
        return guardrails

    def _invoke_agent(
        self, agent: Any, base_fields: dict[str, object]
    ) -> dict[str, object]:
        """Invoca o agente e normaliza a saída em um mapa de sugestões.

        Trata bloqueio de guardrail (``RunStatus.error``) como
        :class:`ScopeRejectedError` (Req 9.5). A saída estruturada esperada é um
        mapa com ``expected_domain`` (str) e/ou ``golden_set`` (lista de casos).
        """
        from agno.run.base import RunStatus

        prompt = self._build_prompt(base_fields)
        response = agent.run(prompt)

        if getattr(response, "status", None) == RunStatus.error:
            # Guardrail (escopo/injeção/PII/moderação) rejeitou o conteúdo.
            raise ScopeRejectedError(
                "Conteúdo fora do escopo de descoberta de alvo de QA; "
                "a chamada foi rejeitada sem aplicar sugestões."
            )
        return self._parse_response(getattr(response, "content", None))

    @staticmethod
    def _build_prompt(base_fields: dict[str, object]) -> str:
        """Monta o prompt de sugestão a partir do Draft (sem segredos)."""
        target = base_fields.get("target", {})
        return (
            "Analise o alvo de QA a seguir e sugira 'expected_domain' e casos "
            "candidatos de 'golden_set'. Alvo: "
            f"{target!r}."
        )

    @staticmethod
    def _parse_response(content: object) -> dict[str, object]:
        """Normaliza o ``content`` do agente em ``{expected_domain, golden_set}``.

        Aceita um mapping direto; conteúdos em outro formato resultam em um mapa
        vazio (nenhuma sugestão), preservando a invariante de não-sobrescrita.
        """
        if isinstance(content, dict):
            out: dict[str, object] = {}
            if "expected_domain" in content:
                out["expected_domain"] = content["expected_domain"]
            if "golden_set" in content:
                out["golden_set"] = content["golden_set"]
            return out
        return {}

    @staticmethod
    def _to_suggestions(
        outputs: dict[str, object], base_fields: dict[str, object]
    ) -> list[Suggestion]:
        """Converte a saída do LLM em :class:`Suggestion` marcadas (Req 7).

        - ``expected_domain`` → uma ``Suggestion`` com ``origin="sugestão"``
          (Req 7.1).
        - cada item de ``golden_set`` → uma ``Suggestion`` com
          ``origin="candidato"`` (Req 7.2).

        Todas nascem com ``state="pendente"`` (default do modelo). O valor
        pré-existente no Draft **não** é sobrescrito: a sugestão entra como
        entrada separada mesmo quando o campo já tem valor não vazio (Req 7.4,
        7.6).
        """
        suggestions: list[Suggestion] = []

        expected_domain = outputs.get("expected_domain")
        if expected_domain is not None:
            suggestions.append(
                Suggestion(
                    field="expected_domain",
                    value=expected_domain,
                    origin="sugestão",
                )
            )

        golden_set = outputs.get("golden_set")
        if isinstance(golden_set, list):
            for case in golden_set:
                suggestions.append(
                    Suggestion(
                        field="golden_set",
                        value=case,
                        origin="candidato",
                    )
                )
        return suggestions


def _build_scope_guardrail() -> Any:
    """Constrói o guardrail de escopo mínimo do enricher (Req 9.5).

    A classe estende ``agno.guardrails.BaseGuardrail`` — um tipo do ``agno``.
    Para preservar o import **lazy** (o módulo importa sem o framework e o
    fail-fast do provider roda antes de qualquer import de ``agno``), a classe é
    definida **dentro** desta fábrica, importando ``agno`` só quando um agente é
    de fato montado. Os tipos do framework ficam confinados a este escopo.

    O guardrail rejeita conteúdo fora do escopo "descoberta de alvo de QA"
    (sugerir ``expected_domain``/``golden_set``) com uma mensagem neutra, sem
    vazar detalhes internos. Reforça — não substitui — as ``instructions`` do
    agente.
    """
    import re

    from agno.exceptions import CheckTrigger, InputCheckError
    from agno.guardrails import BaseGuardrail

    class _ScopeGuardrail(BaseGuardrail):  # type: ignore[misc]
        """Bloqueia entradas fora do escopo de descoberta de alvo de QA."""

        _keywords: tuple[str, ...] = _SCOPE_KEYWORDS

        def _is_in_scope(self, text: str) -> bool:
            low = text.lower()
            return any(re.search(rf"\b{re.escape(k)}\b", low) for k in self._keywords)

        def _validate(self, run_input: Any) -> None:
            content = run_input.input_content_string()
            if (
                isinstance(content, str)
                and content.strip()
                and not self._is_in_scope(content)
            ):
                raise InputCheckError(
                    "Conteúdo fora do escopo de descoberta de alvo de QA; "
                    "o enricher só sugere 'expected_domain' e 'golden_set'.",
                    check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                )

        def check(self, run_input: Any) -> None:
            self._validate(run_input)

        async def async_check(self, run_input: Any) -> None:
            self._validate(run_input)

    return _ScopeGuardrail()
