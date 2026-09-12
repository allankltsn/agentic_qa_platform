"""Manifest_Parser: lê ``qa-target.yaml`` e produz o VO puro do domínio.

Lê o manifesto YAML com o PyYAML (importado como ``yaml``), valida o ``dict``
resultante contra o JSON Schema (Requisito 8.2) e o mapeia para o value object
puro ``QATargetManifest`` do domínio. O tipo do parser YAML **não vaza** para
fora da infraestrutura: as funções públicas retornam apenas o VO de domínio,
mantendo o domínio livre de qualquer dependência de parser (Requisitos 8.1, 12.1).

Este é código de infraestrutura — o único ponto do sistema autorizado a importar
``yaml`` para o manifesto, conforme o contrato do import-linter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from qa_platform.domain.value_objects.ids import LayerId
from qa_platform.domain.entities.manifest import (
    CostParameters,
    QATargetManifest,
    RiskParameters,
)
from qa_platform.infrastructure.manifest.schema import validate_manifest


def parse_manifest_text(text: str) -> QATargetManifest:
    """Faz o parse do conteúdo YAML ``text`` para um ``QATargetManifest``.

    Lê o texto com o PyYAML de forma segura (``safe_load``), valida contra o
    schema (Requisito 8.2) e constrói o VO puro do domínio. O tipo do parser
    YAML não escapa desta função (Requisito 12.1).

    Args:
        text: conteúdo do manifesto ``qa-target.yaml`` como string.

    Returns:
        O ``QATargetManifest`` puro correspondente ao manifesto.

    Raises:
        InvalidManifestError: se o manifesto não estiver conforme o schema,
            nomeando cada campo problemático (Requisito 8.3).
    """
    loaded: Any = yaml.safe_load(text)
    raw: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
    validate_manifest(raw)
    return _to_domain(raw)


def parse_manifest_file(path: str | Path) -> QATargetManifest:
    """Lê o arquivo em ``path`` e faz o parse para um ``QATargetManifest``.

    Args:
        path: caminho para o arquivo ``qa-target.yaml``.

    Returns:
        O ``QATargetManifest`` puro correspondente ao arquivo.

    Raises:
        InvalidManifestError: se o manifesto não estiver conforme o schema.
        OSError: se o arquivo não puder ser lido.
    """
    text = Path(path).read_text(encoding="utf-8")
    return parse_manifest_text(text)


def _to_domain(raw: dict[str, Any]) -> QATargetManifest:
    """Mapeia o ``dict`` validado para o VO puro ``QATargetManifest``.

    Constrói ``LayerId``, ``RiskParameters`` e ``CostParameters`` a partir do
    manifesto já validado. Assume conformidade com o schema (o chamador validou
    antes), portanto os campos obrigatórios estão presentes e bem tipados.
    """
    target: dict[str, Any] = raw["target"]
    applicable_layers = tuple(
        LayerId(layer_id) for layer_id in raw["applicable_layers"]
    )

    risk_parameters = {
        LayerId(layer_id): RiskParameters(weight=float(params["weight"]))
        for layer_id, params in raw["risk_parameters"].items()
    }

    cost_parameters = {
        LayerId(layer_id): CostParameters(
            risk_threshold=float(params.get("risk_threshold", 0.0)),
            estimated_risk=float(params.get("estimated_risk", 0.0)),
        )
        for layer_id, params in raw.get("cost_parameters", {}).items()
    }

    return QATargetManifest(
        target_ref=str(target["ref"]),
        target_version=str(target["version"]),
        applicable_layers=applicable_layers,
        risk_parameters=risk_parameters,
        cost_parameters=cost_parameters,
    )
