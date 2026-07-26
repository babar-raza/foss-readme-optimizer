"""Per-org/repo README-POC pipeline-progress lifecycle (`RPOC-070`, sprint
charter Part B.2 Phase 5 Lane S / Part C.7): the durable, transition-
validated status vocabulary the charter's README-POC lifecycle demands
(`DISCOVERED` through `PR_PROOF_COMPLETE`), reusing this project's existing
CAS state primitives (`state/cas.py::save_state_patch()`) rather than
inventing a parallel state system.

Deliberately its own module, not folded into `state/domain_state.py`: this
status describes ONE repo's overall README-POC pipeline progress -- a single
slot on `RunStateV1`/`RunStateV2` (`readme_poc_lifecycle`), the same "own
slot, never shared" reasoning `supervisor_state`/`profile_cache`/
`open_proposals` already use in `state/schema.py` -- not a per-specialist-
domain record (`domain_states`, which `domain_state.py` exists to serve).
Mirrors `state/lifecycle.py::transition_trigger()`'s transition-table shape
(validate `from_status -> to_status` against an explicit table, CAS-write via
`save_state_patch()`) and `supervisor/mission_control.py::transition_task()`'s
strict "only listed transitions, no implicit self-loop" rule and append-only
transition history, applied to the one new status dimension neither of those
two existing state machines covers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import (
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
    ReadmePocStatusV2,
    ReadmePocTransitionV2,
)
from readme_agent.state.schema import RunStateV2

# Legal `from_status -> {to_status, ...}` moves for one repo's README-POC
# pipeline progress (sprint charter §7/§8, `RPOC-070`). Strict, not
# permissive: a status not listed here for a given `from_status` -- including
# the same status again -- is rejected, matching `supervisor/mission_control.
# py::_TRANSITIONS`'s own "only listed transitions" discipline (no implicit
# self-loop / idempotent-retry carve-out, unlike `state/lifecycle.
# py::_ALLOWED_TRANSITIONS`) -- a README-POC status re-affirmation with no
# distinguishing prior state is never a real event worth recording for this
# vocabulary.
#
# `REPAIRING` is the one shared re-entry point for both failure classes the
# charter names (`DETERMINISTIC_VALIDATION_FAILED`, `AGENT_REVIEW_REJECTED`)
# and for a human reviewer's own rejection (routed through `HUMAN_REVIEW_
# READY -> REPAIRING`, since the charter's vocabulary has no dedicated
# "human rejected" status) -- every repair cycle always re-enters at
# `CANDIDATE_GENERATED`, never skips back into deterministic validation or
# agent review as a separate step, since both happen automatically as part of
# producing a new candidate (`RPOC-022`/`RPOC-051`'s own pipeline wiring).
#
# A fact block may continue to `README_ASSESSED`: missing or conflicting
# facts block only dependent document operations, while the assessment and
# plan preserve or omit those claims. It may not jump to `FACTS_READY`;
# resolving the blocked fact still requires a fresh collection pass.
#
# `PR_PROOF_COMPLETE` is deliberately terminal (empty set) here -- this
# taskcard only establishes the vocabulary and its transition table; whether
# an accepted repo's lifecycle record should ever reopen after a later
# upstream change is a decision for whichever future taskcard (RPOC-071+)
# actually drives transitions in production, not one this schema-only pass
# should guess at.
_README_POC_TRANSITIONS: dict[ReadmePocStatusV2, set[ReadmePocStatusV2]] = {
    "DISCOVERED": {"SNAPSHOTTED", "SYSTEM_FAILURE"},
    "SNAPSHOTTED": {"SNAPSHOTTED", "PROFILED", "SYSTEM_FAILURE"},
    "PROFILED": {"FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "FACTS_COLLECTING": {
        "FACTS_READY",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "SYSTEM_FAILURE",
    },
    "BLOCKED_FACT_CONFLICT": {"README_ASSESSED", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "BLOCKED_MISSING_EVIDENCE": {"README_ASSESSED", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "FACTS_READY": {"README_ASSESSED", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "README_ASSESSED": {"PLAN_READY", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "PLAN_READY": {"CANDIDATE_GENERATED", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "CANDIDATE_GENERATED": {
        "DETERMINISTIC_VALIDATION_FAILED",
        "DETERMINISTIC_VALIDATED",
        "FACTS_COLLECTING",
        "SYSTEM_FAILURE",
    },
    "DETERMINISTIC_VALIDATION_FAILED": {"REPAIRING"},
    "DETERMINISTIC_VALIDATED": {"AGENT_REVIEWING", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "AGENT_REVIEWING": {
        "AGENT_APPROVED",
        "AGENT_REVIEW_REJECTED",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "FACTS_COLLECTING",
        "SYSTEM_FAILURE",
    },
    "AGENT_REVIEW_REJECTED": {"REPAIRING", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    # Repair invokes the same fallible renderer/LLM/tool seams as initial
    # composition. An execution failure there must remain a truthful,
    # recoverable lifecycle outcome rather than making portfolio isolation
    # itself fail while attempting to record the error.
    "REPAIRING": {"CANDIDATE_GENERATED", "SYSTEM_FAILURE"},
    "AGENT_APPROVED": {"NO_OP_PROVEN", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "NO_OP_PROVEN": {"HUMAN_REVIEW_READY", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "HUMAN_REVIEW_READY": {"HUMAN_ACCEPTED", "REPAIRING", "FACTS_COLLECTING"},
    "HUMAN_ACCEPTED": {"PR_ELIGIBLE", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    "PR_ELIGIBLE": {"PR_PROOF_COMPLETE", "FACTS_COLLECTING", "SYSTEM_FAILURE"},
    # A new source snapshot may invalidate even a previously proven PR.
    "PR_PROOF_COMPLETE": {"SNAPSHOTTED", "FACTS_COLLECTING"},
    "SYSTEM_FAILURE": {"SNAPSHOTTED", "FACTS_COLLECTING", "REPAIRING"},
}

# A new immutable source revision invalidates every derived stage. The same-
# revision retry remains an idempotent no-op in ``record_repository_snapshot``;
# only a genuinely different revision may use this reopening edge.
for _derived_status in (
    "PROFILED",
    "FACTS_COLLECTING",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
    "FACTS_READY",
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
):
    _README_POC_TRANSITIONS[_derived_status].add("SNAPSHOTTED")

# A renderer/template/assessment change at the same source revision reopens
# at the earliest affected composition boundary while retaining the verified
# fact graph. The caller must supply fresh assessment/plan/candidate hashes;
# this edge is never used to pretend a fact conflict was resolved.
for _composition_status in (
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
):
    _README_POC_TRANSITIONS[_composition_status].add("README_ASSESSED")

_V1_STATUS_MIGRATION: dict[str, ReadmePocStatusV2] = {
    "DISCOVERED": "DISCOVERED",
    "SNAPSHOTTED": "SNAPSHOTTED",
    "PROFILED": "PROFILED",
    "FACTS_COLLECTING": "FACTS_COLLECTING",
    "FACTS_READY": "FACTS_READY",
    "FACT_CONFLICT": "BLOCKED_FACT_CONFLICT",
    "PLAN_READY": "PLAN_READY",
    "CANDIDATE_GENERATED": "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATION_FAILED": "DETERMINISTIC_VALIDATION_FAILED",
    "AGENT_REVIEW_REJECTED": "AGENT_REVIEW_REJECTED",
    "REPAIRING": "REPAIRING",
    "AGENT_APPROVED": "AGENT_APPROVED",
    "HUMAN_REVIEW_READY": "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED": "HUMAN_ACCEPTED",
    "PR_ELIGIBLE": "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE": "PR_PROOF_COMPLETE",
}


def legal_next_readme_poc_statuses(status: ReadmePocStatusV2) -> frozenset[ReadmePocStatusV2]:
    """Read-only introspection for a caller (e.g. a future portfolio report,
    `RPOC-071`) that needs to know what a given status may legally become
    next, without reaching into this module's own private transition table."""
    return frozenset(_README_POC_TRANSITIONS[status])


def _migrate_v1_lifecycle(prior: ReadmePocLifecycleStateV1) -> ReadmePocLifecycleStateV2:
    """Upgrade the existing lifecycle record without discarding its history."""
    return ReadmePocLifecycleStateV2(
        status=_V1_STATUS_MIGRATION[prior.status],
        updated_at=prior.updated_at,
        details=prior.details,
        history=[
            ReadmePocTransitionV2(
                from_status=(
                    _V1_STATUS_MIGRATION[entry.from_status]
                    if entry.from_status is not None
                    else None
                ),
                to_status=_V1_STATUS_MIGRATION[entry.to_status],
                reason=entry.reason,
                evidence_refs=entry.evidence_refs,
                observed_by=entry.observed_by,
                occurred_at=entry.occurred_at,
            )
            for entry in prior.history
        ],
    )


def transition_readme_poc_status(
    backend: StateBackend,
    org_repo: str,
    to_status: ReadmePocStatusV2,
    *,
    observed_by: str,
    reason: str,
    evidence_refs: list[str] | None = None,
    source_revision: str | None = None,
    facts_hash: str | None = None,
    assessment_hash: str | None = None,
    presentation_plan_hash: str | None = None,
    candidate_hash: str | None = None,
    prompt_hash: str | None = None,
    reviewer_standard_hash: str | None = None,
    protected_content_fingerprint: str | None = None,
    max_retries: int = 5,
) -> ReadmePocLifecycleStateV2:
    """Validate and durably record one README-POC lifecycle transition for
    `org_repo`, CAS-writing onto a freshly reloaded `RunStateV2.readme_poc_
    lifecycle` -- mirrors `state/lifecycle.py::transition_trigger()`'s own
    shape exactly, one status dimension over: no explicit lock is taken (the
    same posture `transition_trigger()` already uses), since `save_state_
    patch()`'s own load-patch-CAS-save-retry loop is already the correctness
    mechanism; a lock here would only add contention, not safety.

    A record with no prior `readme_poc_lifecycle` (a repo that has never
    entered the README-POC pipeline) starts from the implicit `"DISCOVERED"`
    default `ReadmePocLifecycleStateV1` itself declares, so the very first
    real call a caller makes is `to_status="SNAPSHOTTED"`, not a separate
    "initialize" step.

    Raises `StateBackendError` immediately (never retried -- only
    `RetryableOperationError`, raised solely for a genuine CAS staleness, is
    retried by `save_state_patch()`) when `to_status` is not a legal move
    from the record's current status."""

    now = datetime.now(UTC).isoformat()

    def patch(state: RunStateV2) -> RunStateV2:
        stored = state.readme_poc_lifecycle
        prior = (
            _migrate_v1_lifecycle(stored)
            if isinstance(stored, ReadmePocLifecycleStateV1)
            else (stored or ReadmePocLifecycleStateV2())
        )
        if to_status not in _README_POC_TRANSITIONS[prior.status]:
            raise StateBackendError(
                f"invalid README-POC lifecycle transition {prior.status!r} -> "
                f"{to_status!r} for {org_repo!r}"
            )
        next_source_revision = source_revision or prior.source_revision
        source_changed = (
            to_status == "SNAPSHOTTED"
            and prior.status != "DISCOVERED"
            and next_source_revision != prior.source_revision
        )
        if to_status == "SNAPSHOTTED" and prior.status == "SNAPSHOTTED" and not source_changed:
            raise StateBackendError(
                "invalid README-POC lifecycle transition: cannot reopen "
                f"{org_repo!r} at the same source revision {prior.source_revision!r}"
            )
        repair_attempts = prior.repair_attempts_for_revision
        if source_changed:
            repair_attempts = 0
        if to_status == "REPAIRING":
            repair_attempts += 1
            if repair_attempts > 2:
                raise StateBackendError(
                    f"README-POC repair attempts exhausted for {org_repo!r} at source revision "
                    f"{source_revision or prior.source_revision or 'unknown'}"
                )
        transition = ReadmePocTransitionV2(
            from_status=prior.status,
            to_status=to_status,
            reason=reason,
            evidence_refs=evidence_refs or [],
            observed_by=observed_by,
            occurred_at=now,
            source_revision=next_source_revision,
        )
        next_lifecycle = prior.model_copy(
            update={
                "status": to_status,
                "updated_at": now,
                "history": [*prior.history, transition],
                "source_revision": next_source_revision,
                "facts_hash": (
                    facts_hash
                    if facts_hash is not None
                    else (None if source_changed else prior.facts_hash)
                ),
                "assessment_hash": (
                    assessment_hash
                    if assessment_hash is not None
                    else (None if source_changed else prior.assessment_hash)
                ),
                "presentation_plan_hash": (
                    presentation_plan_hash
                    if presentation_plan_hash is not None
                    else (None if source_changed else prior.presentation_plan_hash)
                ),
                "candidate_hash": (
                    candidate_hash
                    if candidate_hash is not None
                    else (None if source_changed else prior.candidate_hash)
                ),
                "prompt_hash": (
                    prompt_hash
                    if prompt_hash is not None
                    else (None if source_changed else prior.prompt_hash)
                ),
                "reviewer_standard_hash": (
                    reviewer_standard_hash
                    if reviewer_standard_hash is not None
                    else (None if source_changed else prior.reviewer_standard_hash)
                ),
                "protected_content_fingerprint": (
                    protected_content_fingerprint
                    if protected_content_fingerprint is not None
                    else (None if source_changed else prior.protected_content_fingerprint)
                ),
                "repair_attempts_for_revision": repair_attempts,
                "details": {} if source_changed else prior.details,
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": next_lifecycle})

    saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
    assert isinstance(saved.readme_poc_lifecycle, ReadmePocLifecycleStateV2)
    return saved.readme_poc_lifecycle


def record_readme_candidate_artifacts(
    backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    assessment_hash: str,
    presentation_plan_hash: str,
    candidate_hash: str,
    evidence_refs: list[str],
) -> ReadmePocLifecycleStateV2:
    """Persist assessment, plan, and candidate boundaries without duplicate events."""

    state = backend.load(org_repo)
    stored = state.readme_poc_lifecycle if state is not None else None
    if stored is None or isinstance(stored, ReadmePocLifecycleStateV1):
        raise StateBackendError(f"{org_repo!r} has no V2 product-truth lifecycle to compose from")
    if stored.source_revision != source_revision:
        raise StateBackendError(
            "README candidate source revision does not match durable lifecycle state: "
            f"{source_revision!r} != {stored.source_revision!r}"
        )
    hashes_match = (
        stored.assessment_hash == assessment_hash
        and stored.presentation_plan_hash == presentation_plan_hash
        and stored.candidate_hash == candidate_hash
    )
    if (
        stored.status
        in {
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
        and hashes_match
    ):
        return stored

    current = stored
    if current.status != "README_ASSESSED":
        current = transition_readme_poc_status(
            backend,
            org_repo,
            "README_ASSESSED",
            observed_by="readme-presentation-composition",
            reason="source-bound README assessment completed",
            evidence_refs=evidence_refs,
            source_revision=source_revision,
            assessment_hash=assessment_hash,
        )
    if current.status != "PLAN_READY":
        current = transition_readme_poc_status(
            backend,
            org_repo,
            "PLAN_READY",
            observed_by="readme-presentation-composition",
            reason="fact-cited source-span presentation plan completed",
            evidence_refs=evidence_refs,
            source_revision=source_revision,
            presentation_plan_hash=presentation_plan_hash,
        )
    return transition_readme_poc_status(
        backend,
        org_repo,
        "CANDIDATE_GENERATED",
        observed_by="readme-presentation-composition",
        reason="revision-addressed README candidate and native patch materialized",
        evidence_refs=evidence_refs,
        source_revision=source_revision,
        candidate_hash=candidate_hash,
    )


def record_repository_snapshot(
    backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    evidence_refs: list[str],
) -> ReadmePocLifecycleStateV2:
    """Persist the first truthful local-POC boundary after a real clone.

    Repeating the same immutable snapshot is intentionally a no-op. A new
    source revision reopens at ``SNAPSHOTTED`` and clears every derived hash;
    profile and product truth must then be rebuilt before presentation work.
    """
    loaded = backend.load(org_repo)
    lifecycle = loaded.readme_poc_lifecycle if loaded is not None else None
    if isinstance(lifecycle, ReadmePocLifecycleStateV1):
        lifecycle = _migrate_v1_lifecycle(lifecycle)
    if lifecycle is not None and lifecycle.source_revision == source_revision:
        return lifecycle
    return transition_readme_poc_status(
        backend,
        org_repo,
        "SNAPSHOTTED",
        observed_by="supervisor_snapshot",
        reason="captured immutable repository snapshot",
        evidence_refs=evidence_refs,
        source_revision=source_revision,
    )


def record_repository_profile(
    backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    evidence_refs: list[str],
) -> ReadmePocLifecycleStateV2:
    """Record the profile already captured from the immutable snapshot.

    `capture_repository_snapshot()` builds the repository profile while
    computing package roots.  This second durable boundary is therefore
    truthful immediately after snapshot persistence; it does not claim that
    product facts, README assessment, or proposal work has happened.

    A retry after interruption is idempotent.  Later lifecycle states for the
    same revision are preserved rather than regressed to `PROFILED`.
    """
    loaded = backend.load(org_repo)
    lifecycle = loaded.readme_poc_lifecycle if loaded is not None else None
    if isinstance(lifecycle, ReadmePocLifecycleStateV1):
        lifecycle = _migrate_v1_lifecycle(lifecycle)
    if lifecycle is None:
        raise StateBackendError(
            f"cannot record repository profile for {org_repo!r} before its snapshot"
        )
    if lifecycle.source_revision != source_revision:
        raise StateBackendError(
            f"cannot record repository profile for {source_revision!r}; durable snapshot is "
            f"{lifecycle.source_revision!r}"
        )
    if lifecycle.status == "SNAPSHOTTED":
        return transition_readme_poc_status(
            backend,
            org_repo,
            "PROFILED",
            observed_by="supervisor_profile",
            reason="profiled immutable repository snapshot",
            evidence_refs=evidence_refs,
            source_revision=source_revision,
        )
    return lifecycle


def record_product_facts(
    backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    facts_hash: str,
    evidence_refs: list[str],
    prompt_hash: str | None = None,
) -> ReadmePocLifecycleStateV2:
    """Record one provenance-complete fact graph without skipping boundaries.

    A same-revision, same-hash retry is idempotent. A changed fact graph
    reopens later lifecycle states at ``FACTS_COLLECTING`` so no candidate or
    approval can silently retain claims derived from stale truth.
    """
    return record_product_facts_outcome(
        backend,
        org_repo,
        source_revision=source_revision,
        facts_hash=facts_hash,
        outcome="FACTS_READY",
        evidence_refs=evidence_refs,
        prompt_hash=prompt_hash,
    )


def record_product_facts_outcome(
    backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    facts_hash: str,
    outcome: ReadmePocStatusV2,
    evidence_refs: list[str],
    prompt_hash: str | None = None,
) -> ReadmePocLifecycleStateV2:
    """Persist a ready or narrowly blocked fact result through the legal boundary."""
    if outcome not in {
        "FACTS_READY",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
    }:
        raise StateBackendError(f"invalid product-facts outcome {outcome!r}")

    loaded = backend.load(org_repo)
    lifecycle = loaded.readme_poc_lifecycle if loaded is not None else None
    if isinstance(lifecycle, ReadmePocLifecycleStateV1):
        lifecycle = _migrate_v1_lifecycle(lifecycle)
    if lifecycle is None or lifecycle.source_revision != source_revision:
        raise StateBackendError(
            f"cannot record product facts for {org_repo!r} without a matching profile at "
            f"{source_revision!r}"
        )
    if (
        lifecycle.facts_hash == facts_hash
        and lifecycle.prompt_hash == prompt_hash
        and lifecycle.status == outcome
    ):
        return lifecycle
    if lifecycle.status == "PROFILED":
        lifecycle = transition_readme_poc_status(
            backend,
            org_repo,
            "FACTS_COLLECTING",
            observed_by="supervisor_product_truth",
            reason="collecting and reconciling repository product truth",
            source_revision=source_revision,
        )
    elif lifecycle.status != "FACTS_COLLECTING":
        lifecycle = transition_readme_poc_status(
            backend,
            org_repo,
            "FACTS_COLLECTING",
            observed_by="supervisor_product_truth",
            reason="fact inputs changed; invalidating dependent README stages",
            source_revision=source_revision,
        )
    return transition_readme_poc_status(
        backend,
        org_repo,
        outcome,
        observed_by="supervisor_product_truth",
        reason=(
            "provenance-complete ProductFactsV2 persisted"
            if outcome == "FACTS_READY"
            else "product facts persisted with a narrowly scoped unresolved evidence boundary"
        ),
        evidence_refs=evidence_refs,
        source_revision=source_revision,
        facts_hash=facts_hash,
        prompt_hash=prompt_hash,
    )
