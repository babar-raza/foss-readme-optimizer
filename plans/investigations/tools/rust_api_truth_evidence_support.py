"""Real-repository helpers for the Rust API-truth evidence builder."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.resolver import resolve
from readme_agent.ecosystems.rust_api_schema import RustConsumerExampleV1
from readme_agent.ecosystems.rust_format_truth import extract_rust_format_evidence
from readme_agent.ecosystems.rust_package_layout import (
    inspect_rust_package_layout,
    pinned_rust_git_dependency,
)
from readme_agent.ecosystems.rust_public_api import inspect_rust_public_api
from readme_agent.facts.rust_consumer import prove_rust_consumer
from readme_agent.facts.rust_dependency_acquisition import RUST_188_IMAGE
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import capture_repository_snapshot

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


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def real_proof(
    representative: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """Resolve real public API, formats, registry state, and offline consumer."""

    snapshot = capture_repository_snapshot(require_listed(ORG_REPO), representative)
    package = inspect_rust_package_layout(representative)
    surface = inspect_rust_public_api(
        representative,
        org_repo=ORG_REPO,
        source_revision=snapshot.source_revision,
    )
    proof = prove_rust_consumer(
        snapshot,
        package,
        surface,
        RustConsumerExampleV1(
            code=EXAMPLE,
            required_symbols=sorted(EXPECTED_SYMBOLS),
        ),
    )
    registry = resolve("rust", {"name": package.package_name})
    installation = pinned_rust_git_dependency(
        package,
        org_repo=ORG_REPO,
        source_revision=snapshot.source_revision,
    )
    return (
        {
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "inventory_sha256": snapshot.inventory_sha256,
            "baseline_tree_clean": not _git(representative, "status", "--porcelain=v1"),
            "baseline_head": _git(representative, "rev-parse", "HEAD"),
        },
        surface.model_dump(mode="json"),
        proof.model_dump(mode="json"),
        {
            "found": registry.found,
            "blocked": registry.blocked,
            "detail": registry.detail,
        },
        installation,
    )


def docker_inventory() -> dict[str, list[str]]:
    """Return managed Docker resources still present after proof execution."""

    containers = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "label=readme-agent=true"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    volumes = subprocess.run(
        ["docker", "volume", "ls", "-q", "--filter", "label=readme-agent=true"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    return {"containers": sorted(containers), "volumes": sorted(volumes)}


def real_formats(surface: dict[str, Any]) -> set[tuple[str, str]]:
    """Rehydrate the surface and return its directional format pairs."""

    from readme_agent.ecosystems.rust_api_schema import RustPublicApiSurfaceV1

    return {
        (record.format, record.direction)
        for record in extract_rust_format_evidence(RustPublicApiSurfaceV1.model_validate(surface))
    }


def immutable_image() -> str:
    """Return the exact Rust image used for acquisition and offline checking."""

    return RUST_188_IMAGE
