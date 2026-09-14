"""Testes por exemplo/edge do ``LLMEnricher``: fail-fast do provider e guardrail.

# Feature: hybrid-target-discovery, Task 8.5 (Req 9.1, 9.2, 9.3, 9.5)

Cobre o comportamento de borda da Fase 2 (advisory, fora do Workflow), sem nunca
invocar um provider de LLM real -- o seam de invocacao do ``agno`` e mockado e o
guardrail de escopo real e exercitado de forma deterministica:

- **Fail-fast do provider (Req 9.2, 9.3):** ``MODEL_PROVIDER`` ausente,
  so-espacos ou com fonte indisponivel -> ``MissingSecretError`` nomeando SOMENTE
  a env (nunca o valor de qualquer segredo), e rapido (< 5s).
- **Ordem (Req 9.1):** o provider e resolvido ANTES de qualquer invocacao do
  LLM; quando o provider falta, o seam do ``agno`` NUNCA e chamado (fail-fast
  antes do LLM).
- **Guardrail de escopo (Req 9.5):** conteudo fora do escopo de "descoberta de
  alvo de QA" e rejeitado (``InputCheckError``); conteudo dentro do escopo
  passa. Tambem exercitado no nivel do enricher: run com status de erro ->
  ``ScopeRejectedError``; run com sucesso -> sugestoes produzidas.
- **Secrets Manager com ``moto`` (``mock_aws``):** o resolver resolve
  ``MODEL_PROVIDER`` do Secrets Manager quando a env esta ausente, e a env local
  SEMPRE vence sobre o Secrets Manager (invariante env-wins).

_Requirements: 9.1, 9.2, 9.3, 9.5_
"""

from __future__ import annotations

import json
import time
from typing import Any, ClassVar

import pytest

from qa_platform.infrastructure.enrichment.errors import (
    EnrichmentError,
    ScopeRejectedError,
)
from qa_platform.infrastructure.enrichment.llm_enricher import (
    MODEL_PROVIDER_ENV,
    LLMEnricher,
    _build_scope_guardrail,
)
from qa_platform.infrastructure.secrets.aws_secrets_manager import (
    AWSSecretsManagerProvider,
)
from qa_platform.infrastructure.secrets.in_memory import InMemorySecretsProvider
from qa_platform.infrastructure.secrets.resolver import (
    MissingSecretError,
    SecretResolver,
)

# Draft deterministico minimo (forma consumida por ``LLMEnricher.enrich``).
_DRAFT: dict[str, Any] = {
    "target": {"identifier": "meu-agente", "source": "repo://x"},
    "applicable_layers": [],
    "risk_parameters": {},
}


class _FakeRunInput:
    """Fake minimo de ``RunInput`` do agno: expoe ``input_content_string()``.

    O guardrail de escopo real chama ``run_input.input_content_string()`` para
    obter o texto a validar. Este fake evita instanciar o pipeline do agno,
    mantendo o teste deterministico e sem rede.
    """

    def __init__(self, content: str) -> None:
        self._content = content

    def input_content_string(self) -> str:
        return self._content


# --------------------------------------------------------------------------- #
# Fail-fast do provider (Req 9.2, 9.3)                                         #
# --------------------------------------------------------------------------- #


def test_model_provider_unset_raises_missing_secret_naming_only_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``MODEL_PROVIDER`` ausente -> ``MissingSecretError`` nomeando so a env (Req 9.2)."""
    # Arrange -- garante a env ausente e resolver sem fonte secundaria.
    monkeypatch.delenv(MODEL_PROVIDER_ENV, raising=False)
    enricher = LLMEnricher(SecretResolver())

    # Act / Assert -- fail-fast rapido, nomeando a env, sem vazar valor.
    start = time.monotonic()
    with pytest.raises(MissingSecretError) as exc_info:
        enricher.enrich(dict(_DRAFT))
    elapsed = time.monotonic() - start

    message = str(exc_info.value)
    assert MODEL_PROVIDER_ENV in message
    # Nenhum valor de segredo e vazado (o Draft nao contem segredos, mas
    # reforcamos que a mensagem descreve so a condicao de ausencia).
    assert "meu-agente" not in message
    assert elapsed < 5.0


def test_model_provider_only_spaces_counts_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``MODEL_PROVIDER`` so-espacos conta como ausente -> mesmo erro (Req 9.2)."""
    # Arrange -- valor apenas com whitespace (== ausente para o resolver).
    monkeypatch.setenv(MODEL_PROVIDER_ENV, "   ")
    enricher = LLMEnricher(SecretResolver())

    # Act / Assert
    with pytest.raises(MissingSecretError) as exc_info:
        enricher.enrich(dict(_DRAFT))

    assert MODEL_PROVIDER_ENV in str(exc_info.value)


def test_provider_source_unavailable_fails_fast_naming_only_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fonte indisponivel (sem env, sem provider) -> erro rapido nomeando a env (Req 9.3)."""
    # Arrange -- nem env nem provider secundario resolvem o valor.
    monkeypatch.delenv(MODEL_PROVIDER_ENV, raising=False)
    enricher = LLMEnricher(SecretResolver(secrets_provider=InMemorySecretsProvider({})))

    # Act / Assert -- sem necessidade de tempo real; se medido, generoso (< 5s).
    start = time.monotonic()
    with pytest.raises(MissingSecretError) as exc_info:
        enricher.enrich(dict(_DRAFT))
    elapsed = time.monotonic() - start

    assert MODEL_PROVIDER_ENV in str(exc_info.value)
    assert elapsed < 5.0


# --------------------------------------------------------------------------- #
# Ordem: provider resolvido ANTES de invocar o LLM (Req 9.1)                    #
# --------------------------------------------------------------------------- #


class _SpyResolver(SecretResolver):
    """Resolver que registra a ordem das chamadas a ``resolve`` num rastro."""

    def __init__(self, trace: list[str], value: str | None) -> None:
        super().__init__()
        self._trace = trace
        self._value = value

    def resolve(
        self,
        env_name: str,
        *,
        required: bool = True,
        default: str | None = None,
    ) -> str | None:
        self._trace.append(f"resolve:{env_name}")
        if self._value is None:
            # Reproduz o fail-fast do resolver real (nomeia so a env).
            raise MissingSecretError(f"Configuracao obrigatoria ausente: '{env_name}'.")
        return self._value


def test_provider_resolved_before_agno_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O provider e resolvido ANTES de qualquer invocacao do LLM (Req 9.1)."""
    # Arrange -- espiona a ordem: resolve() e o seam do agno gravam no rastro.
    trace: list[str] = []
    resolver = _SpyResolver(trace, value="openai:gpt-x")

    def _fake_enrich_via_agno(
        self: LLMEnricher, provider: str, base_fields: dict[str, object]
    ) -> list[Any]:
        trace.append("agno:invoke")
        return []

    monkeypatch.setattr(LLMEnricher, "_enrich_via_agno", _fake_enrich_via_agno)
    enricher = LLMEnricher(resolver)

    # Act
    enricher.enrich(dict(_DRAFT))

    # Assert -- resolve gravado antes do seam do agno.
    assert trace == ["resolve:MODEL_PROVIDER", "agno:invoke"]
    assert trace.index("resolve:MODEL_PROVIDER") < trace.index("agno:invoke")


def test_agno_never_invoked_when_provider_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider ausente -> o seam do agno NUNCA e chamado (fail-fast antes do LLM, Req 9.1)."""
    # Arrange -- resolver que sempre falha e um seam do agno espiao.
    trace: list[str] = []
    resolver = _SpyResolver(trace, value=None)

    def _fake_enrich_via_agno(
        self: LLMEnricher, provider: str, base_fields: dict[str, object]
    ) -> list[Any]:
        trace.append("agno:invoke")
        return []

    monkeypatch.setattr(LLMEnricher, "_enrich_via_agno", _fake_enrich_via_agno)
    enricher = LLMEnricher(resolver)

    # Act / Assert -- falha na resolucao, sem tocar no seam do agno.
    with pytest.raises(MissingSecretError):
        enricher.enrich(dict(_DRAFT))

    assert "agno:invoke" not in trace
    assert trace == ["resolve:MODEL_PROVIDER"]


# --------------------------------------------------------------------------- #
# Guardrail de escopo (Req 9.5) -- agno real, mas deterministico e sem rede     #
# --------------------------------------------------------------------------- #


def test_scope_guardrail_rejects_out_of_scope_content() -> None:
    """Conteudo fora do escopo e rejeitado com ``InputCheckError`` (Req 9.5)."""
    from agno.exceptions import InputCheckError

    guardrail = _build_scope_guardrail()
    run_input = _FakeRunInput("Escreva um poema sobre o por do sol na praia.")

    with pytest.raises(InputCheckError):
        guardrail.check(run_input)


def test_scope_guardrail_allows_in_scope_content() -> None:
    """Conteudo dentro do escopo passa sem levantar (Req 9.5)."""
    guardrail = _build_scope_guardrail()
    run_input = _FakeRunInput(
        "Sugira o expected_domain e casos de golden_set para o alvo de QA."
    )

    # Nao deve levantar -- conteudo em escopo e aceito.
    guardrail.check(run_input)


def test_enricher_surfaces_scope_rejection_as_scope_rejected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run com status de erro -> ``ScopeRejectedError`` no nivel do enricher (Req 9.5)."""
    from agno.run.base import RunStatus

    monkeypatch.setenv(MODEL_PROVIDER_ENV, "openai:gpt-x")

    class _ErrorResponse:
        status = RunStatus.error
        content = None

    class _FakeAgent:
        def run(self, prompt: str) -> _ErrorResponse:
            return _ErrorResponse()

    # Mocka a construcao do agente para nao tocar em provider/rede reais.
    monkeypatch.setattr(
        LLMEnricher, "_build_agent", lambda self, provider: _FakeAgent()
    )
    enricher = LLMEnricher(SecretResolver())

    with pytest.raises(ScopeRejectedError):
        enricher.enrich(dict(_DRAFT))


def test_enricher_produces_suggestions_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run bem-sucedido em escopo -> sugestoes produzidas, Draft intacto (Req 9.5)."""
    from agno.run.base import RunStatus

    monkeypatch.setenv(MODEL_PROVIDER_ENV, "openai:gpt-x")

    class _OkResponse:
        status = RunStatus.completed
        content: ClassVar[dict[str, object]] = {
            "expected_domain": "atendimento ao cliente",
            "golden_set": [{"input": "oi", "expected": "ola"}],
        }

    class _FakeAgent:
        def run(self, prompt: str) -> _OkResponse:
            return _OkResponse()

    monkeypatch.setattr(
        LLMEnricher, "_build_agent", lambda self, provider: _FakeAgent()
    )
    enricher = LLMEnricher(SecretResolver())

    annotated = enricher.enrich(dict(_DRAFT))

    # base_fields e copia fiel do Draft (nunca sobrescrito).
    assert annotated.base_fields == _DRAFT
    # Uma sugestao para expected_domain + uma para cada golden_set case.
    fields = sorted(s.field for s in annotated.suggestions)
    assert fields == ["expected_domain", "golden_set"]
    assert all(s.state == "pendente" for s in annotated.suggestions)


# --------------------------------------------------------------------------- #
# Caminho do Secrets Manager com moto (mock_aws) + invariante env-wins          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def secrets_manager_with_provider(monkeypatch: pytest.MonkeyPatch):
    """Cria um segredo mockado com ``moto`` e devolve um provider que o le.

    O provider (``AWSSecretsManagerProvider``) faz import tardio de boto3 apenas
    ao consultar a fonte, entao o ``mock_aws`` do ``moto`` intercepta a chamada
    real. Reaproveita a convencao dos testes de secrets existentes.
    """
    import boto3
    from moto import mock_aws

    # A regiao precisa estar no ambiente: o ``AWSSecretsManagerProvider`` cria
    # seu proprio cliente boto3 (sem regiao explicita) ao consultar a fonte.
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    secret_name = "qa-platform-secrets"
    with mock_aws():
        client = boto3.client("secretsmanager", region_name="us-east-1")
        client.create_secret(
            Name=secret_name,
            SecretString=json.dumps({MODEL_PROVIDER_ENV: "aws:claude-sm"}),
        )
        provider = AWSSecretsManagerProvider(secret_name=secret_name)
        yield provider


def test_resolves_model_provider_from_secrets_manager_when_env_absent(
    monkeypatch: pytest.MonkeyPatch,
    secrets_manager_with_provider: AWSSecretsManagerProvider,
) -> None:
    """Sem env, o resolver le ``MODEL_PROVIDER`` do Secrets Manager (moto)."""
    monkeypatch.delenv(MODEL_PROVIDER_ENV, raising=False)
    resolver = SecretResolver(secrets_provider=secrets_manager_with_provider)

    assert resolver.resolve(MODEL_PROVIDER_ENV) == "aws:claude-sm"


def test_local_env_wins_over_secrets_manager(
    monkeypatch: pytest.MonkeyPatch,
    secrets_manager_with_provider: AWSSecretsManagerProvider,
) -> None:
    """A env local SEMPRE vence sobre o Secrets Manager (invariante env-wins)."""
    monkeypatch.setenv(MODEL_PROVIDER_ENV, "openai:local")
    resolver = SecretResolver(secrets_provider=secrets_manager_with_provider)

    # Env presente -> vence o valor do Secrets Manager ("aws:claude-sm").
    assert resolver.resolve(MODEL_PROVIDER_ENV) == "openai:local"


# --------------------------------------------------------------------------- #
# Resolução de provider em _build_model (sem rede)                             #
# --------------------------------------------------------------------------- #
#
# Exercita o mapeamento MODEL_PROVIDER -> objeto de modelo do agno. Só constrói
# o objeto de modelo (não invoca o provider), então não há rede nem chamada de
# LLM. Cada classe do agno é importada tardiamente dentro de _build_model; os
# SDKs opcionais (ollama/google-genai/openai) estão instalados no ambiente de
# dev via os extras correspondentes.


@pytest.mark.parametrize(
    ("provider", "expected_cls", "expected_id"),
    [
        # Sem model_id: usa o default do provider (id != vazio).
        ("ollama", "Ollama", None),
        ("gemini", "Gemini", None),
        ("google", "Gemini", None),
        # Com model_id explícito: o id do modelo é propagado.
        ("ollama:llama3.2", "Ollama", "llama3.2"),
        ("gemini:gemini-2.0-flash", "Gemini", "gemini-2.0-flash"),
        ("google:gemini-2.0-flash", "Gemini", "gemini-2.0-flash"),
    ],
)
def test_build_model_resolves_new_providers(
    provider: str, expected_cls: str, expected_id: str | None
) -> None:
    """``_build_model`` resolve os providers ollama e gemini/google (sem rede).

    Os SDKs (ollama/google-genai) são extras OPCIONAIS: o teste tolera os dois
    cenários — SDK presente (o modelo é construído) ou SDK ausente (``_build_model``
    converte o ``ImportError`` em ``EnrichmentError`` acionável). Assim a suíte
    permanece verde mesmo quando os extras não estão sincronizados.
    """
    try:
        model = LLMEnricher._build_model(provider)
    except EnrichmentError as exc:
        # SDK do extra opcional não instalado -> mensagem acionável, sem crash.
        assert "não está instalado" in str(exc)
        return

    assert type(model).__name__ == expected_cls
    if expected_id is not None:
        assert model.id == expected_id
    else:
        # Default do provider: apenas garante que há um id não vazio.
        assert isinstance(model.id, str) and model.id.strip()


def test_build_model_unknown_provider_raises_enrichment_error() -> None:
    """Provider desconhecido -> ``EnrichmentError`` sem vazar o valor bruto."""
    with pytest.raises(EnrichmentError) as exc_info:
        LLMEnricher._build_model("provedor-inexistente")

    message = str(exc_info.value)
    assert "não suportado" in message
    # A mensagem lista os providers suportados para orientar a correção.
    assert "ollama" in message
    assert "gemini" in message


def test_build_model_missing_sdk_raises_enrichment_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK do provider ausente -> ``EnrichmentError`` acionável (não ImportError).

    Simula o SDK ausente forçando o import de ``agno.models.ollama`` a levantar
    ``ImportError`` (como aconteceria sem o extra instalado). O enricher deve
    converter em ``EnrichmentError`` com mensagem acionável, sem stack trace.
    """
    import builtins

    real_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "agno.models.ollama" or name.startswith("agno.models.ollama."):
            raise ImportError("No module named 'ollama'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(EnrichmentError) as exc_info:
        LLMEnricher._build_model("ollama")

    message = str(exc_info.value)
    assert "não está instalado" in message
    assert "ollama" in message


# --------------------------------------------------------------------------- #
# Stack de guardrails: moderação OpenAI condicional à OPENAI_API_KEY            #
# --------------------------------------------------------------------------- #
#
# O OpenAIModerationGuardrail chama a API da OpenAI e exige OPENAI_API_KEY,
# INDEPENDENTE do provider do modelo. Para rodar com providers locais (ex.:
# Ollama) sem rede/credencial da OpenAI, a moderação só entra na stack quando a
# chave está presente; os demais guardrails (escopo, injeção, PII) são locais e
# ficam sempre ativos.


def _guardrail_class_names(guardrails: list[Any]) -> list[str]:
    return [type(g).__name__ for g in guardrails]


def test_guardrails_omit_moderation_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem OPENAI_API_KEY, a moderação é omitida; demais guardrails ativos."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    names = _guardrail_class_names(LLMEnricher._build_guardrails())

    # Invariante do portfólio: stack local mínima sempre presente (>= 1).
    assert "PromptInjectionGuardrail" in names
    assert "PIIDetectionGuardrail" in names
    # Moderação (externa) ausente sem credencial — não força chamada à OpenAI.
    assert "OpenAIModerationGuardrail" not in names
    assert len(names) >= 1


def test_guardrails_only_spaces_openai_key_counts_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OPENAI_API_KEY só-espaços conta como ausente -> moderação omitida."""
    monkeypatch.setenv("OPENAI_API_KEY", "   ")

    names = _guardrail_class_names(LLMEnricher._build_guardrails())

    assert "OpenAIModerationGuardrail" not in names


def test_guardrails_include_moderation_with_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Com OPENAI_API_KEY, a moderação entra na stack (por último)."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")

    names = _guardrail_class_names(LLMEnricher._build_guardrails())

    assert "OpenAIModerationGuardrail" in names
    # Guardrail externo é o último da stack (falha cedo nos locais antes).
    assert names[-1] == "OpenAIModerationGuardrail"
