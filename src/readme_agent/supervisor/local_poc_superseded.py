"""Preserve invalidated local README bundles as immutable superseded evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, sha256_file, write_redacted_json

_EVIDENCE_DIRECTORIES = ("facts", "assessment", "planning", "candidate", "review", "receipts")
_DOWNSTREAM_DIRECTORIES = ("assessment", "planning", "candidate", "review")
_DOWNSTREAM_RECEIPT_STAGES = frozenset(
    {
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATION_FAILED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
        "AGENT_REVIEW_REJECTED",
        "REPAIRING",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_REVIEW_READY",
        "HUMAN_ACCEPTED",
        "PR_ELIGIBLE",
        "PR_PROOF_COMPLETE",
    }
)
_DIRECTORY_HASH_LENGTH = 16


def preserve_superseded_candidate(
    bundle_dir: Path,
    prior_manifest: dict,
    *,
    reason: str,
) -> str | None:
    """Snapshot one displaced candidate and its evidence without inventing acceptance."""

    candidate_path = bundle_dir / "candidate" / "README.md"
    if not candidate_path.is_file():
        return None
    candidate_hash = sha256_file(candidate_path)[0]
    destination = bundle_dir / "superseded" / candidate_hash[:_DIRECTORY_HASH_LENGTH]
    preserved_candidate = destination / "candidate" / "README.md"
    if preserved_candidate.is_file():
        if sha256_file(preserved_candidate)[0] != candidate_hash:
            raise RuntimeError(f"superseded candidate hash collision in {destination}")
        record_path = destination / "superseded.json"
        if not record_path.is_file():
            raise RuntimeError(f"superseded candidate record is missing in {destination}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("candidate_hash") != candidate_hash:
            raise RuntimeError(f"superseded candidate identity collision in {destination}")
        return candidate_hash

    destination.mkdir(parents=True, exist_ok=False)
    for name in _EVIDENCE_DIRECTORIES:
        source = bundle_dir / name
        if source.is_dir():
            shutil.copytree(source, destination / name)
    for name in ("manifest.json", "sha256sums.txt"):
        source = bundle_dir / name
        if source.is_file():
            shutil.copy2(source, destination / name)
    manifest_candidate_hash = prior_manifest.get("candidate_hash")
    write_redacted_json(
        destination / "superseded.json",
        {
            "schema_version": 1,
            "candidate_hash": candidate_hash,
            "source_revision": prior_manifest.get("source_revision"),
            "prior_lifecycle_status": prior_manifest.get("lifecycle_status"),
            "prior_manifest_candidate_hash": manifest_candidate_hash,
            "candidate_binding": (
                "manifest_bound"
                if manifest_candidate_hash == candidate_hash
                else "retained_artifact_without_current_manifest_binding"
            ),
            "reason": reason,
        },
    )
    refresh_sha256sums(destination)
    return candidate_hash


def archive_and_prune_downstream_artifacts(
    bundle_dir: Path,
    prior_manifest: dict,
    *,
    reason: str,
) -> dict:
    """Archive a physical candidate, then remove artifacts invalid below product truth."""

    preserve_superseded_candidate(bundle_dir, prior_manifest, reason=reason)
    for name in _DOWNSTREAM_DIRECTORIES:
        path = bundle_dir / name
        if path.is_dir():
            shutil.rmtree(path)

    receipts_dir = bundle_dir / "receipts"
    if receipts_dir.is_dir():
        for stage in _DOWNSTREAM_RECEIPT_STAGES:
            (receipts_dir / f"{stage}.json").unlink(missing_ok=True)
        if not any(receipts_dir.iterdir()):
            receipts_dir.rmdir()

    retained = dict(prior_manifest)
    stage_receipts = retained.get("stage_receipts")
    if isinstance(stage_receipts, dict):
        retained_receipts = {
            stage: receipt
            for stage, receipt in stage_receipts.items()
            if stage not in _DOWNSTREAM_RECEIPT_STAGES
        }
        if retained_receipts:
            retained["stage_receipts"] = retained_receipts
        else:
            retained.pop("stage_receipts", None)
            retained.pop("acceptance_authority", None)
    return retained


def superseded_candidate_hashes(bundle_dir: Path) -> list[str]:
    """Return the deterministic set of preserved candidate identities."""

    root = bundle_dir / "superseded"
    if not root.is_dir():
        return []
    hashes: list[str] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        record_path = path / "superseded.json"
        if not record_path.is_file():
            raise RuntimeError(f"superseded candidate record is missing in {path}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        candidate_hash = record.get("candidate_hash")
        if not isinstance(candidate_hash, str) or len(candidate_hash) != 64:
            raise RuntimeError(f"superseded candidate identity is invalid in {path}")
        hashes.append(candidate_hash)
    return sorted(hashes)
