"""Real Cells/Rust public-API and locked offline consumer proof."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from readme_agent.ecosystems.resolver import resolve
from readme_agent.ecosystems.rust_api_schema import RustConsumerExampleV1
from readme_agent.ecosystems.rust_format_truth import extract_rust_format_evidence
from readme_agent.ecosystems.rust_package_layout import (
    inspect_rust_package_layout,
    pinned_rust_git_dependency,
)
from readme_agent.ecosystems.rust_public_api import inspect_rust_public_api
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.rust_consumer import prove_rust_consumer
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import capture_repository_snapshot

REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_RUST_REPRESENTATIVE",
        "runs/baseline/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust",
    )
)
ORG_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
EXPECTED_SYMBOLS = {
    "aspose_cells_foss_rust::Workbook",
    "aspose_cells_foss_rust::Workbook.new",
    "aspose_cells_foss_rust::Workbook.save_xlsx_to_bytes",
}
EXAMPLE = (
    "use aspose_cells_foss_rust::Workbook;\n"
    "fn main() {\n"
    "    let workbook = Workbook::new();\n"
    "    let _bytes = workbook.save_xlsx_to_bytes();\n"
    "}\n"
)


def _snapshot_and_surface():
    if not REPRESENTATIVE.is_dir():
        pytest.skip("real Cells/Rust baseline clone is unavailable")
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, REPRESENTATIVE)
    package = inspect_rust_package_layout(REPRESENTATIVE)
    surface = inspect_rust_public_api(
        REPRESENTATIVE,
        org_repo=ORG_REPO,
        source_revision=snapshot.source_revision,
    )
    return snapshot, package, surface


@pytest.mark.live
def test_real_cells_rust_public_api_formats_and_unpublished_source_acquisition():
    snapshot, package, surface = _snapshot_and_surface()
    names = {symbol.qualified_name for symbol in surface.symbols}
    formats = {
        (record.format, record.direction) for record in extract_rust_format_evidence(surface)
    }
    registry = resolve("rust", {"name": package.package_name})

    assert EXPECTED_SYMBOLS <= names
    assert not any("pub(crate)" in symbol.visibility_evidence for symbol in surface.symbols)
    assert ("xlsx", "export") in formats
    assert ("xlsx", "import") in formats
    assert registry.blocked is False
    assert registry.found is False
    assert package.acquisition == "pinned_source"
    dependency = pinned_rust_git_dependency(
        package,
        org_repo=ORG_REPO,
        source_revision=snapshot.source_revision,
    )
    assert package.package_name in dependency
    assert snapshot.source_revision in dependency
    assert "github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust" in dependency


@pytest.mark.live
def test_real_cells_rust_locked_offline_external_consumer():
    snapshot, package, surface = _snapshot_and_surface()
    proof = prove_rust_consumer(
        snapshot,
        package,
        surface,
        RustConsumerExampleV1(
            code=EXAMPLE,
            required_symbols=sorted(EXPECTED_SYMBOLS),
        ),
    )

    assert proof.accepted is True, proof
    assert set(proof.verified_symbols) == EXPECTED_SYMBOLS
    assert proof.acquisition.lock_package_count > 1
    assert proof.acquisition.network_mode == "bridge"
    assert proof.acquisition.cleanup_complete is True
    assert proof.isolated_execution.policy.network_mode == "none"
    assert proof.isolated_execution.cleanup.complete is True


@pytest.mark.live
def test_canonical_local_verifier_uses_isolated_rust_consumer():
    snapshot, package, _surface = _snapshot_and_surface()
    verification = verify_local_product_example(
        snapshot,
        MinimalExamplePolicy(
            language="rust",
            class_name="readme_example",
            code=EXAMPLE,
            evidence_paths=[
                "src/Aspose.Cells_FOSS/Workbook.rs",
                "src/lib.rs",
            ],
            required_symbols=sorted(EXPECTED_SYMBOLS),
        ),
    )

    assert verification.outcome == "SOURCE_BUILD_VERIFIED", verification
    assert verification.truth_eligible is True
    assert verification.rust_package == package
    assert set(verification.verified_public_symbols) == EXPECTED_SYMBOLS
    assert verification.rust_source_dependency is not None
    assert verification.isolated_execution is not None
    assert verification.isolated_execution.policy.network_mode == "none"
    assert verification.isolated_execution.cleanup.complete is True
