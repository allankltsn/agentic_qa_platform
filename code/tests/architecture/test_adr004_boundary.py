"""Teste determinístico de fronteira ADR-004 (Property 6 de requirements).

A fronteira entre o fluxo **determinístico** (Fase 1 — `Static_Inspector`,
dentro do `Orchestrator_Workflow`) e o enriquecimento **advisory** (Fase 2 —
`LLM_Enricher`, fora do fluxo) é garantida fisicamente pelo import-linter, não
apenas por convenção. Este módulo valida essa invariante de grafo de imports
como um **teste determinístico** (não é PBT): o caminho do Workflow nunca
alcança o enricher e a Fase 1 permanece livre de `agno` e do pacote de
enriquecimento.

Reutiliza integralmente o harness genérico já implementado em
``test_layer_boundaries`` (``_run_import_linter``/``_run_lint_imports``/
``_lint_imports_argv``): não há duplicação da mecânica de invocação da CLI. Aqui
apenas se acrescenta a validação específica dos dois contratos novos da fronteira
ADR-004 e um cenário negativo que espelha a aresta proibida
``orchestration -> enrichment``.

* Positivo: roda o import-linter sobre a config real (``importlinter.ini``) e
  afirma exit code 0 e que os contratos ``workflow-nao-importa-enricher`` e
  ``fase1-sem-llm`` são reportados como mantidos (KEPT) — cobre Req 10.1, 10.2,
  10.3.
* Negativo: monta um pacote descartável em que o módulo "workflow" importa o
  módulo "enrichment" (espelhando a aresta proibida do ADR-004), declara um
  contrato ``forbidden`` correspondente, roda ``lint-imports`` e afirma exit
  code != 0 e que o import ofensor (origem -> destino) é nomeado na saída —
  cobre Req 10.6.

O teste é pulado com ``pytest.skip`` quando a CLI do import-linter não puder ser
invocada no ambiente, seguindo o mesmo padrão do harness reutilizado.
"""

from __future__ import annotations

import os
from pathlib import Path

# Reutiliza o harness genérico do módulo irmão — NÃO reimplementa a mecânica de
# invocação da CLI do import-linter (evita duplicação, conforme steering 11).
from tests.architecture.test_layer_boundaries import (
    PROJECT_ROOT,
    _run_import_linter,
    _run_lint_imports,
)

# Nomes (campo `name`) dos dois contratos da fronteira ADR-004 declarados em
# importlinter.ini. São afirmados como mantidos (KEPT) no cenário positivo.
CONTRACT_WORKFLOW_NAO_IMPORTA_ENRICHER = (
    "orchestration nao importa enrichment (fronteira Workflow x LLM_Enricher)"
)
CONTRACT_FASE1_SEM_LLM = "Fase 1 (inspecao estatica) sem agno nem enrichment"


def _assert_contract_kept(output: str, contract_name: str) -> None:
    """Afirma que ``contract_name`` aparece como mantido (KEPT) na saída.

    O import-linter imprime, na seção "Contracts", uma linha por contrato no
    formato ``<name> KEPT`` ou ``<name> BROKEN``. Validamos a presença do nome e
    a ausência da marca BROKEN para ele.
    """
    assert (
        contract_name in output
    ), f"contrato ausente na saída do import-linter: {contract_name!r}\n{output}"
    broken_line = f"{contract_name} BROKEN"
    assert (
        broken_line not in output
    ), f"contrato reportado como BROKEN (esperado KEPT): {contract_name!r}\n{output}"


def test_adr004_boundary_contracts_pass() -> None:
    """Fronteira ADR-004: os dois contratos novos passam (KEPT), exit 0.

    Roda o import-linter sobre a config real do pacote ``qa_platform`` e afirma
    que o caminho do Orchestrator_Workflow não importa o LLM_Enricher e que a
    Fase 1 (inspeção estática determinística) não importa ``agno`` nem o pacote
    de enriquecimento. Pulado com graça se a CLI não estiver disponível.

    Validates: Requirements 10.1, 10.2, 10.3
    """
    # Feature: hybrid-target-discovery, Property 6
    result = _run_import_linter()
    assert result.returncode == 0, (
        "import-linter reportou violações de contrato:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    _assert_contract_kept(combined, CONTRACT_WORKFLOW_NAO_IMPORTA_ENRICHER)
    _assert_contract_kept(combined, CONTRACT_FASE1_SEM_LLM)


def test_adr004_boundary_reports_offender_on_forbidden_edge(tmp_path: Path) -> None:
    """Cenário negativo: workflow -> enrichment reprova e nomeia o ofensor.

    Monta um pacote descartável espelhando a aresta proibida do ADR-004: o
    módulo "orchestration" (Workflow) importa o módulo "enrichment"
    (LLM_Enricher). Declara um contrato ``forbidden`` idêntico em intenção ao
    ``workflow-nao-importa-enricher`` real e afirma que a verificação retorna
    código != 0 e nomeia o import ofensor (origem -> destino) — provando que a
    fronteira é de fato fisicamente verificada e identifica origem e destino.

    Validates: Requirements 10.6
    """
    # Feature: hybrid-target-discovery, Property 6
    root = "pkg_adr004"
    pkg = tmp_path / root
    orchestration = pkg / "infrastructure" / "orchestration"
    enrichment = pkg / "infrastructure" / "enrichment"
    orchestration.mkdir(parents=True)
    enrichment.mkdir(parents=True)

    for init_dir in (pkg, pkg / "infrastructure", orchestration, enrichment):
        (init_dir / "__init__.py").write_text("", encoding="utf-8")

    # Enricher (Fase 2 — destino proibido a partir do Workflow).
    (enrichment / "llm_enricher.py").write_text(
        "LLM_ENRICHER = object()\n", encoding="utf-8"
    )
    # Workflow (Fase 1 — origem) importando o enricher: a aresta proibida.
    (orchestration / "workflow.py").write_text(
        f"from {root}.infrastructure.enrichment import llm_enricher\n\n"
        '__all__ = ["llm_enricher"]\n',
        encoding="utf-8",
    )

    config = tmp_path / "importlinter_adr004_negativo.ini"
    config.write_text(
        "[importlinter]\n"
        f"root_package = {root}\n"
        "include_external_packages = True\n"
        "\n"
        "[importlinter:contract:workflow-nao-importa-enricher]\n"
        "name = orchestration nao importa enrichment (fronteira negativa)\n"
        "type = forbidden\n"
        "source_modules =\n"
        f"    {root}.infrastructure.orchestration\n"
        "forbidden_modules =\n"
        f"    {root}.infrastructure.enrichment\n",
        encoding="utf-8",
    )

    # Torna o pacote temporário importável pelo grafo do import-linter.
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(tmp_path) + os.pathsep + existing if existing else str(tmp_path)
    )

    result = _run_lint_imports(config, tmp_path, env=env)

    assert result.returncode != 0, (
        "esperava-se que o import-linter reprovasse a aresta workflow -> "
        f"enrichment, mas retornou 0:\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    origin = f"{root}.infrastructure.orchestration.workflow"
    destination = f"{root}.infrastructure.enrichment.llm_enricher"
    assert origin in combined, (
        "a saída deveria nomear o módulo de ORIGEM do import ofensor "
        f"({origin!r}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert destination in combined, (
        "a saída deveria nomear o módulo de DESTINO do import ofensor "
        f"({destination!r}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_project_root_has_importlinter_config() -> None:
    """A config real (``importlinter.ini``) existe na raiz do projeto.

    Guarda de sanidade: o teste positivo depende de rodar os contratos reais.
    """
    # Feature: hybrid-target-discovery, Property 6
    config = PROJECT_ROOT / "importlinter.ini"
    assert config.is_file(), f"importlinter.ini ausente na raiz: {config}"
