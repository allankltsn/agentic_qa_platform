"""Testes unitários da hierarquia de erros de domínio (Req 5.2)."""

from qa_platform.domain.exceptions import ConfigurationDomainError, DomainError


def test_configuration_domain_error_herda_de_domain_error() -> None:
    """ConfigurationDomainError deve herdar de DomainError (Req 5.2)."""
    assert issubclass(ConfigurationDomainError, DomainError)


def test_domain_error_e_uma_exception() -> None:
    """DomainError é a base da hierarquia e uma Exception."""
    assert issubclass(DomainError, Exception)


def test_configuration_domain_error_e_capturavel_como_domain_error() -> None:
    """Uma instância de ConfigurationDomainError é capturável como DomainError."""
    try:
        raise ConfigurationDomainError("configuração inválida")
    except DomainError as exc:
        assert isinstance(exc, ConfigurationDomainError)
    else:
        raise AssertionError(
            "ConfigurationDomainError deveria ser capturada como DomainError"
        )
