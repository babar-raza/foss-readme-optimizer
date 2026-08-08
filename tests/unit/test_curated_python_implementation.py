from __future__ import annotations

from pathlib import Path

from readme_agent.facts.curated_python_implementation import python_implementation_components


def test_collects_checksum_bound_ms_one_and_onestore_parser_components(tmp_path: Path) -> None:
    parser = tmp_path / "src" / "aspose" / "note" / "_internal" / "onestore" / "parser.py"
    parser.parent.mkdir(parents=True)
    parser.write_text("def parse():\n    return None\n", encoding="utf-8")
    loader = tmp_path / "src" / "aspose" / "note" / "_internal" / "ms_one" / "loader.py"
    loader.parent.mkdir(parents=True)
    loader.write_text("def load():\n    return None\n", encoding="utf-8")

    result = python_implementation_components(tmp_path)

    assert result is not None
    value, locations = result
    assert locations == [
        "src/aspose/note/_internal/ms_one/loader.py",
        "src/aspose/note/_internal/onestore/parser.py",
    ]
    assert {label for item in value["components"] for label in item["labels"]} == {
        "MS-ONE",
        "OneStore",
    }
    assert all(len(item["source_sha256"]) == 64 for item in value["components"])


def test_ignores_generic_parser_without_a_named_repository_technology(tmp_path: Path) -> None:
    parser = tmp_path / "src" / "package" / "parser.py"
    parser.parent.mkdir(parents=True)
    parser.write_text("pass\n", encoding="utf-8")

    assert python_implementation_components(tmp_path) is None
