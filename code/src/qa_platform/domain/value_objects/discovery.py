"""DiscoveryInfo, DetectedItem e Framework: VOs puros da inspeção estática.

Representam o que a inspeção estática do repositório-alvo detectou (framework,
tools, prompts, indícios de RAG). São código de domínio puro: sem qualquer
import de framework de orquestração (Agno), parser de YAML, Pydantic ou de
infraestrutura/interface (Requisitos 4.5, 5.1, 10.5). Todos são value objects
imutáveis, comparados por valor.

Caráter documental/advisory (Requisitos 4.5, 4.6): ``DiscoveryInfo`` descreve o
que foi observado por heurística — não emite veredito nem altera o roteamento
das camadas de QA. As heurísticas podem gerar falso positivo/negativo e exigem
revisão do Developer (``fragility_note``, Requisito 3.5).
"""

from dataclasses import dataclass
from enum import Enum


class Framework(str, Enum):
    """Framework de agente detectado por heurística estática (Requisito 3).

    Herda de ``str`` para serialização/comparação diretas com strings. O valor
    ``NOT_DETECTED`` cobre o caso em que nenhum framework foi identificado
    (Requisito 3.4).
    """

    AGNO = "agno"
    LANGGRAPH = "langgraph"
    NOT_DETECTED = "not_detected"


@dataclass(frozen=True)
class DetectedItem:
    """Item detectado (tool/prompt/indício de RAG) com sua origem.

    Value object imutável e comparável por valor (Requisitos 4.1–4.3).

    Campos:
        identifier: identificador do item detectado (ex.: nome da tool/prompt).
        source: origem do achado (ex.: caminho do arquivo onde foi detectado).
    """

    identifier: str
    source: str


@dataclass(frozen=True)
class DiscoveryInfo:
    """O que a inspeção estática detectou. Documental/derivado (Req 4.5, 4.6).

    Value object imutável e comparável por valor. Usa ``tuple`` para todas as
    coleções, preservando imutabilidade e ordenação estável.

    Campos:
        framework: framework predominante detectado; ``NOT_DETECTED`` quando
            nenhum foi identificado (Requisito 3.4).
        frameworks_detected: todos os frameworks detectados; contém mais de um
            quando a detecção é ambígua (Requisito 3.3).
        ambiguous: indica detecção ambígua (mais de um framework, Requisito 3.3).
        tools: tools detectadas, cada uma com identificador e origem.
        prompts: prompts detectados, cada um com identificador e origem.
        rag: indícios de RAG detectados, cada um com identificador e origem.
        fragility_note: nota fixa de fragilidade — heurísticas podem gerar
            falso positivo/negativo e exigem revisão (Requisito 3.5).
    """

    framework: Framework = Framework.NOT_DETECTED
    frameworks_detected: tuple[Framework, ...] = ()
    ambiguous: bool = False
    tools: tuple[DetectedItem, ...] = ()
    prompts: tuple[DetectedItem, ...] = ()
    rag: tuple[DetectedItem, ...] = ()
    fragility_note: str = ""

    @classmethod
    def empty(cls) -> "DiscoveryInfo":
        """Retorna um ``DiscoveryInfo`` vazio/default (nada detectado)."""
        return cls()
