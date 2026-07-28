"""Validate reusable stage-bounded portfolio product-truth bundles."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import sha256_file
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.supervisor.portfolio_scheduler.contracts import StageReceiptV1
from readme_agent.supervisor.product_truth import load_prepared_product_truth
from readme_agent.supervisor.stage_limit import (
    ReadmePocStageLimitV1,
    lifecycle_stage_reaches_limit,
)


def _checksum_inventory_valid(bundle_dir: Path) -> bool:
    inventory_path = bundle_dir / "sha256sums.txt"
    if not inventory_path.is_file():
        return False
    try:
        expected: dict[str, str] = {}
        for line in inventory_path.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", maxsplit=1)
            if (
                len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or not relative
                or relative in expected
            ):
                return False
            expected[relative] = digest
    except (OSError, UnicodeError, ValueError):
        return False
    actual = {
        path.relative_to(bundle_dir).as_posix(): path
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != "sha256sums.txt"
    }
    return set(expected) == set(actual) and all(
        sha256_file(actual[relative])[0] == digest for relative, digest in expected.items()
    )


def completed_bounded_product_truth_status(
    backend: StateBackend,
    org_repo: str,
    bundle_dir: Path,
    requested_stage: ReadmePocStageLimitV1,
) -> str | None:
    """Return a reusable bounded status only under current truth contracts."""

    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if (
        not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or not lifecycle.source_revision
        or not lifecycle_stage_reaches_limit(requested_stage, lifecycle.status)
    ):
        return None
    prepared = load_prepared_product_truth(
        org_repo,
        backend,
        lifecycle.source_revision,
    )
    if prepared is None or not lifecycle_stage_reaches_limit(
        requested_stage,
        prepared.lifecycle_status,
    ):
        return None
    refreshed = backend.load(org_repo)
    refreshed_lifecycle = refreshed.readme_poc_lifecycle if refreshed is not None else None
    if (
        not isinstance(refreshed_lifecycle, ReadmePocLifecycleStateV2)
        or refreshed_lifecycle.source_revision != lifecycle.source_revision
        or refreshed_lifecycle.status != prepared.lifecycle_status
    ):
        return None
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file() or not _checksum_inventory_valid(bundle_dir):
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        manifest.get("org_repo") != org_repo
        or manifest.get("source_revision") != refreshed_lifecycle.source_revision
        or manifest.get("lifecycle_status") != prepared.lifecycle_status
        or manifest.get("facts_hash") != prepared.facts.canonical_hash()
        or requested_stage not in manifest.get("completed_stages", [])
    ):
        return None
    if requested_stage in {"CANDIDATE_GENERATED", "DETERMINISTIC_VALIDATED"}:
        receipt_record = (manifest.get("stage_receipts") or {}).get(requested_stage)
        if not isinstance(receipt_record, dict):
            return None
        receipt_relative = receipt_record.get("receipt_path")
        if not isinstance(receipt_relative, str):
            return None
        receipt_path = bundle_dir / receipt_relative
        try:
            receipt = StageReceiptV1.model_validate_json(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            return None
        if (
            receipt.target_stage != requested_stage
            or receipt.org_repo != org_repo
            or receipt.source_revision != refreshed_lifecycle.source_revision
            or receipt.campaign_id != manifest.get("campaign_id")
            or receipt.work_id != receipt_record.get("work_id")
            or receipt.output_hash != receipt_record.get("output_hash")
        ):
            return None
    return prepared.lifecycle_status
