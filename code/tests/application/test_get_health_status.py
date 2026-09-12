"""Teste de propriedade do caso de uso GetHealthStatus (Property 1).

Verifica a propriedade universal de que a versão do serviço injetada flui
íntegra (sem alteração) para o HealthStatus produzido, com status == "ok".
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from qa_platform.application.get_health_status import GetHealthStatus
from qa_platform.domain.value_objects.health import STATUS_OK


# Gerador de strings de versão não-vazias: descarta valores vazios ou compostos
# apenas por espaços em branco, restringindo ao espaço de entrada válido.
_non_empty_versions = st.text().filter(lambda v: v.strip() != "")


# Feature: executable-environment-bootstrap, Property 1
# Property 1: Versão da configuração flui íntegra para a resposta de saúde
# Validates: Requirements 1.2, 1.3
@settings(max_examples=200)
@given(service_version=_non_empty_versions)
def test_versao_flui_integra_para_o_health_status(service_version: str) -> None:
    """Para qualquer versão não-vazia injetada, o HealthStatus preserva a versão
    exatamente e reporta status == "ok" (Req 1.2, 1.3)."""
    use_case = GetHealthStatus(service_version=service_version)

    result = use_case.execute()

    assert result.version == service_version
    assert result.status == STATUS_OK
