"""Gate R6c: real, structured dependency evidence -- the DependencySnapshot
readme_refresh_checks.py's dependency_snapshot-parameterized checks (MT041)
have expected since their authoring, but that this repo never built until
now (confirmed: the underlying PEP 621/517 readers this module reuses were
themselves unused anywhere in the codebase)."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.dependency_snapshot import (
    build_dependency_snapshot,
    dependency_snapshot_fact_record,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_python_manifest_separates_required_optional_and_development(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
dependencies = ["olefile>=0.46", "pycryptodome>=3.15.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
""",
    )

    snapshot = build_dependency_snapshot(tmp_path, "python")

    assert snapshot.applicable is True
    assert snapshot.parse_errors == ()
    assert snapshot.source_manifest_path == "pyproject.toml"
    assert [e.name for e in snapshot.required] == ["olefile", "pycryptodome"]
    assert snapshot.required[0].version_constraint == ">=0.46"
    assert snapshot.required[0].role == "runtime"
    assert snapshot.required[0].dev_only is False
    assert [e.name for e in snapshot.optional] == ["pytest", "pytest-cov"]
    assert [e.name for e in snapshot.development] == ["setuptools", "wheel"]
    assert snapshot.development[0].role == "build"
    assert snapshot.development[0].dev_only is True
    assert snapshot.native_system == ()
    assert snapshot.proprietary_runtime == ()


def test_python_manifest_missing_is_not_applicable_with_a_real_reason(tmp_path):
    snapshot = build_dependency_snapshot(tmp_path, "python")

    assert snapshot.applicable is False
    assert snapshot.not_applicable_reason is not None
    assert "pyproject.toml" in snapshot.not_applicable_reason
    assert "setup.py" in snapshot.not_applicable_reason
    assert snapshot.required == ()


def test_python_setup_py_literal_dependencies_are_parsed_without_execution(tmp_path):
    _write(
        tmp_path / "setup.py",
        """
from setuptools import setup

setup(
    name="widget",
    install_requires=["requests>=2", "pillow"],
    extras_require={"dev": ["pytest>=8"], "images": ["numpy>=2"]},
)
""",
    )

    snapshot = build_dependency_snapshot(tmp_path, "python")

    assert snapshot.applicable is True
    assert snapshot.source_manifest_path == "setup.py"
    assert snapshot.parse_errors == ()
    assert [entry.name for entry in snapshot.required] == ["pillow", "requests"]
    assert [entry.name for entry in snapshot.optional] == ["numpy"]
    assert [entry.name for entry in snapshot.development] == ["pytest"]


def test_python_setup_py_dynamic_dependency_expression_fails_closed(tmp_path):
    _write(
        tmp_path / "setup.py",
        "from setuptools import setup\ndeps = ['requests']\nsetup(install_requires=deps)\n",
    )

    snapshot = build_dependency_snapshot(tmp_path, "python")

    assert snapshot.applicable is True
    assert snapshot.parse_errors
    assert snapshot.required == ()


def test_rust_manifest_separates_dependencies_by_table(tmp_path):
    _write(
        tmp_path / "Cargo.toml",
        """
[package]
name = "widget"
version = "1.0.0"

[dependencies]
chrono = "0.4"
zip = { version = "0.6" }

[dev-dependencies]
tempfile = "3"

[build-dependencies]
cc = "1.0"
""",
    )

    snapshot = build_dependency_snapshot(tmp_path, "rust")

    assert snapshot.applicable is True
    assert snapshot.source_manifest_path == "Cargo.toml"
    required_names = {e.name for e in snapshot.required}
    assert required_names == {"chrono", "zip"}
    zip_entry = next(e for e in snapshot.required if e.name == "zip")
    assert zip_entry.version_constraint == "0.6"
    development_names = {e.name for e in snapshot.development}
    assert development_names == {"tempfile", "cc"}
    assert all(e.dev_only for e in snapshot.development)


def test_malformed_python_manifest_reports_parse_errors_never_crashes(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
dependencies = "not a list"
""",
    )

    snapshot = build_dependency_snapshot(tmp_path, "python")

    assert snapshot.applicable is True
    assert snapshot.parse_errors  # a real, surfaced parse failure
    assert snapshot.required == ()


def test_unsupported_ecosystem_is_explicitly_not_applicable(tmp_path):
    for ecosystem in ("java", "net", "cpp", "go", "typescript"):
        snapshot = build_dependency_snapshot(tmp_path, ecosystem)
        assert snapshot.applicable is False
        assert snapshot.not_applicable_reason is not None
        assert "not yet built" in snapshot.not_applicable_reason


def test_fact_record_is_deterministic_across_identical_manifests(tmp_path):
    _write(tmp_path / "pyproject.toml", '[project]\ndependencies = ["a>=1"]\n')

    first = dependency_snapshot_fact_record(tmp_path, "python")
    second = dependency_snapshot_fact_record(tmp_path, "python")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.source.source_revision is not None
    assert first.source.source_revision.startswith("content-sha256:")


def test_fact_record_changes_when_manifest_content_changes(tmp_path):
    _write(tmp_path / "pyproject.toml", '[project]\ndependencies = ["a>=1"]\n')
    first = dependency_snapshot_fact_record(tmp_path, "python")

    _write(tmp_path / "pyproject.toml", '[project]\ndependencies = ["a>=2"]\n')
    second = dependency_snapshot_fact_record(tmp_path, "python")

    assert first.source.source_revision != second.source.source_revision


def test_fact_record_confidence_reflects_applicability_and_parse_health(tmp_path):
    clean = dependency_snapshot_fact_record(
        tmp_path / "clean", "python"
    )  # no manifest -> not applicable
    assert clean.verification_state == "unverified"
    assert clean.confidence < 1.0
