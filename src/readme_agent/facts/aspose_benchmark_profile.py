"""Freeze and qualify the evolving Aspose.org README benchmark without runtime coupling."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json

AuditRunner = Callable[[Path, Path], dict[str, Any]]

_CANONICAL_TREE = "repo-presenter-regen-full"
_DIMENSIONS = (
    (
        "information_coverage",
        "accepted",
        "Cover the material visitor questions that have repository-verified answers.",
    ),
    (
        "product_specificity",
        "accepted",
        "Use repository-specific identity, audience, capabilities, formats, and constraints.",
    ),
    (
        "structure_and_navigation",
        "adapted",
        "Retain the useful benchmark section coverage through the local template contract.",
    ),
    (
        "branding_and_visuals",
        "adapted",
        "Use the locally approved header and Mermaid contracts rather than copying "
        "benchmark bytes.",
    ),
    (
        "capability_depth",
        "adapted",
        "Require visible, non-duplicated capabilities backed by current ProductFactsV2 evidence.",
    ),
    (
        "installation_and_dependencies",
        "adapted",
        "Render only repository-declared and independently verified acquisition routes.",
    ),
    (
        "source_derived_examples",
        "adapted",
        "Use benchmark coverage as a hint while requiring isolated verification of exact "
        "local examples.",
    ),
    (
        "api_reference_depth",
        "adapted",
        "Select useful public APIs from current local source evidence and avoid benchmark-only "
        "names.",
    ),
    (
        "documentation_and_resources",
        "accepted",
        "Provide useful verified documentation, support, contribution, and reference routes.",
    ),
    (
        "limitations",
        "accepted",
        "Keep material constraints visible, specific, and non-duplicated.",
    ),
    (
        "development_and_testing",
        "adapted",
        "Present relevant repository development guidance without exposing internal verification "
        "prose.",
    ),
    (
        "licensing",
        "accepted",
        "Explain the verified repository license and link the repository-owned license artifacts.",
    ),
    (
        "inherited_content_accountability",
        "adapted",
        "Account for valuable source README material, but verify it before reuse and normalize "
        "its tone.",
    ),
    (
        "public_tone_and_process_hygiene",
        "accepted",
        "Use professional public prose and prohibit internal validation, evidence, or workflow "
        "narration.",
    ),
    (
        "benchmark_claim_authority",
        "quarantined",
        "Benchmark claims and examples are discovery hints only and never become product truth.",
    ),
    (
        "benchmark_item_verdicts",
        "quarantined",
        "Upstream clean, dirty, skipped, and published labels do not satisfy local acceptance.",
    ),
    (
        "upstream_site_workflow_metadata",
        "not_applicable",
        "Hugo, content-site, publication, and upstream task-state metadata do not enter README "
        "runtime inputs.",
    ),
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the exact byte hash used to bind benchmark artifacts."""

    return _sha256_bytes(path.read_bytes())


def inventory_tree(root: Path) -> dict[str, Any]:
    """Build a deterministic complete file inventory for one generated tree."""

    files = [path for path in root.rglob("*") if path.is_file()]
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(files, key=lambda item: item.relative_to(root).as_posix())
    ]
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "root": str(root.resolve()),
        "file_count": len(entries),
        "tree_sha256": _sha256_bytes(encoded),
        "files": entries,
    }


def _git_snapshot(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return result.stdout.strip()

    status_entries = run("status", "--short").splitlines()
    return {
        "head": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "status_dirty": bool(status_entries),
        "status_entry_count": len(status_entries),
        "status_sha256": _sha256_bytes("\n".join(status_entries).encode("utf-8")),
        "captured_at": datetime.now(UTC).isoformat(),
    }


def build_quality_profile(*, audit: dict[str, Any], snapshot_sha256: str) -> dict[str, Any]:
    """Derive the development-only quality obligations from a complete fresh audit."""

    dimensions = [
        {
            "dimension_id": dimension_id,
            "disposition": disposition,
            "obligation": obligation,
        }
        for dimension_id, disposition, obligation in _DIMENSIONS
    ]
    counts: dict[str, int] = {}
    for dimension in dimensions:
        disposition = str(dimension["disposition"])
        counts[disposition] = counts.get(disposition, 0) + 1
    return {
        "schema_version": 1,
        "profile_type": "BenchmarkQualityProfileV1",
        "state": "BENCHMARK_PROFILE_FROZEN",
        "development_only": True,
        "runtime_dependency_on_aspose_org": False,
        "snapshot_sha256": snapshot_sha256,
        "audit_summary": {
            "total": audit.get("total"),
            "clean_count": audit.get("clean_count"),
            "dirty_count": audit.get("dirty_count"),
            "disposition_verified_count": audit.get("disposition_verified_count"),
        },
        "disposition_counts": counts,
        "dimensions": dimensions,
        "authority": {
            "facts": "current immutable product repositories through ProductFactsV2",
            "benchmark": "visitor-quality calibration and gap discovery only",
            "acceptance": "local deterministic gates plus independent 30-point review",
        },
    }


def _validate_complete_audit(audit: dict[str, Any], candidate_count: int) -> None:
    total = audit.get("total")
    skipped = audit.get("skipped")
    products = audit.get("products")
    if (
        total != candidate_count
        or not isinstance(products, list)
        or len(products) != candidate_count
    ):
        raise ValueError(
            "fresh benchmark audit denominator mismatch: "
            f"audit={total}, candidates={candidate_count}"
        )
    if skipped:
        raise ValueError(f"fresh benchmark audit skipped {len(skipped)} candidate(s)")


def refresh_benchmark_profile(
    aspose_root: Path,
    output_root: Path,
    *,
    audit_runner: AuditRunner,
) -> dict[str, Any]:
    """Freeze current generated bytes, audit an isolated copy, and write qualified evidence."""

    aspose_root = aspose_root.resolve()
    source_tree = aspose_root / "reports" / _CANONICAL_TREE
    if not source_tree.is_dir():
        raise FileNotFoundError(f"benchmark tree is missing: {source_tree}")

    prior_receipt = output_root / "receipt.json"
    prior_receipt_sha256 = sha256_file(prior_receipt) if prior_receipt.is_file() else None
    git_before = _git_snapshot(aspose_root)
    first_inventory = inventory_tree(source_tree)
    candidate_ids = sorted(
        path.parent.relative_to(source_tree).as_posix()
        for path in source_tree.glob("*/*/readme.md")
    )
    if not candidate_ids:
        raise ValueError("benchmark tree has no candidate README files")

    with tempfile.TemporaryDirectory(prefix="readme-agent-benchmark-") as temp_name:
        temp_root = Path(temp_name)
        frozen_tree = temp_root / "reports" / _CANONICAL_TREE
        shutil.copytree(source_tree, frozen_tree)
        copied_inventory = inventory_tree(frozen_tree)
        second_inventory = inventory_tree(source_tree)
        if first_inventory["files"] != copied_inventory["files"]:
            raise RuntimeError("frozen benchmark copy differs from the first source inventory")
        if first_inventory["files"] != second_inventory["files"]:
            raise RuntimeError("benchmark tree changed while it was being frozen")
        audit = audit_runner(aspose_root, temp_root / "reports")

    third_inventory = inventory_tree(source_tree)
    git_after = _git_snapshot(aspose_root)
    if first_inventory["files"] != third_inventory["files"]:
        raise RuntimeError("benchmark tree changed while the isolated audit was running")
    stable_git_fields = ("head", "branch", "status_sha256", "status_entry_count")
    if any(git_before[field] != git_after[field] for field in stable_git_fields):
        raise RuntimeError("Aspose.org producer state changed during benchmark qualification")
    _validate_complete_audit(audit, len(candidate_ids))

    snapshot = {
        "schema_version": 1,
        "snapshot_type": "DevelopmentBenchmarkSnapshotV1",
        "state": "BENCHMARK_AUDITED",
        "source_repository": str(aspose_root),
        "canonical_tree": _CANONICAL_TREE,
        "producer": git_after,
        "stability": {
            "result": "STABLE_TRIPLE_READ",
            "inventories_equal": True,
            "producer_identity_equal": True,
            "first_tree_sha256": first_inventory["tree_sha256"],
            "second_tree_sha256": second_inventory["tree_sha256"],
            "third_tree_sha256": third_inventory["tree_sha256"],
        },
        "candidate_count": len(candidate_ids),
        "candidate_ids": candidate_ids,
        "target_tree": first_inventory,
        "fresh_audit": {
            "total": audit["total"],
            "clean_count": audit["clean_count"],
            "dirty_count": audit["dirty_count"],
            "disposition_verified_count": audit.get("disposition_verified_count"),
            "skipped_count": len(audit.get("skipped", [])),
        },
        "isolation": {
            "audited_frozen_copy": True,
            "source_tree_written": False,
            "product_remote_effects": 0,
            "llm_provider_calls": 0,
        },
    }
    write_redacted_json(output_root / "development-benchmark-snapshot.json", snapshot)
    write_redacted_json(output_root / "fresh-audit.json", audit)
    snapshot_sha256 = sha256_file(output_root / "development-benchmark-snapshot.json")
    profile = build_quality_profile(audit=audit, snapshot_sha256=snapshot_sha256)
    write_redacted_json(output_root / "benchmark-quality-profile.json", profile)
    profile_sha256 = sha256_file(output_root / "benchmark-quality-profile.json")
    audit_sha256 = sha256_file(output_root / "fresh-audit.json")
    receipt = {
        "schema_version": 2,
        "lane_id": "L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY/benchmark-snapshot",
        "generated_at": datetime.now(UTC).isoformat(),
        "verdict": "BENCHMARK_PROFILE_FROZEN",
        "classification": "development_diagnostic_only",
        "prior_receipt_sha256": prior_receipt_sha256,
        "source": {
            "repository": str(aspose_root),
            "producer_head": git_after["head"],
            "producer_branch": git_after["branch"],
            "producer_status_dirty": git_after["status_dirty"],
            "producer_status_entry_count": git_after["status_entry_count"],
            "producer_status_sha256": git_after["status_sha256"],
        },
        "denominator": {
            "candidate_count": len(candidate_ids),
            "candidate_ids": candidate_ids,
            "audit_total": audit["total"],
            "audit_skipped": len(audit.get("skipped", [])),
            "complete": True,
        },
        "fresh_audit": {
            "sha256": audit_sha256,
            "clean_count": audit["clean_count"],
            "dirty_count": audit["dirty_count"],
            "item_failures_remain_diagnostic": True,
        },
        "snapshot": {
            "path": "development-benchmark-snapshot.json",
            "sha256": snapshot_sha256,
        },
        "quality_profile": {
            "path": "benchmark-quality-profile.json",
            "sha256": profile_sha256,
            "state": profile["state"],
            "disposition_counts": profile["disposition_counts"],
        },
        "runtime_contract": {
            "aspose_org_required_after_freeze": False,
            "benchmark_claims_are_facts": False,
            "benchmark_failures_can_lower_local_acceptance": False,
            "local_native_acceptance_remains_required": True,
        },
    }
    write_redacted_json(output_root / "receipt.json", receipt)
    refresh_sha256sums(output_root)
    return receipt
