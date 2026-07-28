"""Tests for source-proven repair of malformed Rust consumers."""

from pathlib import Path

from readme_agent.facts.rust_example_normalization import normalize_rust_public_consumer
from readme_agent.registry.models import MinimalExamplePolicy


def _rust_repo(root: Path, *, default: bool = True) -> None:
    (root / "src").mkdir()
    (root / "Cargo.toml").write_text(
        '[package]\nname = "widget-crate"\nversion = "1.0.0"\nedition = "2021"\n',
        encoding="utf-8",
    )
    derive = "#[derive(Default)]\n" if default else ""
    (root / "src" / "lib.rs").write_text(
        f"{derive}pub struct Workbook;\npub enum CellValue {{ Text }}\n",
        encoding="utf-8",
    )


def _example(code: str) -> MinimalExamplePolicy:
    return MinimalExamplePolicy(
        language="rust",
        class_name="Workbook",
        code=code,
        evidence_paths=["README.md"],
        required_symbols=["Workbook", "CellValue"],
    )


def test_non_self_contained_draft_becomes_source_proven_default_construction(
    tmp_path: Path,
) -> None:
    _rust_repo(tmp_path)
    original = _example(
        "use widget_crate::{CellValue, Workbook};\nlet workbook = Workbook::default();\n"
    )

    normalized = normalize_rust_public_consumer(tmp_path, original)

    assert normalized.code == (
        "use widget_crate::Workbook;\n\nfn main() {\n    let _workbook = Workbook::default();\n}\n"
    )
    assert normalized.class_name == "Workbook"
    assert normalized.evidence_paths == ["src/lib.rs"]
    assert normalized.required_symbols == ["Workbook"]


def test_self_contained_consumer_that_uses_every_symbol_is_preserved(tmp_path: Path) -> None:
    original = _example(
        "use widget_crate::{CellValue, Workbook};\n\n"
        "fn main() {\n"
        "    let _workbook = Workbook::default();\n"
        "    let _value = CellValue::Text;\n"
        "}\n"
    )

    assert normalize_rust_public_consumer(tmp_path, original) == original


def test_repository_without_constructible_public_type_keeps_original(tmp_path: Path) -> None:
    _rust_repo(tmp_path, default=False)
    original = _example("use widget_crate::Workbook;\n")

    assert normalize_rust_public_consumer(tmp_path, original) == original
