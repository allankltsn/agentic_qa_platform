"""Testes de fronteiras de arquitetura (ports & adapters).

Garante, de forma automática, as invariantes de dependência entre camadas:

* A camada ``domain`` é pura: não importa framework web, bibliotecas de
  infraestrutura nem código das camadas ``application``/``infrastructure``/
  ``interface`` (Requisito 5.2).
* ``boto3`` (cliente AWS) não vaza para ``domain`` nem para ``interface``; ele
  só pode aparecer no adapter de Secrets Manager
  (``infrastructure/secrets/aws_secrets_manager.py``) (Requisito 5.3).
* A rota de saúde vive na camada ``interface`` e o ``domain`` não a conhece
  (Requisito 5.5).

Estratégia: um teste baseado em AST — robusto e sempre executável — varre o
código-fonte das camadas e valida os imports; complementarmente, se a CLI do
import-linter estiver disponível, um segundo teste roda o contrato declarado em
``importlinter.ini`` (e é pulado com ``pytest.skip`` quando a ferramenta não
puder ser invocada).
"""

from __future__ import annotations

import ast
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest

# Raiz do projeto (…/qa-platform) e diretório-base do pacote.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "src" / "qa_platform"

DOMAIN_DIR = PACKAGE_ROOT / "domain"
INTERFACE_DIR = PACKAGE_ROOT / "interface"

# Único módulo autorizado a referenciar boto3 (o adapter de Secrets Manager).
BOTO3_ADAPTER = PACKAGE_ROOT / "infrastructure" / "secrets" / "aws_secrets_manager.py"

# Adapters autorizados a importar boto3 (fronteira externa AWS): o adapter de
# Secrets Manager e o adapter durável de RunStateStore sobre DynamoDB. Ambos
# fazem o import tardio de boto3 no ponto de uso; domain/interface permanecem
# proibidos (ver import-linter).
BOTO3_ADAPTERS = frozenset(
    {
        BOTO3_ADAPTER,
        PACKAGE_ROOT / "infrastructure" / "persistence" / "dynamodb_run_store.py",
    }
)

# Frameworks web / infraestrutura proibidos no domínio (Req 5.2, 12.1).
# Inclui o framework de orquestração ('agno') e o parser YAML do manifesto
# qa-target.yaml. O projeto usa PyYAML (importado como 'yaml'); 'ruamel' é
# coberto defensivamente — nenhum módulo do domínio pode importar um parser
# YAML, mantendo os value objects e ports puros (Req 6.2, 11.1, 12.1).
FORBIDDEN_IN_DOMAIN_EXTERNAL = frozenset(
    {
        "fastapi",
        "starlette",
        "pydantic",
        "uvicorn",
        "mangum",
        "boto3",
        "agno",
        "yaml",
        "ruamel",
    }
)

# Framework de orquestração proibido em domain e interface (Req 12.1–12.4).
# Só os adapters de infrastructure (orchestration/layers) podem importar 'agno';
# domain e interface nunca o fazem diretamente.
AGNO_TOP_LEVEL = "agno"

# Parsers YAML proibidos em domain e interface. O manifesto qa-target.yaml é
# lido apenas na infraestrutura; os tipos do domínio permanecem agnósticos ao
# formato de serialização (Req 12.1). 'ruamel' é coberto defensivamente.
YAML_PARSER_TOP_LEVELS = frozenset({"yaml", "ruamel"})
# Outras camadas que o domínio nunca pode importar (Req 5.2).
FORBIDDEN_IN_DOMAIN_LAYERS = frozenset(
    {
        "qa_platform.application",
        "qa_platform.infrastructure",
        "qa_platform.interface",
    }
)


def _iter_python_files(directory: Path) -> Iterator[Path]:
    """Itera os arquivos ``.py`` de uma camada, ignorando caches."""
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _imported_names(source: str, filename: str) -> Iterator[str]:
    """Extrai, via AST, os nomes de módulo importados por um arquivo.

    Rende tanto ``import a.b`` quanto ``from a.b import c`` como ``"a.b"``.
    Imports relativos (``from . import x``) são resolvidos para o pacote
    ``qa_platform.<camada>`` correspondente pelo chamador; aqui devolvemos o
    módulo bruto e o nível é tratado à parte quando necessário.
    """
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            # Imports relativos (level > 0) ficam dentro da própria camada e
            # são inofensivos para estas regras; só analisamos os absolutos.
            if node.level == 0 and node.module:
                yield node.module


def _top_level(module: str) -> str:
    """Primeiro segmento de um caminho de módulo pontilhado."""
    return module.split(".", 1)[0]


def test_domain_layer_has_no_forbidden_imports() -> None:
    """domain não importa framework web, infraestrutura nem outras camadas.

    Valida Requisitos 5.2 e 5.5 (o domínio não conhece a interface/rota).
    """
    assert DOMAIN_DIR.is_dir(), f"diretório domain ausente: {DOMAIN_DIR}"

    violations: list[str] = []
    for path in _iter_python_files(DOMAIN_DIR):
        source = path.read_text(encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)
        for module in _imported_names(source, str(path)):
            top = _top_level(module)
            if top in FORBIDDEN_IN_DOMAIN_EXTERNAL:
                violations.append(
                    f"{rel}: import proibido de framework/infra '{module}'"
                )
            if any(
                module == layer or module.startswith(layer + ".")
                for layer in FORBIDDEN_IN_DOMAIN_LAYERS
            ):
                violations.append(f"{rel}: domain importa outra camada '{module}'")

    assert not violations, "Fronteiras do domain violadas:\n" + "\n".join(violations)


def test_boto3_does_not_leak_into_domain_or_interface() -> None:
    """boto3 não aparece em domain nem interface (confinado ao adapter).

    Valida Requisito 5.3.
    """
    violations: list[str] = []
    for directory in (DOMAIN_DIR, INTERFACE_DIR):
        for path in _iter_python_files(directory):
            source = path.read_text(encoding="utf-8")
            rel = path.relative_to(PROJECT_ROOT)
            for module in _imported_names(source, str(path)):
                if _top_level(module) == "boto3":
                    violations.append(f"{rel}: import proibido de '{module}'")

    assert not violations, "boto3 vazou para domain/interface:\n" + "\n".join(
        violations
    )


def test_agno_does_not_leak_into_domain_or_interface() -> None:
    """agno não aparece em domain nem interface (confinado aos adapters).

    Só os adapters de orquestração/camadas de QA em ``infrastructure`` podem
    importar o framework 'agno' diretamente; domain e interface nunca o fazem,
    mantendo os tipos do framework fora do núcleo e da borda HTTP.
    Valida Requisitos 12.1, 12.2, 12.3.
    """
    violations: list[str] = []
    for directory in (DOMAIN_DIR, INTERFACE_DIR):
        for path in _iter_python_files(directory):
            source = path.read_text(encoding="utf-8")
            rel = path.relative_to(PROJECT_ROOT)
            for module in _imported_names(source, str(path)):
                if _top_level(module) == AGNO_TOP_LEVEL:
                    violations.append(f"{rel}: import proibido de '{module}'")

    assert not violations, "agno vazou para domain/interface:\n" + "\n".join(violations)


def test_yaml_parser_does_not_leak_into_domain_or_interface() -> None:
    """O parser YAML não aparece em domain nem interface.

    O manifesto ``qa-target.yaml`` é lido apenas na infraestrutura; os tipos do
    domínio e a borda HTTP permanecem agnósticos ao formato de serialização.
    Cobre 'yaml' (PyYAML, usado pelo projeto) e 'ruamel' (defensivamente).
    Valida Requisito 12.1.
    """
    violations: list[str] = []
    for directory in (DOMAIN_DIR, INTERFACE_DIR):
        for path in _iter_python_files(directory):
            source = path.read_text(encoding="utf-8")
            rel = path.relative_to(PROJECT_ROOT)
            for module in _imported_names(source, str(path)):
                if _top_level(module) in YAML_PARSER_TOP_LEVELS:
                    violations.append(
                        f"{rel}: import proibido de parser YAML '{module}'"
                    )

    assert not violations, "parser YAML vazou para domain/interface:\n" + "\n".join(
        violations
    )


def test_domain_value_objects_and_ports_remain_pure() -> None:
    """Value objects e ports do domínio permanecem puros.

    Varre ``DOMAIN_DIR`` (que inclui o subpacote ``ports/`` via rglob) e garante
    que nenhum arquivo importa o framework de orquestração ('agno'), um parser
    YAML ('yaml'/'ruamel') ou qualquer outra camada — os ports (interfaces) e os
    value objects não dependem de infraestrutura, orquestração nem serialização.
    Valida Requisitos 6.2, 11.1, 12.1.
    """
    assert DOMAIN_DIR.is_dir(), f"diretório domain ausente: {DOMAIN_DIR}"
    ports_dir = DOMAIN_DIR / "ports"
    assert ports_dir.is_dir(), f"subpacote de ports ausente: {ports_dir}"

    violations: list[str] = []
    for path in _iter_python_files(DOMAIN_DIR):
        source = path.read_text(encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)
        for module in _imported_names(source, str(path)):
            top = _top_level(module)
            if top in FORBIDDEN_IN_DOMAIN_EXTERNAL:
                violations.append(
                    f"{rel}: import proibido de framework/parser/infra '{module}'"
                )
            if any(
                module == layer or module.startswith(layer + ".")
                for layer in FORBIDDEN_IN_DOMAIN_LAYERS
            ):
                violations.append(f"{rel}: domain importa outra camada '{module}'")

    assert not violations, (
        "Pureza do domínio (value objects/ports) violada:\n" + "\n".join(violations)
    )


def test_boto3_only_appears_in_secrets_adapter() -> None:
    """No pacote inteiro, boto3 só é importado pelos adapters AWS autorizados.

    Os únicos módulos que podem importar boto3 são o adapter de Secrets Manager
    e o adapter durável de RunStateStore sobre DynamoDB (fronteira externa AWS).
    Valida Requisito 5.3 (boto3 confinado aos adapters).
    """
    for adapter in BOTO3_ADAPTERS:
        assert adapter.is_file(), f"adapter esperado ausente: {adapter}"

    offenders: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT):
        if path in BOTO3_ADAPTERS:
            continue
        source = path.read_text(encoding="utf-8")
        for module in _imported_names(source, str(path)):
            if _top_level(module) == "boto3":
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
                break

    assert not offenders, (
        "boto3 deve aparecer apenas nos adapters AWS autorizados "
        "(Secrets Manager e DynamoDB RunStateStore); encontrado também em:\n"
        + "\n".join(offenders)
    )


def test_health_route_lives_in_interface_not_domain() -> None:
    """A rota de saúde é definida na interface; o domain não a contém.

    Valida Requisito 5.5.
    """
    # A definição da rota existe na camada interface.
    interface_defines_route = any(
        "/health" in path.read_text(encoding="utf-8")
        for path in _iter_python_files(INTERFACE_DIR)
    )
    assert interface_defines_route, "rota /health não encontrada na camada interface"

    # O domain não referencia nem define a rota de saúde.
    for path in _iter_python_files(DOMAIN_DIR):
        text = path.read_text(encoding="utf-8")
        assert (
            "/health" not in text
        ), f"{path.relative_to(PROJECT_ROOT)} referencia a rota /health"


def _lint_imports_argv() -> list[str]:
    """Devolve o prefixo de argv para invocar o import-linter, ou pula com graça.

    O import-linter expõe o comando click ``importlinter.cli.lint_imports_command``.
    Preferimos invocá-lo como módulo via ``python -c`` — determinístico e imune a
    console scripts ausentes ou a shims inválidos no ambiente. Se o pacote
    ``importlinter`` não estiver importável, caímos para o console script
    ``lint-imports`` (ao lado do interpretador ou no PATH); e, se nada disso
    existir, o teste é pulado com ``pytest.skip``.
    """
    if importlib.util.find_spec("importlinter") is not None:
        run_cli = (
            "import sys; from importlinter.cli import lint_imports_command as c;"
            " sys.exit(c(standalone_mode=False) or 0)"
        )
        return [sys.executable, "-c", run_cli]

    candidates = [
        Path(sys.executable).with_name("lint-imports"),
        Path(sys.executable).with_name("lint-imports.exe"),
    ]
    lint_imports = next((str(c) for c in candidates if c.exists()), None)
    if lint_imports is None:
        lint_imports = shutil.which("lint-imports")
    if lint_imports is None:
        pytest.skip("import-linter não está disponível neste ambiente")
    return [lint_imports]


def _run_lint_imports(
    config: Path,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Roda o import-linter com ``--config <config>`` num diretório de trabalho.

    Helper genérico reutilizado pelo teste positivo (config real do projeto) e
    pelo cenário negativo (config temporário). Pula com graça se a CLI não puder
    ser invocada no ambiente.
    """
    argv = _lint_imports_argv()
    return subprocess.run(
        [*argv, "--config", str(config)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_import_linter() -> subprocess.CompletedProcess[str]:
    """Executa o import-linter contra o importlinter.ini na raiz do projeto."""
    config = PROJECT_ROOT / "importlinter.ini"
    return _run_lint_imports(config, PROJECT_ROOT)


def test_import_linter_contracts_pass() -> None:
    """Os contratos declarados em importlinter.ini são satisfeitos.

    Complementa a verificação AST usando a ferramenta oficial. É pulado com
    graça quando o import-linter não puder ser invocado no ambiente.
    Valida Requisitos 5.2, 5.3, 5.5.
    """
    result = _run_import_linter()
    assert result.returncode == 0, (
        "import-linter reportou violações de contrato:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_import_linter_reports_failure_on_forbidden_import(tmp_path: Path) -> None:
    """Cenário negativo: a verificação FALHA e nomeia o import proibido.

    Confirma que o mecanismo de verificação de fronteiras realmente reprova
    quando um import proibido existe (não é um teste que só passa por vacuidade).
    Monta um pacote descartável em ``tmp_path`` cujo módulo importa a stdlib
    ``os`` e um contrato ``forbidden`` que proíbe exatamente ``os``; então roda
    ``lint-imports`` e verifica que o retorno é diferente de zero e que o módulo
    proibido ('os') é nomeado na saída. Usa-se ``os`` — sempre importável — para
    manter o teste hermético e determinístico, sem depender de pacotes opcionais
    (ex.: 'agno' pode não estar instalado). Valida Requisito 12.3.
    """
    pkg = tmp_path / "pkg_negativo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    # Módulo que introduz o import proibido de forma determinística.
    (pkg / "usa_os.py").write_text('import os\n\n__all__ = ["os"]\n', encoding="utf-8")

    config = tmp_path / "importlinter_negativo.ini"
    config.write_text(
        "[importlinter]\n"
        "root_package = pkg_negativo\n"
        "include_external_packages = True\n"
        "\n"
        "[importlinter:contract:proibe-os]\n"
        "name = pkg_negativo nao pode importar os\n"
        "type = forbidden\n"
        "source_modules =\n"
        "    pkg_negativo\n"
        "forbidden_modules =\n"
        "    os\n",
        encoding="utf-8",
    )

    # Garante que o pacote temporário é importável pelo grafo do import-linter.
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(tmp_path) + os.pathsep + existing if existing else str(tmp_path)
    )

    result = _run_lint_imports(config, tmp_path, env=env)

    assert result.returncode != 0, (
        "esperava-se que o import-linter reprovasse com um import proibido, "
        f"mas retornou 0:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "os" in combined, (
        "a saída da verificação deveria nomear o módulo proibido 'os':\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
