"""Validate curated README examples before reuse in product truth."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.repository_examples import repository_readme_example_candidates
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import capture_repository_snapshot

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is unavailable"),
]

BASELINE_ROOT = Path("runs/baseline")


def _curated_example(org_repo: str, language: str):
    root = BASELINE_ROOT / org_repo.replace("/", "__")
    snapshot = capture_repository_snapshot(require_listed(org_repo), root)
    candidates = repository_readme_example_candidates(root, language)
    assert candidates
    return snapshot, candidates[0]


def test_python_readme_example_is_rejected_when_installed_package_cannot_import_it():
    snapshot, example = _curated_example(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "python",
    )

    result = verify_local_product_example(snapshot, example)

    assert result.outcome == "BUILD_FAILED"
    assert result.truth_eligible is False
    assert result.isolated_execution is not None
    assert "aspose.threed.formats.collada" in result.isolated_execution.stderr


def test_typescript_readme_example_is_rejected_before_stale_imports_can_be_reused():
    snapshot, example = _curated_example(
        "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
        "typescript",
    )

    result = verify_local_product_example(snapshot, example)

    assert result.outcome == "BUILD_FAILED"
    assert result.truth_eligible is False
    assert result.isolated_execution is None
    assert "one unambiguous named package import" in result.detail


def test_rust_readme_example_compiles_unchanged_against_the_pinned_source():
    snapshot, example = _curated_example(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
        "rust",
    )

    result = verify_local_product_example(snapshot, example)

    assert result.outcome == "SOURCE_BUILD_VERIFIED", result
    assert result.truth_eligible is True
    assert set(result.verified_public_symbols) == {
        "aspose_cells_foss_rust::CellValue",
        "aspose_cells_foss_rust::Workbook",
    }
    assert result.isolated_execution is not None
    assert result.isolated_execution.policy.network_mode == "none"
    assert result.isolated_execution.cleanup.complete is True
