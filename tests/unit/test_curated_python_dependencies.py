"""Tests for curated_python_dependencies.py's python_distribution_evidence()."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.curated_python_dependencies import python_distribution_evidence


def _write_manifest(root: Path, text: str) -> None:
    (root / "pyproject.toml").write_text(text, encoding="utf-8")


def test_dependency_groups_table_is_the_real_aspose_org_convention(tmp_path: Path) -> None:
    """Barcode-python's real pyproject.toml uses PEP 735 [dependency-groups], not
    [project.optional-dependencies] -- both must be supported."""

    _write_manifest(
        tmp_path,
        """
[project]
name = "aspose-barcode-foss"
dependencies = ["Pillow>=10.1.0"]

[dependency-groups]
dev = ["pytest>=8.0", "ruff>=0.15.7"]
""",
    )

    result = python_distribution_evidence(tmp_path)

    assert result is not None
    value, _locations = result
    assert value["development_dependencies"] == ["pytest>=8.0", "ruff>=0.15.7"]


def test_optional_dependencies_dev_group_is_also_supported(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
[project]
name = "example"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]
docs = ["sphinx>=7"]
""",
    )

    result = python_distribution_evidence(tmp_path)

    assert result is not None
    value, _locations = result
    assert value["development_dependencies"] == ["pytest>=8.0"]


def test_groups_are_deduped_and_flattened_across_both_tables(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
[project]
name = "example"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8.0"]

[dependency-groups]
dev = ["pytest>=8.0", "ruff>=0.15.7"]
""",
    )

    result = python_distribution_evidence(tmp_path)

    assert result is not None
    value, _locations = result
    # "dev" sorts before "test" case-insensitively; pytest is deduped across groups.
    assert value["development_dependencies"] == ["pytest>=8.0", "ruff>=0.15.7"]


def test_declared_but_empty_dev_group_is_verified_empty(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
[project]
name = "example"
dependencies = []

[dependency-groups]
dev = []
""",
    )

    result = python_distribution_evidence(tmp_path)

    assert result is not None
    value, _locations = result
    assert value["development_dependencies"] == []


def test_no_dev_test_lint_ci_group_declared_omits_the_field_entirely(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
[project]
name = "example"
dependencies = []

[project.optional-dependencies]
docs = ["sphinx>=7"]

[dependency-groups]
release = ["build>=1.0"]
""",
    )

    result = python_distribution_evidence(tmp_path)

    assert result is not None
    value, _locations = result
    assert "development_dependencies" not in value


def test_no_optional_or_dependency_groups_table_at_all_omits_the_field(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        """
[project]
name = "example"
dependencies = []
""",
    )

    result = python_distribution_evidence(tmp_path)

    assert result is not None
    value, _locations = result
    assert "development_dependencies" not in value
