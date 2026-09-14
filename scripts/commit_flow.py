# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""commit_flow.py — fluxo de commit/push/PR guiado por arquivo.

Objetivo
--------
Simplificar e padronizar o versionamento: o conteúdo (mensagem de commit,
CHANGELOG, SemVer, descrição de PR) é redigido por fora, em UM arquivo por
commit dentro de ``commits/``; este script apenas EXECUTA o fluxo git de forma
determinística a partir desse arquivo.

Uso
---
    uv run commit                    # add + commit + push (SEM PR). Maior N em commits/
    uv run commit --pr               # ... e também abre o PR (usa a seção PR)
    uv run commit 3-fix-parser       # arquivo específico (com/sem prefixo)
    uv run --script scripts/commit_flow.py [arquivo] [opções]

Comportamento padrão
--------------------
Sem opções, o fluxo é ``add + commit + push`` — nunca abre PR, mesmo que o
arquivo tenha a seção ``PR``. O PR é opt-in via ``--pr`` (exige a seção ``PR``).

Seleção automática do arquivo
-----------------------------
Os arquivos de commit são nomeados ``<N>-<nome>.md`` (ex.: ``0-setup.md``,
``1-fix.md``). Sem argumento, o script escolhe SEMPRE o de maior ``N``. Para
forçar outro, passe o nome (com ou sem o ``.md``); se não for um caminho
existente, o script o procura dentro de ``commits/``.

Opções
------
    --pr             Abre o PR ao final (usa a seção PR do arquivo).
    --dry-run        Mostra o que faria, sem executar nada que altere o repo.
    --no-push        Faz commit mas não faz push.
    --base <branch>  Branch base do PR (default: 'main').
    --yes            Não pede confirmação interativa antes de commit/push.
    --keep           Não remove o arquivo de commit após concluir com sucesso.

Formato do arquivo de commit
----------------------------
Seções delimitadas por ``>>> NOME`` ... ``<<<`` (veja ``commits/_TEMPLATE.md``):
    COMMIT     (obrigatória) mensagem completa do commit.
    FILES      (opcional)    um caminho por linha; vazio => `git add -A`.
    CHANGELOG  (opcional)    apenas documentação, não é aplicado.
    PR         (opcional)    título (1ª linha) + descrição; usada apenas com --pr.

Disciplina operacional
-----------------------
- Fail-fast: valida pré-requisitos e o arquivo ANTES de tocar no repo.
- Um comando git por vez; lê a saída e só então prossegue.
- `git push` SEMPRE explícito: `git push -u origin <branch-atual>`.
- NUNCA faz push direto para a branch base (main/master).
- PR: usa `gh` se disponível; senão, imprime a URL de "compare" do GitHub.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess  # nosec B404 - uso controlado, sem shell, args em lista
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

# Branches base protegidas: o script recusa push direto para qualquer uma delas.
PROTECTED_BRANCHES = frozenset({"main", "master"})

SECTION_RE = re.compile(r"^>>>[ \t]+([A-Z]+)[ \t]*$")
SECTION_END = "<<<"
KNOWN_SECTIONS = frozenset({"COMMIT", "FILES", "CHANGELOG", "PR"})

# Pasta dos arquivos de commit e o padrão de nome `<N>-<nome>.md`.
COMMITS_DIRNAME = "commits"
COMMIT_FILE_RE = re.compile(r"^(\d+)-.+\.md$")


def fail(message: str) -> None:
    """Encerra com exit code != 0 e mensagem no stderr, sem mudanças parciais."""
    print(f"Erro (commit_flow.py): {message}", file=sys.stderr)
    raise SystemExit(1)


@dataclass(frozen=True)
class CommitSpec:
    """Conteúdo declarado no arquivo de commit, já validado."""

    commit_message: str
    files: list[str] = field(default_factory=list)
    pr_title: str | None = None
    pr_body: str | None = None

    @property
    def has_pr(self) -> bool:
        return self.pr_title is not None


def parse_sections(text: str) -> dict[str, str]:
    """Extrai as seções ``>>> NOME`` ... ``<<<`` do arquivo.

    Texto fora de seções é ignorado. Uma seção desconhecida é um erro explícito
    (evita silenciar um typo no nome da seção).
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []

    for lineno, raw in enumerate(text.splitlines(), start=1):
        match = SECTION_RE.match(raw)
        if match is not None:
            if current is not None:
                fail(
                    f"seção '{current}' não foi fechada com '{SECTION_END}' "
                    f"antes de abrir '{match.group(1)}' (linha {lineno})."
                )
            name = match.group(1)
            if name not in KNOWN_SECTIONS:
                fail(
                    f"seção desconhecida '{name}' (linha {lineno}). "
                    f"Válidas: {', '.join(sorted(KNOWN_SECTIONS))}."
                )
            if name in sections:
                fail(f"seção '{name}' declarada mais de uma vez (linha {lineno}).")
            current = name
            buffer = []
            continue

        if current is not None and raw.strip() == SECTION_END:
            sections[current] = "\n".join(buffer).strip("\n")
            current = None
            buffer = []
            continue

        if current is not None:
            buffer.append(raw)

    if current is not None:
        fail(
            f"seção '{current}' não foi fechada com '{SECTION_END}' no fim do arquivo."
        )

    return sections


def build_spec(path: Path) -> CommitSpec:
    """Lê o arquivo de commit e valida o conteúdo mínimo (fail-fast)."""
    if not path.is_file():
        fail(f"arquivo de commit não encontrado: {path}")

    sections = parse_sections(path.read_text(encoding="utf-8"))

    commit_message = sections.get("COMMIT", "").strip()
    if not commit_message:
        fail("seção obrigatória 'COMMIT' ausente ou vazia.")

    files = [
        line.strip() for line in sections.get("FILES", "").splitlines() if line.strip()
    ]

    pr_title: str | None = None
    pr_body: str | None = None
    pr_raw = sections.get("PR", "").strip()
    if pr_raw:
        pr_lines = pr_raw.splitlines()
        pr_title = pr_lines[0].strip()
        pr_body = "\n".join(pr_lines[1:]).strip()
        if not pr_title:
            fail("seção 'PR' presente mas sem título na primeira linha.")

    return CommitSpec(
        commit_message=commit_message,
        files=files,
        pr_title=pr_title,
        pr_body=pr_body,
    )


def run_git(args: list[str], *, capture: bool = False, dry_run: bool = False) -> str:
    """Executa um comando git (sem shell). Em dry-run, apenas ecoa."""
    printable = "git " + " ".join(args)
    if dry_run:
        print(f"[dry-run] {printable}")
        return ""
    try:
        result = subprocess.run(  # nosec B603 - args em lista, sem shell
            ["git", *args],
            check=True,
            text=True,
            capture_output=capture,
        )
    except FileNotFoundError:
        fail("dependência de sistema ausente: 'git' não encontrada no PATH.")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        fail(f"comando falhou: {printable}\n{detail}")
    return (result.stdout or "").strip() if capture else ""


def git_output(args: list[str]) -> str:
    """Lê a saída de um git de leitura (sempre executa, mesmo em dry-run)."""
    try:
        result = subprocess.run(  # nosec B603 - args em lista, sem shell
            ["git", *args],
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        fail("dependência de sistema ausente: 'git' não encontrada no PATH.")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        fail(f"comando falhou: git {' '.join(args)}\n{detail}")
    return result.stdout.strip()


def confirm(prompt: str, *, assume_yes: bool) -> None:
    """Confirmação interativa; aborta se o usuário não confirmar."""
    if assume_yes:
        return
    answer = input(f"{prompt} [s/N] ").strip().lower()
    if answer not in {"s", "sim", "y", "yes"}:
        print("Abortado pelo usuário.")
        raise SystemExit(130)


def compare_url(remote_url: str, base: str, branch: str) -> str | None:
    """Deriva a URL de 'compare' do GitHub a partir da URL do remote."""
    slug: str | None = None
    if remote_url.startswith("git@github.com:"):
        slug = remote_url.split(":", 1)[1]
    elif "github.com/" in remote_url:
        slug = remote_url.split("github.com/", 1)[1]
    if slug is None:
        return None
    slug = slug.removesuffix(".git")
    b = urllib.parse.quote(base, safe="")
    h = urllib.parse.quote(branch, safe="")
    return f"https://github.com/{slug}/compare/{b}...{h}?expand=1&title="


def repo_root() -> Path:
    """Raiz do repositório git (onde o fluxo opera, independente do cwd)."""
    top = git_output(["rev-parse", "--show-toplevel"])
    return Path(top)


def commits_dir() -> Path:
    """Pasta ``commits/`` na raiz do repo; falha se ausente."""
    directory = repo_root() / COMMITS_DIRNAME
    if not directory.is_dir():
        fail(
            f"pasta '{COMMITS_DIRNAME}/' não encontrada na raiz do repo ({directory})."
        )
    return directory


def latest_commit_file() -> Path:
    """Arquivo ``<N>-<nome>.md`` de MAIOR ``N`` em ``commits/`` (fail-fast se vazio)."""
    directory = commits_dir()
    candidates: list[tuple[int, str, Path]] = []
    for entry in directory.iterdir():
        match = COMMIT_FILE_RE.match(entry.name)
        if entry.is_file() and match is not None:
            # Ordena por (N, nome) para desempate determinístico e estável.
            candidates.append((int(match.group(1)), entry.name, entry))
    if not candidates:
        fail(
            f"nenhum arquivo de commit '<N>-<nome>.md' em '{COMMITS_DIRNAME}/'. "
            f"Crie um (ex.: '{COMMITS_DIRNAME}/0-descricao.md')."
        )
    candidates.sort()
    return candidates[-1][2]


def resolve_commit_file(arg: str | None) -> Path:
    """Resolve o arquivo de commit a usar.

    - Sem argumento: o de maior ``N`` em ``commits/``.
    - Com argumento: usa como caminho se existir; senão procura em ``commits/``
      aceitando o nome com ou sem a extensão ``.md``.
    """
    if arg is None:
        return latest_commit_file()

    direct = Path(arg)
    if direct.is_file():
        return direct

    directory = commits_dir()
    for name in (arg, f"{arg}.md"):
        candidate = directory / name
        if candidate.is_file():
            return candidate

    fail(
        f"arquivo de commit '{arg}' não encontrado (nem como caminho, nem em "
        f"'{COMMITS_DIRNAME}/')."
    )
    raise AssertionError("inalcançável")  # ajuda o type-checker; fail() já sai


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="commit_flow.py",
        description="Fluxo add+commit+push (PR opcional via --pr) a partir de um arquivo.",
    )
    parser.add_argument(
        "commit_file",
        nargs="?",
        default=None,
        help="Arquivo em commits/ (nome com/sem .md, ou caminho). "
        "Se omitido, usa o de maior número.",
    )
    parser.add_argument(
        "--pr",
        action="store_true",
        help="Abre o PR ao final (usa a seção PR do arquivo). Sem esta flag, o "
        "fluxo é apenas add + commit + push.",
    )
    parser.add_argument(
        "--base", default="main", help="Branch base do PR (default: main)."
    )
    parser.add_argument("--no-push", action="store_true", help="Não faz push.")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o que faria.")
    parser.add_argument("--yes", action="store_true", help="Não pede confirmação.")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Não remove o arquivo de commit após concluir com sucesso.",
    )
    opts = parser.parse_args()

    # --- pré-requisitos (ANTES de tocar no repo) -----------------------------
    if shutil.which("git") is None:
        fail("dependência de sistema ausente: 'git' não encontrada no PATH.")

    if git_output(["rev-parse", "--is-inside-work-tree"]) != "true":
        fail("diretório atual não é um repositório git.")

    # Resolve o arquivo (auto: maior número) e lê/valida seu conteúdo.
    commit_file = resolve_commit_file(opts.commit_file)
    spec = build_spec(commit_file)

    # PR é opt-in via --pr; exige a seção PR no arquivo (fail-fast).
    if opts.pr and not spec.has_pr:
        fail("--pr informado, mas o arquivo de commit não tem a seção 'PR'.")

    branch = git_output(["rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "HEAD":
        fail("HEAD destacado (detached). Faça checkout de uma branch antes.")
    if branch in PROTECTED_BRANCHES:
        fail(
            f"branch atual '{branch}' é protegida. Trabalhe numa branch de "
            f"feature; nunca comite/pushe direto para {sorted(PROTECTED_BRANCHES)}."
        )

    # --- resumo do que será feito -------------------------------------------
    title = spec.commit_message.splitlines()[0]
    print("== Fluxo de commit ==")
    print(f"  branch      : {branch}")
    print(f"  arquivo     : {commit_file}")
    print(f"  add         : {'arquivos específicos' if spec.files else 'tudo (-A)'}")
    print(f"  commit      : {title}")
    print(f"  push        : {'não' if opts.no_push else f'origin {branch}'}")
    print(f"  PR          : {'sim -> ' + (spec.pr_title or '') if opts.pr else 'não'}")
    print()

    confirm("Prosseguir com o commit?", assume_yes=opts.yes or opts.dry_run)

    # --- stage --------------------------------------------------------------
    if spec.files:
        run_git(["add", "--", *spec.files], dry_run=opts.dry_run)
    else:
        run_git(["add", "-A"], dry_run=opts.dry_run)

    # Nada staizado é erro claro (evita commit vazio silencioso).
    if not opts.dry_run:
        staged = git_output(["diff", "--cached", "--name-only"])
        if not staged:
            fail("nada staizado para commitar (working tree limpa ou FILES não casou).")

    # --- commit (mensagem da seção COMMIT via arquivo temporário) -----------
    # Escrever a mensagem em arquivo e usar `git commit -F` preserva o corpo
    # (múltiplas linhas, linhas em branco, trailers) sem depender de shell.
    if opts.dry_run:
        print(
            f"[dry-run] git commit -F <mensagem da seção COMMIT>\n---\n{spec.commit_message}\n---"
        )
    else:
        tmp = commit_file.with_suffix(commit_file.suffix + ".msg.tmp")
        tmp.write_text(spec.commit_message + "\n", encoding="utf-8")
        try:
            run_git(["commit", "-F", str(tmp)])
        finally:
            tmp.unlink(missing_ok=True)

    # --- push (explícito) ----------------------------------------------------
    # Sem push, o fluxo fica incompleto: mantém o arquivo de commit para retomar.
    if opts.no_push:
        print("Push pulado (--no-push). Arquivo de commit preservado.")
        return
    confirm(f"Fazer push para origin {branch}?", assume_yes=opts.yes or opts.dry_run)
    run_git(["push", "-u", "origin", branch], dry_run=opts.dry_run)

    # --- PR (opt-in via --pr) ------------------------------------------------
    if opts.pr:
        open_pull_request(
            spec, branch, base=opts.base, title=title, dry_run=opts.dry_run
        )
    else:
        print("Concluído (add + commit + push, sem PR).")

    # --- limpeza do arquivo de commit (fluxo concluído com sucesso) ----------
    if opts.dry_run:
        print(f"[dry-run] removeria o arquivo de commit: {commit_file}")
    elif opts.keep:
        print(f"Arquivo de commit preservado (--keep): {commit_file}")
    else:
        commit_file.unlink(missing_ok=True)
        print(f"Arquivo de commit consumido e removido: {commit_file}")


def open_pull_request(
    spec: CommitSpec,
    branch: str,
    *,
    base: str,
    title: str,
    dry_run: bool,
) -> None:
    """Abre o PR via `gh` se disponível; senão, imprime a URL de compare."""
    if shutil.which("gh") is not None:
        pr_args = [
            "pr",
            "create",
            "--base",
            base,
            "--head",
            branch,
            "--title",
            spec.pr_title or title,
            "--body",
            spec.pr_body or "",
        ]
        if dry_run:
            print("[dry-run] gh " + " ".join(pr_args))
            return
        try:
            subprocess.run(["gh", *pr_args], check=True)  # nosec B603 B607
        except subprocess.CalledProcessError as exc:
            fail(f"'gh pr create' falhou (exit {exc.returncode}).")
        return

    # Sem gh: entrega a URL de compare para abrir o PR manualmente.
    remote_url = git_output(["remote", "get-url", "origin"])
    url = compare_url(remote_url, base, branch)
    print("\n'gh' não encontrado. Abra o PR manualmente:")
    if url:
        print(f"  {url}{urllib.parse.quote(spec.pr_title or title)}")
    else:
        print(f"  remote: {remote_url}  (base: {base}  <- {branch})")
    print("\n--- Título do PR ---")
    print(spec.pr_title or title)
    print("\n--- Descrição do PR ---")
    print(spec.pr_body or "")


if __name__ == "__main__":
    main()
