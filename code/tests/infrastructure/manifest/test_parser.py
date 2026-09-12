"""Teste por exemplo do Manifest_Parser (round-trip)."""

from pathlib import Path

import yaml

from qa_platform.infrastructure.manifest.parser import (
    parse_manifest_file,
    parse_manifest_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "qa-target.example.yaml"


def test_qa_target_example_faz_parse_para_vo() -> None:
    """qa-target.example.yaml faz parse para QATargetManifest (Req 8.1)."""
    manifest = parse_manifest_file(EXAMPLE_PATH)
    assert manifest.target_ref == "github.com/example/qa-platform"
    assert manifest.target_version == "1.4.2"
    assert len(manifest.applicable_layers) == 3


def test_parse_manifest_text_round_trip_estavel() -> None:
    """Parse repetido do mesmo YAML produz VO idêntico (Req 8.2)."""
    text = EXAMPLE_PATH.read_text(encoding="utf-8")
    first = parse_manifest_text(text)
    second = parse_manifest_text(text)
    assert first == second
    assert yaml.safe_load(text)["target"]["ref"] == first.target_ref
