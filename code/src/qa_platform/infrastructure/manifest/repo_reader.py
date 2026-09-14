"""Leitura estática total do repositório-alvo (Fase 1, Requisitos 2.3, 2.6).

Produz uma visão **imutável e ordenada** dos arquivos do artefato resolvido a
partir do **filesystem local** — sem rede, sem LLM, sem framework de agente. É
detalhe de implementação do ``Static_Inspector`` (mesma fase, mesmo adapter),
por isso vive em ``infrastructure/manifest`` junto dele.

Determinismo por design (Requisito 2.3): este módulo **não importa** ``agno``,
``boto3`` nem qualquer cliente HTTP. Toda a leitura é do sistema de arquivos
local, e a visão devolvida (``RepoView``) é ordenada por caminho com critério
explícito e independente da ordem de varredura do filesystem.

Integridade da leitura (Requisito 2.6): se qualquer arquivo elegível não puder
ser lido integralmente (permissão, decodificação, I/O), a leitura **aborta sem
visão parcial**, levantando ``RepoReadError`` — o chamador não recebe um
``RepoView`` incompleto.

``RepoView`` é o estado interno do módulo (steering 12: estado interno de um
módulo fica junto do próprio módulo), não um VO de domínio.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Extensões elegíveis à inspeção estática de imports/arquivos (Fase 1). Restringe
# a leitura a texto-fonte relevante para as heurísticas, evitando binários e
# artefatos irrelevantes — mantém a visão determinística e enxuta.
_ELIGIBLE_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".txt", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".md", ".json"}
)

# Diretórios ignorados na varredura: ambientes, caches e metadados de VCS não
# fazem parte da superfície do agente-alvo e poluiriam as heurísticas.
_IGNORED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".hypothesis",
        "node_modules",
        ".tox",
        ".eggs",
        "dist",
        "build",
    }
)

# Limite de tamanho por arquivo (bytes) para leitura em memória. Arquivos acima
# do limite não são conteúdo-fonte relevante às heurísticas; são pulados (não
# constituem falha de leitura íntegra).
_MAX_FILE_BYTES: int = 2 * 1024 * 1024


class RepoReadError(RuntimeError):
    """Falha ao ler o repositório-alvo de forma íntegra (Requisito 2.6).

    Sinaliza que a entrada não pôde ser inspecionada integralmente — arquivo ou
    conteúdo inacessível. Quando levantada, **nenhum** ``RepoView`` parcial é
    produzido: o ``Static_Inspector`` aborta sem Draft parcial. Nomeia o caminho
    afetado e um motivo já sanitizado; nunca carrega valores de segredo.
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"Leitura incompleta do alvo em '{source}': {reason}")


@dataclass(frozen=True)
class RepoView:
    """Visão imutável e ordenada do repositório-alvo (Requisitos 2.3, 2.4).

    Estado interno do ``repo_reader`` — não é VO de domínio. Contém os arquivos
    elegíveis do artefato resolvido como pares ``(caminho_relativo, conteúdo)``,
    ordenados por caminho (ASCII, case-sensitive) de forma total, estável e
    independente da ordem de varredura do filesystem, garantindo determinismo
    byte-a-byte da inspeção (Requisito 2.1).

    Campos:
        root: caminho absoluto (POSIX) da raiz inspecionada, para referência.
        files: par ``(path, content)`` por arquivo, imutável e ordenado por
            ``path``. ``path`` é relativo à raiz, em formato POSIX.
    """

    root: str
    files: tuple[tuple[str, str], ...] = ()

    def paths(self) -> tuple[str, ...]:
        """Retorna os caminhos relativos (POSIX), na ordem estável da visão."""
        return tuple(path for path, _ in self.files)


def read_target(resolved_ref: str) -> RepoView:
    """Lê o artefato resolvido no filesystem local e devolve um ``RepoView``.

    Varre recursivamente o caminho ``resolved_ref`` (arquivo único ou diretório),
    coletando os arquivos elegíveis e seus conteúdos numa visão **imutável e
    ordenada** (Requisitos 2.3, 2.4). Sem rede e sem LLM — o módulo não importa
    ``agno``/``boto3``/cliente HTTP (Requisito 2.3).

    Args:
        resolved_ref: caminho do artefato-alvo já resolvido/normalizado (o
            ``Static_Inspector`` resolve a referência antes de chamar aqui).

    Returns:
        ``RepoView`` com os arquivos elegíveis ordenados por caminho.

    Raises:
        RepoReadError: se a raiz não existir ou se qualquer arquivo elegível não
            puder ser lido integralmente; nesse caso **nenhuma** visão parcial é
            devolvida (Requisito 2.6).
    """
    root = Path(resolved_ref)
    if not root.exists():
        raise RepoReadError(resolved_ref, "caminho do alvo não encontrado")

    if root.is_file():
        collected = _read_single_file(root, root.parent)
        root_str = root.parent.resolve().as_posix()
    else:
        collected = _read_directory(root)
        root_str = root.resolve().as_posix()

    # Ordenação total e estável por caminho (ASCII, case-sensitive), independente
    # da ordem de varredura do filesystem (Requisito 2.4).
    ordered = tuple(sorted(collected, key=lambda pair: pair[0]))
    return RepoView(root=root_str, files=ordered)


def _read_directory(root: Path) -> list[tuple[str, str]]:
    """Coleta os arquivos elegíveis de um diretório, abortando se algum falhar."""
    collected: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if _is_in_ignored_dir(path.relative_to(root)):
            continue
        if not path.is_file():
            continue
        if path.suffix not in _ELIGIBLE_SUFFIXES:
            continue
        content = _read_file_content(path)
        if content is None:
            continue  # arquivo grande demais / não-elegível: pulado sem falha
        rel = path.relative_to(root).as_posix()
        collected.append((rel, content))
    return collected


def _read_single_file(path: Path, base: Path) -> list[tuple[str, str]]:
    """Coleta um único arquivo-alvo (quando ``resolved_ref`` aponta um arquivo)."""
    content = _read_file_content(path)
    if content is None:
        raise RepoReadError(
            path.as_posix(), "arquivo excede o tamanho máximo de leitura"
        )
    return [(path.relative_to(base).as_posix(), content)]


def _read_file_content(path: Path) -> str | None:
    """Lê o conteúdo textual de ``path`` ou aborta com ``RepoReadError``.

    Retorna ``None`` para arquivos acima do limite de tamanho (pulados, não é
    falha de integridade). Qualquer erro de I/O ou de decodificação constitui
    leitura incompleta e levanta ``RepoReadError`` (Requisito 2.6).
    """
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RepoReadError(
            path.as_posix(), f"conteúdo não decodificável como UTF-8: {exc.reason}"
        ) from exc
    except OSError as exc:
        raise RepoReadError(
            path.as_posix(), f"arquivo ou conteúdo inacessível: {exc.strerror}"
        ) from exc


def _is_in_ignored_dir(relative_path: Path) -> bool:
    """Indica se algum componente do caminho relativo é um diretório ignorado."""
    return any(part in _IGNORED_DIR_NAMES for part in relative_path.parts)


__all__ = ["RepoReadError", "RepoView", "read_target"]
