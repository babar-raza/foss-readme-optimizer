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


def test_collects_format_io_groups_with_dependency_and_stdlib_assurance(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "words"\ndependencies = ["olefile>=0.46"]\n',
        encoding="utf-8",
    )
    docx_reader = tmp_path / "package" / "docx_reader" / "document_reader.py"
    docx_reader.parent.mkdir(parents=True)
    docx_reader.write_text(
        '"""Reads DOCX with only the standard library."""\n'
        "import zipfile\nfrom xml.etree import ElementTree\nclass DocumentReader: pass\n",
        encoding="utf-8",
    )
    docx_writer = tmp_path / "package" / "docx_writer" / "writer.py"
    docx_writer.parent.mkdir(parents=True)
    docx_writer.write_text("import zipfile\nclass DocxWriter: pass\n", encoding="utf-8")
    doc_reader = tmp_path / "package" / "doc_reader" / "doc_file_reader.py"
    doc_reader.parent.mkdir(parents=True)
    doc_reader.write_text(
        '"""Word 97-2003 binary format reader."""\nimport olefile\nclass DocFileReader: pass\n',
        encoding="utf-8",
    )

    result = python_implementation_components(tmp_path)

    assert result is not None
    value, _locations = result
    groups = {item["format"]: item for item in value["capability_groups"]}
    assert groups["DOCX"]["roles"] == ["read", "write"]
    assert groups["DOCX"]["runtime_imports"] == []
    assert groups["DOCX"]["stdlib_imports"] == ["xml.etree", "zipfile"]
    assert groups["DOC"]["label"] == "Read Word 97-2003 DOC binary documents with olefile"
    assert groups["DOC"]["runtime_imports"] == ["olefile"]


def test_does_not_treat_internal_reader_names_as_public_formats(tmp_path: Path) -> None:
    reader = tmp_path / "package" / "numbering_reader.py"
    reader.parent.mkdir(parents=True)
    reader.write_text("class NumberingReader: pass\n", encoding="utf-8")

    assert python_implementation_components(tmp_path) is None
