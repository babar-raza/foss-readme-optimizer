"""Run one source-bound read-only intake before the normal supervisor."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.gitsafety.baseline_reuse import verified_baseline_at_revision
from readme_agent.gitsafety.clone import remote_head_sha
from readme_agent.registry.intake import (
    ReadOnlyIntakePreflightV1,
    blocked_access_intake,
    classify_readonly_intake,
    intake_contract_hash,
    system_failure_intake,
)
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import capture_repository_snapshot
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import IntakePreflightBindingV1
from readme_agent.state.readme_poc_intake import (
    begin_readonly_intake_preflight,
    complete_readonly_intake_preflight,
    intake_preflight_dedup_key,
)


@dataclass(frozen=True)
class ReadonlyIntakeExecution:
    """Public command adapter result for one logical intake."""

    binding: IntakePreflightBindingV1
    executed: bool
    resumed: bool = False


def run_readonly_intake_preflight(
    entry: ProductEntry,
    backend: StateBackend,
    *,
    source_revision: str | None = None,
) -> ReadonlyIntakeExecution:
    """Inspect through the neutered local clone and persist one result."""

    identity = entry.provider_identity
    if identity is None:
        raise ValueError(f"{entry.org_repo!r} has no stable provider identity")
    contract_hash = intake_contract_hash(entry)
    probed_revision = source_revision or remote_head_sha(entry.clone_url)
    if probed_revision is None:
        source_revision = hashlib.sha256(
            f"unresolved:{identity.repository_id}".encode()
        ).hexdigest()
        result = blocked_access_intake(
            entry,
            source_revision,
            "default-branch revision was unavailable through read-only git inspection",
        )
        return _persist_result(entry, backend, result)

    dedup_key = intake_preflight_dedup_key(
        entry.org_repo,
        identity.repository_id,
        probed_revision,
        contract_hash,
    )
    acceptance = begin_readonly_intake_preflight(
        backend,
        entry.org_repo,
        dedup_key=dedup_key,
        source_revision=probed_revision,
    )
    if not acceptance.should_execute:
        assert acceptance.completed is not None
        return ReadonlyIntakeExecution(acceptance.completed, executed=False)

    try:
        baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
        verified_baseline_at_revision(
            entry,
            baseline_path,
            expected_revision=probed_revision,
        )
        snapshot = capture_repository_snapshot(entry, baseline_path)
        if snapshot.source_revision != probed_revision:
            result = system_failure_intake(
                entry,
                probed_revision,
                "default branch moved between the intake probe and immutable snapshot",
            )
        else:
            result = classify_readonly_intake(entry, snapshot)
    except Exception as exc:  # noqa: BLE001 -- converted to a visible retryable intake receipt
        result = system_failure_intake(
            entry,
            probed_revision,
            f"read-only intake failed at {type(exc).__name__}",
        )
    return _complete_result(
        entry,
        backend,
        result,
        dedup_key=dedup_key,
        attempt=acceptance.reservation.attempt if acceptance.reservation is not None else 1,
        resumed=acceptance.resumed,
    )


def _persist_result(
    entry: ProductEntry,
    backend: StateBackend,
    result: ReadOnlyIntakePreflightV1,
) -> ReadonlyIntakeExecution:
    identity = entry.provider_identity
    assert identity is not None
    dedup_key = intake_preflight_dedup_key(
        entry.org_repo,
        identity.repository_id,
        result.source_revision,
        result.contract_hash,
    )
    acceptance = begin_readonly_intake_preflight(
        backend,
        entry.org_repo,
        dedup_key=dedup_key,
        source_revision=result.source_revision,
        source_revision_resolved=result.source_revision_resolved,
    )
    if not acceptance.should_execute:
        assert acceptance.completed is not None
        return ReadonlyIntakeExecution(acceptance.completed, executed=False)
    return _complete_result(
        entry,
        backend,
        result,
        dedup_key=dedup_key,
        attempt=acceptance.reservation.attempt if acceptance.reservation is not None else 1,
        resumed=acceptance.resumed,
    )


def _complete_result(
    entry: ProductEntry,
    backend: StateBackend,
    result: ReadOnlyIntakePreflightV1,
    *,
    dedup_key: str,
    attempt: int,
    resumed: bool,
) -> ReadonlyIntakeExecution:
    evidence_path = _write_intake_evidence(
        entry,
        result,
        dedup_key=dedup_key,
        attempt=attempt,
    )
    binding = complete_readonly_intake_preflight(
        backend,
        entry.org_repo,
        dedup_key=dedup_key,
        source_revision=result.source_revision,
        outcome=result.outcome,
        result_hash=result.canonical_hash(),
        reason=result.reason,
        evidence_refs=[str(evidence_path)],
    )
    return ReadonlyIntakeExecution(binding, executed=True, resumed=resumed)


def _write_intake_evidence(
    entry: ProductEntry,
    result: ReadOnlyIntakePreflightV1,
    *,
    dedup_key: str,
    attempt: int,
) -> Path:
    org, repo = entry.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, result.source_revision)
    evidence_path = bundle_dir / "intake" / "receipts" / f"{dedup_key[:16]}-a{attempt}.json"
    if evidence_path.is_file():
        prior = json.loads(evidence_path.read_text(encoding="utf-8"))
        if prior.get("dedup_key") != dedup_key or prior.get("attempt") != attempt:
            raise RuntimeError("compact intake evidence identity collided")
    write_redacted_json(
        evidence_path,
        {
            "dedup_key": dedup_key,
            "attempt": attempt,
            "result": result,
        },
    )
    write_redacted_json(bundle_dir / "intake" / "preflight.json", result)
    refresh_sha256sums(bundle_dir)
    return evidence_path
