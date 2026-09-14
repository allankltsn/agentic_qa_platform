"""Testes por exemplo — gate de promoção humana e isolamento da Fase 1.

Cobre duas garantias distintas da Descoberta Híbrida de Alvo (ADR-004),
ambas por exemplo (não por propriedade):

1. **Gate de promoção humana (Requisitos 8.3, 8.4):** um Draft/``Annotated_Draft``
   ainda **não promovido** — que preserva a sentinela ``PENDING`` onde o schema
   a detecta (o ``weight`` numérico de ``risk_parameters``) — é **bloqueado**
   ao ser submetido ao Workflow. O gate é a validação de schema executada
   **antes** do primeiro step do orquestrador (``run_orchestration`` chama
   ``validate_manifest`` antes de qualquer step; ``parse_manifest_text`` valida
   igualmente antes de produzir o VO). O bloqueio se materializa como
   ``InvalidManifestError`` nomeando **cada** campo pendente, sem promover o
   Draft ao fluxo. Um ``expected_domain``/``golden_set`` sugerido permanece
   candidato não confirmado enquanto não estiver no ``qa-target.yaml`` promovido:
   o próprio Draft de ``discover_target`` **não** carrega esses campos e ainda
   tem ``version``/``weight`` pendentes.

2. **Static_Inspector não toca segredos (Requisito 9.4):** ``discover_target``
   (Fase 1) é isento de resolução de segredos. Espionamos que
   ``SecretResolver.resolve`` **não** é chamado e que ``MODEL_PROVIDER`` **não**
   é lido do ambiente durante a chamada. Reforçamos com uma inspeção estrutural
   de que o módulo ``target_discovery`` sequer importa ``SecretResolver`` ou
   referencia ``MODEL_PROVIDER`` no seu código-fonte.

O mecanismo de "submeter ao Workflow" usado no gate é o próprio caminho de
promoção do produto: para entrar no ``Orchestrator_Workflow`` é preciso um
``QATargetManifest`` válido, e obtê-lo (via ``parse_manifest_text``) — ou acionar
``run_orchestration`` — passa pela validação de schema que rejeita pendências.
A Fase 1 não toca AWS por design, então nenhum caminho ``moto``/``mock_aws`` é
necessário aqui (é justamente o ponto do teste de isolamento).

# Feature: hybrid-target-discovery
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from qa_platform.domain.exceptions import InvalidManifestError
from qa_platform.infrastructure.manifest import target_discovery
from qa_platform.infrastructure.manifest.parser import parse_manifest_text
from qa_platform.infrastructure.manifest.target_discovery import (
    PENDING,
    discover_target,
    has_pending_fields,
    is_pending,
)
from qa_platform.infrastructure.secrets.resolver import SecretResolver

_MODEL_PROVIDER_ENV = "MODEL_PROVIDER"


def _synthetic_target(tmp_path: Path) -> str:
    """Cria um alvo sintético mínimo e resolvível no filesystem local.

    ``discover_target`` compõe ``repo_reader.read_target``, que lê o filesystem
    local. Um único arquivo ``.py`` elegível basta para produzir um Draft.
    """
    target = tmp_path / "agent.py"
    target.write_text(
        "from agno.agent import Agent\n\nSYSTEM_PROMPT = 'ajude o usuario'\n",
        encoding="utf-8",
    )
    return str(target)


# --------------------------------------------------------------------------- #
# 1) Gate de promoção humana — Draft não promovido é BLOQUEADO (Req 8.3, 8.4)
# --------------------------------------------------------------------------- #


def test_draft_nao_promovido_ainda_contem_campos_pendentes(tmp_path: Path) -> None:
    """O Draft de ``discover_target`` nasce não promovido (Req 8.3).

    Um Draft recém-descoberto preserva ``PENDING`` em ``target.version`` e em
    cada ``risk_parameters.<layer>.weight``, o que o distingue de um manifesto
    promovido. Também **não** carrega ``expected_domain``/``golden_set``: esses
    permanecem candidatos não confirmados até serem promovidos ao
    ``qa-target.yaml``.
    """
    # Arrange / Act
    draft = discover_target(_synthetic_target(tmp_path))

    # Assert — pendências presentes onde o schema as detecta e onde não.
    assert has_pending_fields(draft)
    assert is_pending(draft["target"]["version"])
    for params in draft["risk_parameters"].values():
        assert is_pending(params["weight"])

    # Candidatos sugeridos NÃO entram no Draft não promovido.
    assert "expected_domain" not in draft
    assert "golden_set" not in draft


def test_submeter_draft_nao_promovido_ao_workflow_e_bloqueado_nomeando_pendencias(
    tmp_path: Path,
) -> None:
    """Draft não promovido submetido ao Workflow → bloqueio nomeando campos (Req 8.4).

    O gate que antecede o ``Orchestrator_Workflow`` é a validação de schema
    (``run_orchestration`` a executa antes do 1º step; ``parse_manifest_text``
    a executa antes de produzir o VO). Serializamos o Draft para YAML — como um
    submissor faria — e submetemos ao parser: a promoção é **negada** com
    ``InvalidManifestError`` nomeando **cada** ``weight`` pendente. Nenhum VO
    (entrada no fluxo) é produzido.
    """
    # Arrange — Draft não promovido, serializado como um submissor faria.
    draft = discover_target(_synthetic_target(tmp_path))
    manifest_text = yaml.safe_dump(draft, allow_unicode=True)

    # Act / Assert — o gate rejeita antes de qualquer entrada no Workflow.
    with pytest.raises(InvalidManifestError) as exc_info:
        parse_manifest_text(manifest_text)

    invalid_fields = exc_info.value.invalid_fields
    # Cada ``weight`` pendente é nomeado no erro agregado (nenhum silenciado).
    expected_pending = {
        f"risk_parameters.{layer}.weight" for layer in draft["risk_parameters"]
    }
    assert expected_pending, "o Draft deve ter ao menos uma camada aplicável"
    for field_path in expected_pending:
        assert field_path in invalid_fields
        assert (
            "PENDING" not in invalid_fields[field_path]
        )  # nomeia o campo, não o valor


def test_expected_domain_sugerido_permanece_candidato_ate_promovido() -> None:
    """Valor sugerido de ``expected_domain`` só vale quando promovido (Req 8.3).

    Enquanto o ``weight`` seguir ``PENDING`` (Draft não promovido), o manifesto
    é bloqueado mesmo que um ``expected_domain`` sugerido esteja presente — a
    sugestão não promove o Draft por si só. Uma vez promovido (pendências
    substituídas por valores válidos), o mesmo manifesto passa e o
    ``expected_domain`` promovido é honrado pelo parser.
    """
    # Arrange — manifesto com sugestão, mas ainda com ``weight`` pendente.
    not_promoted = {
        "target": {"ref": "artifact://x", "version": "1.0.0"},
        "applicable_layers": ["ai"],
        "risk_parameters": {"ai": {"weight": PENDING}},
        "expected_domain": "atendimento ao cliente",
    }

    # Act / Assert — sugestão não promove: gate ainda bloqueia nomeando o campo.
    with pytest.raises(InvalidManifestError) as exc_info:
        parse_manifest_text(yaml.safe_dump(not_promoted, allow_unicode=True))
    assert "risk_parameters.ai.weight" in exc_info.value.invalid_fields

    # Arrange — mesmo manifesto, agora PROMOVIDO (pendência resolvida).
    promoted = dict(not_promoted)
    promoted["risk_parameters"] = {"ai": {"weight": 1.0}}

    # Act
    manifest = parse_manifest_text(yaml.safe_dump(promoted, allow_unicode=True))

    # Assert — promovido passa e o candidato confirmado é honrado.
    assert manifest.expected_domain == "atendimento ao cliente"


# --------------------------------------------------------------------------- #
# 2) Static_Inspector não toca SecretResolver nem MODEL_PROVIDER (Req 9.4)
# --------------------------------------------------------------------------- #


def test_discover_target_nao_chama_secret_resolver_resolve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``discover_target`` não invoca ``SecretResolver.resolve`` (Req 9.4).

    Espionamos ``SecretResolver.resolve`` com uma armadilha que registra
    qualquer chamada. Como a Fase 1 é isenta de resolução de segredos, a
    contagem de invocações permanece em zero durante ``discover_target``.
    """
    # Arrange — espião de resolução de segredos.
    resolve_calls: list[str] = []

    def _spy_resolve(
        self: SecretResolver,
        env_name: str,
        *,
        required: bool = True,
        default: str | None = None,
    ) -> str | None:
        resolve_calls.append(env_name)
        raise AssertionError(
            "Fase 1 invocou SecretResolver.resolve — resolução de segredo "
            "proibida no Static_Inspector (Req 9.4)."
        )

    monkeypatch.setattr(SecretResolver, "resolve", _spy_resolve)

    # Act — a chamada completa não deve disparar a armadilha.
    draft = discover_target(_synthetic_target(tmp_path))

    # Assert — Draft produzido sem nenhuma resolução de segredo.
    assert isinstance(draft, dict)
    assert resolve_calls == []


def test_discover_target_nao_le_model_provider_do_ambiente(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``discover_target`` não lê ``MODEL_PROVIDER`` do ambiente (Req 9.4).

    Espionamos ``os.environ.get`` para registrar qualquer leitura de
    ``MODEL_PROVIDER``. A Fase 1 não consulta o provider de modelo, então a env
    nunca é lida — mesmo estando definida no ambiente (o que provaria leitura,
    não ausência).
    """
    # Arrange — define a env (se fosse lida, apareceria no espião) e espiona get.
    monkeypatch.setenv(_MODEL_PROVIDER_ENV, "sentinela-nao-deve-ser-lida")

    read_env_names: list[str] = []
    real_get = os.environ.get

    def _spy_get(key: str, default: Any = None) -> Any:  # type: ignore[override]
        read_env_names.append(key)
        return real_get(key, default)

    monkeypatch.setattr(os.environ, "get", _spy_get)

    # Act
    draft = discover_target(_synthetic_target(tmp_path))

    # Assert — Draft produzido e MODEL_PROVIDER jamais lido.
    assert isinstance(draft, dict)
    assert _MODEL_PROVIDER_ENV not in read_env_names


def test_target_discovery_module_nao_referencia_secret_nem_model_provider() -> None:
    """Inspeção estrutural: Fase 1 é isenta de resolução de segredos (Req 9.4).

    O módulo ``target_discovery`` não deve importar ``SecretResolver`` nem
    referenciar ``MODEL_PROVIDER`` no seu código-fonte — reforço estático de que
    a Fase 1 não resolve segredos, independente do caminho de execução.
    """
    source = Path(target_discovery.__file__).read_text(encoding="utf-8")

    assert "SecretResolver" not in source
    assert _MODEL_PROVIDER_ENV not in source
    # Também não importa o módulo de segredos.
    assert "qa_platform.infrastructure.secrets" not in source
