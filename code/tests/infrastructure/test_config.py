"""Testes por exemplo da infraestrutura de configuração/segredos.

Este arquivo é compartilhado entre a parte de **secrets** (SecretResolver +
adapter AWS) e, futuramente, a parte de **Settings/load_settings**. As classes
abaixo cobrem exclusivamente a porção de secrets (Tarefa 4.5): os três ramos do
pipe de fallback do ``SecretResolver`` e a importabilidade do adapter AWS sem o
boto3 instalado (import tardio). Mantidas em classes de escopo claro para
coexistir com os testes de ``load_settings`` (Tarefa 5.1) sem colisão.

_Requirements: 7.1, 7.2_
"""

from __future__ import annotations

import builtins
import importlib
import sys

import pytest

from qa_platform.infrastructure.secrets.in_memory import InMemorySecretsProvider
from qa_platform.infrastructure.secrets.resolver import (
    MissingSecretError,
    SecretResolver,
)


class TestSecretResolverFallbackPipe:
    """Os três ramos do pipe de fallback ``env -> Secrets Manager`` (Req 7.1, 7.2)."""

    def test_env_presente_vence_sobre_o_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quando a env está presente, ela vence o valor do provider (Req 7.1)."""
        monkeypatch.setenv("MY_SECRET", "valor-da-env")
        provider = InMemorySecretsProvider({"MY_SECRET": "valor-do-provider"})
        resolver = SecretResolver(secrets_provider=provider)

        assert resolver.resolve("MY_SECRET") == "valor-da-env"

    def test_valor_somente_no_provider_e_retornado_quando_env_ausente(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sem env, o valor vem do provider (Secrets Manager) (Req 7.1)."""
        monkeypatch.delenv("MY_SECRET", raising=False)
        provider = InMemorySecretsProvider({"MY_SECRET": "valor-do-provider"})
        resolver = SecretResolver(secrets_provider=provider)

        assert resolver.resolve("MY_SECRET") == "valor-do-provider"

    def test_ausente_em_ambos_levanta_missing_secret_error_nomeando_a_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ausente em env e provider (obrigatório, sem default) -> erro (Req 7.2)."""
        monkeypatch.delenv("MY_SECRET", raising=False)
        provider = InMemorySecretsProvider({})  # não contém a chave
        resolver = SecretResolver(secrets_provider=provider)

        with pytest.raises(MissingSecretError) as exc_info:
            resolver.resolve("MY_SECRET")

        message = str(exc_info.value)
        # A mensagem nomeia a variável...
        assert "MY_SECRET" in message
        # ...e NUNCA vaza qualquer valor de segredo.
        assert "valor-do-provider" not in message
        assert "valor-da-env" not in message

    def test_erro_nao_vaza_valor_presente_apenas_no_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reforça que o erro nomeia a var, nunca o valor do provider (Req 7.2).

        Aqui o provider tem a chave apenas com whitespace (== ausente), então o
        resolver deve falhar sem colocar o conteúdo do provider na mensagem.
        """
        monkeypatch.delenv("MY_SECRET", raising=False)
        provider = InMemorySecretsProvider(
            {"MY_SECRET": "   "}
        )  # whitespace == ausente
        resolver = SecretResolver(secrets_provider=provider)

        with pytest.raises(MissingSecretError) as exc_info:
            resolver.resolve("MY_SECRET")

        assert "MY_SECRET" in str(exc_info.value)


class TestAWSSecretsManagerProviderImportableWithoutBoto3:
    """O adapter AWS é importável/instanciável SEM boto3 (import tardio) (Req 7.1)."""

    ADAPTER_MODULE = "qa_platform.infrastructure.secrets.aws_secrets_manager"

    def test_importavel_e_instanciavel_sem_boto3(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Importar o módulo e instanciar o provider não requer boto3.

        Simulamos a ausência do SDK bloqueando qualquer ``import boto3`` e
        recarregando o módulo do adapter. Import + instanciação devem funcionar;
        o boto3 só seria exigido em ``_load()``/``get()``.
        """
        # Bloqueia a importação de boto3 para simular o SDK ausente.
        monkeypatch.setitem(sys.modules, "boto3", None)

        real_import = builtins.__import__

        def _blocked_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "boto3" or name.startswith("boto3."):
                raise ImportError("No module named 'boto3'")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(builtins, "__import__", _blocked_import)

        # (Re)importar o módulo do adapter deve funcionar mesmo sem boto3.
        module = importlib.import_module(self.ADAPTER_MODULE)
        module = importlib.reload(module)

        provider_cls = module.AWSSecretsManagerProvider

        # Instanciar o provider NÃO deve exigir boto3 (import tardio).
        provider = provider_cls(secret_name="qa-platform-secrets")
        assert provider is not None

    def test_boto3_so_e_necessario_ao_consultar_a_fonte(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``get()`` (que aciona ``_load``) é o único ponto que exige boto3.

        Com o SDK bloqueado, import + instanciação passam, mas ``get()`` tenta o
        import tardio de boto3 e falha com ImportError — provando que a
        dependência é confinada à consulta real.
        """
        monkeypatch.setitem(sys.modules, "boto3", None)

        real_import = builtins.__import__

        def _blocked_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "boto3" or name.startswith("boto3."):
                raise ImportError("No module named 'boto3'")
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(builtins, "__import__", _blocked_import)

        module = importlib.import_module(self.ADAPTER_MODULE)
        module = importlib.reload(module)
        provider = module.AWSSecretsManagerProvider(secret_name="qa-platform-secrets")

        with pytest.raises(ImportError):
            provider.get("ANY_KEY")
