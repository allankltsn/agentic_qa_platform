#!/usr/bin/env python3
"""Executa o tooling de qualidade de codigo e consolida os resultados.

Roda, de forma deterministica e sem gasto de token de LLM, todas as ferramentas
de qualidade descritas em ``scripts/README.md`` (secao 2 — Tooling de qualidade
de codigo), captura a saida e o exit code de cada uma e gera dois artefatos:

- ``reports/quality-report.md``  (Markdown)
- ``reports/quality-report.pdf`` (PDF, via reportlab)

Uso (a partir da pasta ``code/``)::

    uv run python generate_quality_report.py
    uv run python generate_quality_report.py --package qa_platform

O script se re-executa via ``uv run --with reportlab`` para garantir a presenca
do reportlab num ambiente efemero, sem poluir o ``pyproject.toml`` do projeto.
As ferramentas do ciclo dev/deploy (setup/run-local/build/deploy) sao propositais
omitidas: sobem servidor ou fazem deploy AWS e nao produzem um relatorio.

Exit code do script:
- 0  se todas as ferramentas passarem (exit code 0);
- 1  se qualquer ferramenta falhar (relatorios ainda sao gerados).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import shutil
import subprocess  # nosec B404 - execucao controlada de ferramentas de qualidade locais
import sys
from dataclasses import dataclass
from pathlib import Path

# Diretorio do projeto (onde vive este script e o pyproject.toml).
PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_ROOT / "reports"

# Marcador para evitar loop infinito no re-exec com reportlab.
_REEXEC_FLAG = "QA_REPORT_REEXEC"

# Timeout por ferramenta (segundos): evita travar o relatorio em um comando preso.
DEFAULT_TOOL_TIMEOUT = 900

# Trunca a saida por ferramenta no PDF (a versao integral fica no Markdown).
_PDF_MAX_CHARS = 12000

# Frase de abertura reaproveitada no Markdown e no PDF.
_INTRO = "Consolida a execucao das ferramentas de qualidade descritas em scripts/README.md (secao 2)."


def _escape(text: str) -> str:
    """Escapa os caracteres especiais de markup do reportlab (&, <, >)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass(frozen=True)
class Tool:
    """Uma ferramenta de qualidade a executar.

    ``command`` e uma lista ja resolvida (sem shell) para evitar injecao.
    """

    name: str
    description: str
    command: list[str]


@dataclass
class ToolResult:
    """Resultado da execucao de uma ferramenta."""

    tool: Tool
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    skipped_reason: str | None = None

    @property
    def status(self) -> str:
        if self.skipped_reason is not None:
            return "SKIPPED"
        return "PASS" if self.exit_code == 0 else "FAIL"

    @property
    def combined_output(self) -> str:
        return (self.stdout + ("\n" + self.stderr if self.stderr else "")).strip()


def build_tools(package: str) -> list[Tool]:
    """Monta a lista de ferramentas de qualidade (scripts/README.md, secao 2)."""
    return [
        Tool(
            name="Ruff (lint)",
            description="Lint: verifica estilo, imports, complexidade e regras de seguranca.",
            command=["uv", "run", "ruff", "check", "."],
        ),
        Tool(
            name="Ruff (format --check)",
            description="Formatacao: confere se o codigo esta formatado (nao altera arquivos).",
            command=["uv", "run", "ruff", "format", "--check", "."],
        ),
        Tool(
            name="mypy",
            description="Checagem estatica de tipos em src.",
            command=["uv", "run", "mypy", "src"],
        ),
        Tool(
            name="Bandit",
            description="SAST: detecta padroes inseguros no codigo (nao roda em tests/).",
            command=["uv", "run", "bandit", "-c", "pyproject.toml", "-r", "src"],
        ),
        Tool(
            name="pip-audit",
            description="Audita dependencias com vulnerabilidades conhecidas (CVEs).",
            command=["uv", "run", "pip-audit"],
        ),
        Tool(
            name="import-linter",
            description="Garante a direcao de dependencia entre camadas (ports & adapters).",
            command=["uv", "run", "lint-imports"],
        ),
        Tool(
            name="Radon (cc)",
            description="Metricas de complexidade ciclomatica (media por bloco).",
            command=["uv", "run", "radon", "cc", "src", "-a"],
        ),
        Tool(
            name="Xenon",
            description="Falha o build se a complexidade exceder o limite configurado.",
            command=["uv", "run", "xenon", "--max-absolute", "B", "src"],
        ),
        Tool(
            name="pytest (+cov)",
            description="Testes unitarios com relatorio de cobertura.",
            command=[
                "uv",
                "run",
                "pytest",
                "-m",
                "not e2e and not system and not integration",
                f"--cov={package}",
            ],
        ),
    ]


def run_tool(tool: Tool, *, timeout: int) -> ToolResult:
    """Executa uma ferramenta capturando stdout/stderr/exit code, sem shell."""
    executable = tool.command[0]
    if shutil.which(executable) is None:
        return ToolResult(
            tool=tool,
            exit_code=127,
            stdout="",
            stderr=f"Dependencia ausente: '{executable}' nao encontrado no PATH.",
            duration_s=0.0,
            skipped_reason=f"'{executable}' nao encontrado no PATH",
        )

    start = _dt.datetime.now(tz=_dt.UTC)
    try:
        completed = subprocess.run(  # nosec B603 - comando fixo, sem shell, entradas controladas
            tool.command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        duration = (_dt.datetime.now(tz=_dt.UTC) - start).total_seconds()
        return ToolResult(
            tool=tool,
            exit_code=124,
            stdout="",
            stderr=f"Timeout apos {timeout}s.",
            duration_s=duration,
        )

    duration = (_dt.datetime.now(tz=_dt.UTC) - start).total_seconds()
    return ToolResult(
        tool=tool,
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_s=duration,
    )


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tally(results: list[ToolResult]) -> tuple[int, int, int]:
    """Retorna (passed, failed, skipped)."""
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIPPED")
    return passed, failed, skipped


def render_markdown(results: list[ToolResult], generated_at: str) -> str:
    """Gera o corpo do relatorio em Markdown."""
    lines: list[str] = [
        "# Relatorio de Qualidade de Codigo — QA Platform",
        "",
        f"Gerado em: `{generated_at}`",
        "",
        _INTRO,
        "",
        "## Sumario",
        "",
        "| Ferramenta | Status | Exit code | Duracao (s) |",
        "| --- | --- | --- | --- |",
    ]
    for r in results:
        lines.append(
            f"| {r.tool.name} | {r.status} | {r.exit_code} | {r.duration_s:.1f} |"
        )
    lines.append("")

    passed, failed, skipped = _tally(results)
    lines.append(
        f"**Total:** {len(results)} ferramentas — "
        f"{passed} PASS, {failed} FAIL, {skipped} SKIPPED."
    )
    lines.append("")

    lines.append("## Detalhes")
    lines.append("")
    for r in results:
        lines.append(f"### {r.tool.name} — {r.status}")
        lines.append("")
        lines.append(r.tool.description)
        lines.append("")
        lines.append(f"- Comando: `{' '.join(r.tool.command)}`")
        lines.append(f"- Exit code: `{r.exit_code}`")
        lines.append(f"- Duracao: `{r.duration_s:.1f}s`")
        if r.skipped_reason:
            lines.append(f"- Ignorada: {r.skipped_reason}")
        lines.append("")
        output = r.combined_output
        if output:
            lines.append("```text")
            lines.append(output)
            lines.append("```")
        else:
            lines.append("_Sem saida._")
        lines.append("")

    return "\n".join(lines)


def render_pdf(results: list[ToolResult], generated_at: str, out_path: Path) -> None:
    """Gera o relatorio em PDF usando reportlab (skill 'pdf')."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    mono = ParagraphStyle(
        "Mono",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7,
        leading=8.5,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        title="Relatorio de Qualidade de Codigo — QA Platform",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    story: list = []

    story.append(
        Paragraph("Relatorio de Qualidade de Codigo — QA Platform", styles["Title"])
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Gerado em: {_escape(generated_at)}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_escape(_INTRO), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Tabela de sumario
    status_color = {"PASS": colors.green, "FAIL": colors.red, "SKIPPED": colors.orange}
    table_data: list[list[str]] = [["Ferramenta", "Status", "Exit code", "Duracao (s)"]]
    for r in results:
        table_data.append(
            [r.tool.name, r.status, str(r.exit_code), f"{r.duration_s:.1f}"]
        )
    table = Table(
        table_data, hAlign="LEFT", colWidths=[70 * mm, 25 * mm, 25 * mm, 30 * mm]
    )
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#f4f6f7")],
        ),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for row_idx, r in enumerate(results, start=1):
        style_cmds.append(
            (
                "TEXTCOLOR",
                (1, row_idx),
                (1, row_idx),
                status_color.get(r.status, colors.black),
            )
        )
    table.setStyle(TableStyle(style_cmds))
    story.append(table)
    story.append(Spacer(1, 8))

    passed, failed, skipped = _tally(results)
    story.append(
        Paragraph(
            f"<b>Total:</b> {len(results)} ferramentas — {passed} PASS, "
            f"{failed} FAIL, {skipped} SKIPPED.",
            styles["Normal"],
        )
    )
    story.append(PageBreak())

    # Detalhes
    story.append(Paragraph("Detalhes", styles["Heading1"]))
    for r in results:
        story.append(
            Paragraph(f"{_escape(r.tool.name)} — {r.status}", styles["Heading2"])
        )
        story.append(Paragraph(_escape(r.tool.description), styles["Normal"]))
        detail = (
            f"Comando: <font face='Courier'>{_escape(' '.join(r.tool.command))}</font><br/>"
            f"Exit code: {r.exit_code} &nbsp;|&nbsp; Duracao: {r.duration_s:.1f}s"
        )
        if r.skipped_reason:
            detail += f"<br/>Ignorada: {_escape(r.skipped_reason)}"
        story.append(Paragraph(detail, styles["Normal"]))
        story.append(Spacer(1, 4))

        output = r.combined_output or "Sem saida."
        if len(output) > _PDF_MAX_CHARS:
            output = (
                output[:_PDF_MAX_CHARS] + "\n... [saida truncada; veja o Markdown] ..."
            )
        for chunk in output.splitlines() or [""]:
            story.append(Paragraph(_escape(chunk) or "&nbsp;", mono))
        story.append(Spacer(1, 10))

    doc.build(story)


def ensure_reportlab_and_reexec() -> None:
    """Garante reportlab; se ausente, re-executa via uv run --with reportlab."""
    try:
        import reportlab  # noqa: F401
    except ImportError:
        pass
    else:
        return

    if os.environ.get(_REEXEC_FLAG) == "1":
        # Ja tentamos o re-exec e ainda falta reportlab: falha clara.
        print(
            "Erro: 'reportlab' ausente e o re-exec via uv nao o disponibilizou.",
            file=sys.stderr,
        )
        sys.exit(2)

    if shutil.which("uv") is None:
        print(
            "Erro: 'reportlab' ausente e 'uv' nao encontrado no PATH para instala-lo. "
            "Instale reportlab ou uv (https://docs.astral.sh/uv/).",
            file=sys.stderr,
        )
        sys.exit(2)

    env = dict(os.environ, **{_REEXEC_FLAG: "1"})
    cmd = ["uv", "run", "--with", "reportlab", "python", *sys.argv]
    completed = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, check=False)  # nosec B603
    sys.exit(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        default="qa_platform",
        help="Pacote alvo para a cobertura do pytest (default: qa_platform).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TOOL_TIMEOUT,
        help=f"Timeout por ferramenta em segundos (default: {DEFAULT_TOOL_TIMEOUT}).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPORTS_DIR),
        help="Diretorio de saida dos relatorios (default: reports/).",
    )
    args = parser.parse_args(argv)

    # Garante reportlab antes de qualquer trabalho (fail-fast; pode re-executar).
    ensure_reportlab_and_reexec()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tools = build_tools(args.package)
    generated_at = _now_iso()
    print(_now_iso())

    print(f"==> Executando {len(tools)} ferramentas de qualidade...", file=sys.stderr)
    results: list[ToolResult] = []
    for tool in tools:
        print(f"    - {tool.name} ...", file=sys.stderr)
        result = run_tool(tool, timeout=args.timeout)
        print(f"      {result.status} (exit {result.exit_code})", file=sys.stderr)
        results.append(result)

    md = render_markdown(results, generated_at)
    md_path = output_dir / f"{_now_iso().replace(':', '-')}/quality-report.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    print(md_path)
    md_path.write_text(md, encoding="utf-8")
    print(f"==> Markdown gerado: {md_path}", file=sys.stderr)

    pdf_path = output_dir / f"{_now_iso().replace(':', '-')}/quality-report.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    render_pdf(results, generated_at, pdf_path)
    print(f"==> PDF gerado: {pdf_path}", file=sys.stderr)

    _, failed_count, _ = _tally(results)
    if failed_count:
        names = ", ".join(r.tool.name for r in results if r.status == "FAIL")
        print(f"==> {failed_count} ferramenta(s) com falha: {names}", file=sys.stderr)
        return 1
    print("==> Todas as ferramentas passaram.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
