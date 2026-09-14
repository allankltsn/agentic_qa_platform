"""Schema e validador do ``QA_Target_Manifest`` (Requisitos 8.1, 8.2, 8.3).

Define o carregamento do JSON Schema do manifesto e um validador que verifica um
``dict`` de manifesto já parseado contra esse schema. O validador **agrega todos**
os campos problemáticos em uma única passada — campos obrigatórios ausentes, tipos
inválidos e valores fora do conjunto/limites permitidos — e, havendo qualquer
problema, levanta ``InvalidManifestError`` nomeando **cada** campo com o respectivo
motivo (Requisito 8.3). Não falha no primeiro erro: valida o manifesto completo
antes de retornar sucesso (Requisito 8.2).

Este é código de infraestrutura: o schema (JSON) e a mecânica de validação vivem
aqui, fora do domínio. Nenhum tipo de infraestrutura vaza para o domínio.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from qa_platform.domain.exceptions import InvalidManifestError

# Caminho do JSON Schema versionado em ``code/schemas/qa-target.schema.json``.
# Sobe de ``.../infrastructure/manifest/schema.py`` até a raiz de ``code/``.
_SCHEMA_PATH = Path(__file__).resolve().parents[4] / "schemas" / "qa-target.schema.json"


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Carrega e cacheia o JSON Schema do ``QA_Target_Manifest``.

    O schema é lido do arquivo versionado em ``code/schemas`` uma única vez por
    processo (cache). Retorna o schema como ``dict`` puro.

    Raises:
        FileNotFoundError: se o arquivo de schema não for encontrado.
    """
    with _SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema: dict[str, Any] = json.load(schema_file)
    return schema


def _type_name(value: Any) -> str:
    """Nome legível do tipo JSON de ``value`` para mensagens de erro."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _matches_type(value: Any, expected: str) -> bool:
    """Indica se ``value`` corresponde ao ``type`` JSON esperado do schema."""
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        # ``bool`` é subtipo de ``int`` em Python; não conta como number.
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _matches_any_type(value: Any, expected: str | list[str]) -> bool:
    """Indica se ``value`` corresponde ao ``type`` esperado (``str`` ou lista).

    Quando ``expected`` é uma lista de tipos JSON (ex.: ``["string", "null"]``),
    o valor é considerado válido se casar com **qualquer** um dos tipos listados.
    Quando é uma ``str``, o comportamento é idêntico a :func:`_matches_type`.
    """
    if isinstance(expected, list):
        return any(_matches_type(value, item) for item in expected)
    return _matches_type(value, expected)


def _format_expected_type(expected: str | list[str]) -> str:
    """Formata o ``type`` esperado para mensagens de erro (``str`` ou lista)."""
    if isinstance(expected, list):
        return ", ".join(expected)
    return expected


def _validate_node(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: dict[str, str],
) -> None:
    """Valida ``value`` contra ``schema`` acumulando problemas em ``errors``.

    Percorre recursivamente objetos, arrays e ``additionalProperties`` mapeados,
    registrando cada campo problemático em ``errors`` (nome -> motivo) sem
    interromper a validação (Requisitos 8.2, 8.3).
    """
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_any_type(value, expected_type):
        errors[path] = (
            f"tipo inválido: esperado {_format_expected_type(expected_type)}, "
            f"obtido {_type_name(value)}"
        )
        return  # sem o tipo correto, validações filhas não se aplicam

    # Quando ``type`` é uma lista (ex.: ``["string", "null"]``), o valor já
    # casou com um dos tipos acima; o ramo de validação segue a forma concreta
    # do valor. Comportamento com ``type`` como ``str`` permanece idêntico.
    if isinstance(value, dict):
        _validate_object(value, schema, path, errors)
    elif isinstance(value, list):
        _validate_array(value, schema, path, errors)
    else:
        _validate_scalar(value, schema, path, errors)


def _validate_object(
    value: dict[str, Any],
    schema: dict[str, Any],
    path: str,
    errors: dict[str, str],
) -> None:
    """Valida ``value`` (objeto) contra ``schema``, acumulando problemas."""
    properties: dict[str, Any] = schema.get("properties", {})
    additional = schema.get("additionalProperties")

    for required_field in schema.get("required", []):
        if required_field not in value:
            field_path = _join(path, required_field)
            errors[field_path] = "campo obrigatório ausente"

    min_props = schema.get("minProperties")
    if min_props is not None and len(value) < min_props:
        errors[path] = f"deve conter ao menos {min_props} propriedade(s)"

    for key, sub_value in value.items():
        field_path = _join(path, key)
        if key in properties:
            _validate_node(sub_value, properties[key], field_path, errors)
        elif isinstance(additional, dict):
            _validate_node(sub_value, additional, field_path, errors)
        elif additional is False:
            errors[field_path] = "campo não permitido pelo schema"


def _validate_array(
    value: list[Any],
    schema: dict[str, Any],
    path: str,
    errors: dict[str, str],
) -> None:
    """Valida ``value`` (array) contra ``schema``, acumulando problemas."""
    min_items = schema.get("minItems")
    if min_items is not None and len(value) < min_items:
        errors[path] = f"deve conter ao menos {min_items} item(ns)"

    if schema.get("uniqueItems") and _has_duplicates(value):
        errors[path] = "itens duplicados não são permitidos"

    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            _validate_node(item, item_schema, f"{path}[{index}]", errors)


def _validate_scalar(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: dict[str, str],
) -> None:
    """Valida restrições de escalares (string/number/null), acumulando problemas.

    Suporta ``enum`` (conjunto fechado de valores permitidos, podendo incluir
    ``None`` — ex.: o campo ``framework``): valor fora do conjunto é registrado
    em ``errors`` nomeando o campo, sem interromper a validação (Requisito 5.7).
    """
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors[path] = f"valor fora do conjunto permitido: {enum}"

    min_length = schema.get("minLength")
    if min_length is not None and isinstance(value, str) and len(value) < min_length:
        errors[path] = (
            "valor vazio ou muito curto"
            if min_length == 1
            else f"comprimento mínimo é {min_length}"
        )

    minimum = schema.get("minimum")
    if (
        minimum is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < minimum
    ):
        errors[path] = f"valor fora do limite: deve ser >= {minimum}"


def _has_duplicates(items: list[Any]) -> bool:
    """Indica se ``items`` contém valores repetidos (comparação por valor)."""
    seen: list[Any] = []
    for item in items:
        if item in seen:
            return True
        seen.append(item)
    return False


def _join(path: str, field: str) -> str:
    """Compõe o caminho pontuado de um campo para mensagens de erro."""
    return field if not path else f"{path}.{field}"


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Valida ``manifest`` contra o schema, agregando todos os problemas.

    Verifica o manifesto completo contra o JSON Schema antes de retornar
    sucesso (Requisito 8.2). Não falha no primeiro erro: coleta **todos** os
    campos problemáticos — obrigatórios ausentes, tipo inválido e valor fora do
    conjunto/limites — em uma única passada e, havendo qualquer um, levanta
    ``InvalidManifestError`` nomeando **cada** campo com o motivo (Requisito 8.3).

    Args:
        manifest: manifesto já parseado como ``dict`` (ex.: saída do parser YAML).

    Raises:
        InvalidManifestError: quando um ou mais campos são inválidos; agrega
            todos os campos problemáticos com o respectivo motivo.
    """
    errors: dict[str, str] = {}
    _validate_node(manifest, load_schema(), "", errors)
    if errors:
        raise InvalidManifestError(errors)
