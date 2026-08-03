"""Durable source-revision deduplication for read-only repository intake."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend, safe_release_lock
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle import acquire_lifecycle_lock
from readme_agent.state.lifecycle_schema import (
    AssuranceReadmePocStatusV1,
    IntakePreflightBindingV1,
    IntakePreflightOutcomeV1,
    IntakePreflightReservationV1,
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
    ReadmePocTransitionV2,
)
from readme_agent.state.readme_poc_lifecycle import migrate_readme_poc_lifecycle
from readme_agent.state.schema import RunStateV2


@dataclass(frozen=True)
class IntakePreflightAcceptance:
    """Whether the caller owns or can reuse one logical intake."""

    reservation: IntakePreflightReservationV1 | None
    completed: IntakePreflightBindingV1 | None
    should_execute: bool
    resumed: bool = False


_NON_INTAKE_FAILURE_RESUME_STAGES: dict[AssuranceReadmePocStatusV1, tuple[str, ...]] = {
    "SNAPSHOTTED": ("source_revision",),
    "PROFILED": ("source_revision",),
    "FACTS_COLLECTING": ("source_revision",),
    "FACTS_READY": ("facts_hash",),
    "README_ASSESSED": ("facts_hash", "assessment_hash"),
    "PLAN_READY": ("facts_hash", "assessment_hash", "presentation_plan_hash"),
    "CANDIDATE_GENERATED": (
        "facts_hash",
        "assessment_hash",
        "presentation_plan_hash",
        "candidate_hash",
    ),
    "DETERMINISTIC_VALIDATED": (
        "facts_hash",
        "assessment_hash",
        "presentation_plan_hash",
        "candidate_hash",
    ),
    "AGENT_REVIEWING": (
        "facts_hash",
        "assessment_hash",
        "presentation_plan_hash",
        "candidate_hash",
    ),
}


FailureOwner = Literal["intake", "non_intake", "unknown"]


def _failure_recovery(
    lifecycle: ReadmePocLifecycleStateV2,
) -> tuple[FailureOwner, AssuranceReadmePocStatusV1 | None]:
    """Classify failure ownership and the last checksum-bound safe stage."""

    failure = None
    if lifecycle.status == "SYSTEM_FAILURE":
        failure = next(
            (item for item in reversed(lifecycle.history) if item.to_status == "SYSTEM_FAILURE"),
            None,
        )
    elif (
        lifecycle.status == "INTAKE_READY"
        and lifecycle.history
        and lifecycle.history[-1].reason == "reconciled successful read-only intake retry"
    ):
        failure = next(
            (
                item
                for item in reversed(lifecycle.history[:-1])
                if item.to_status == "SYSTEM_FAILURE"
            ),
            None,
        )
    if failure is None:
        if lifecycle.status == "SYSTEM_FAILURE" and any(
            item.outcome == "SYSTEM_FAILURE" and item.observed_by == "registry_intake"
            for item in lifecycle.intake_preflight_history
        ):
            return "intake", None
        return "unknown", None
    if failure.from_status == "INTAKE_PREFLIGHTING" and failure.observed_by == "registry_intake":
        return "intake", None

    failed_stage = failure.from_status
    if failed_stage is None:
        return "non_intake", None
    resume_stage = "DETERMINISTIC_VALIDATED" if failed_stage == "AGENT_REVIEWING" else failed_stage
    required = _NON_INTAKE_FAILURE_RESUME_STAGES.get(resume_stage)
    if required is None or any(getattr(lifecycle, field) is None for field in required):
        return "non_intake", None
    return "non_intake", resume_stage


def intake_preflight_dedup_key(
    org_repo: str,
    provider_repository_id: int,
    source_revision: str,
    contract_hash: str,
) -> str:
    """Bind one logical intake to stable identity, revision, and rules."""

    material = "\n".join(
        (org_repo.casefold(), str(provider_repository_id), source_revision, contract_hash)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def begin_readonly_intake_preflight(
    backend: StateBackend,
    org_repo: str,
    *,
    dedup_key: str,
    source_revision: str,
    source_revision_resolved: bool = True,
    max_retries: int = 5,
) -> IntakePreflightAcceptance:
    """Claim once; an interrupted matching reservation resumes in place."""

    lock = acquire_lifecycle_lock(backend, org_repo, max_attempts=max_retries)
    try:
        current = backend.load(org_repo)
        lifecycle = _current_lifecycle(current)
        completed = _latest_completed(lifecycle, dedup_key)
        if completed is not None and completed.outcome != "SYSTEM_FAILURE":
            if (
                completed.source_revision != source_revision
                or completed.source_revision_resolved != source_revision_resolved
            ):
                raise StateBackendError(f"{org_repo!r} completed intake identity is inconsistent")
            failure_owner, resume_stage = _failure_recovery(lifecycle)
            revisions_match = lifecycle.source_revision in {None, completed.source_revision}
            needs_repair = (lifecycle.status == "SYSTEM_FAILURE" and failure_owner == "intake") or (
                failure_owner == "non_intake"
                and (resume_stage is not None or lifecycle.status == "INTAKE_READY")
                and lifecycle.source_revision == completed.source_revision == source_revision
            )
            if needs_repair and revisions_match:
                now = datetime.now(UTC).isoformat()

                def repair_terminal_status(state: RunStateV2) -> RunStateV2:
                    prior = _current_lifecycle(state)
                    latest = _latest_completed(prior, dedup_key)
                    owner, recovered_stage = _failure_recovery(prior)
                    if latest is None or latest.outcome == "SYSTEM_FAILURE":
                        return state
                    if owner == "intake" and prior.status == "SYSTEM_FAILURE":
                        next_status: AssuranceReadmePocStatusV1 = "INTAKE_READY"
                    elif (
                        owner == "non_intake"
                        and prior.status in {"SYSTEM_FAILURE", "INTAKE_READY"}
                        and prior.source_revision == latest.source_revision == source_revision
                    ):
                        next_status = recovered_stage or "SYSTEM_FAILURE"
                    else:
                        return state
                    if prior.status == next_status:
                        return state
                    updated = prior.model_copy(
                        update={
                            "status": next_status,
                            "updated_at": now,
                            "history": [
                                *prior.history,
                                ReadmePocTransitionV2(
                                    from_status=prior.status,
                                    to_status=next_status,
                                    reason=(
                                        "recovered checksum-bound safe boundary after "
                                        "non-intake system failure"
                                        if owner == "non_intake" and recovered_stage is not None
                                        else (
                                            "undid unsafe intake rewind after non-intake "
                                            "system failure"
                                            if owner == "non_intake"
                                            else "reconciled successful read-only intake retry"
                                        )
                                    ),
                                    evidence_refs=latest.evidence_refs,
                                    observed_by="registry_intake",
                                    occurred_at=now,
                                    source_revision=latest.source_revision,
                                ),
                            ],
                        }
                    )
                    return state.model_copy(update={"readme_poc_lifecycle": updated})

                save_state_patch(backend, org_repo, repair_terminal_status, max_retries=max_retries)
            return IntakePreflightAcceptance(
                reservation=None,
                completed=completed,
                should_execute=False,
            )
        pending = lifecycle.intake_preflight_pending
        if pending is not None:
            if pending.dedup_key != dedup_key:
                raise StateBackendError(
                    f"{org_repo!r} has an unfinished intake for a different source revision"
                )
            if (
                pending.source_revision != source_revision
                or pending.source_revision_resolved != source_revision_resolved
            ):
                raise StateBackendError(f"{org_repo!r} intake dedup identity is inconsistent")
            return IntakePreflightAcceptance(
                reservation=pending,
                completed=None,
                should_execute=True,
                resumed=True,
            )

        attempt = (completed.attempt + 1) if completed is not None else 1
        reservation = IntakePreflightReservationV1(
            dedup_key=dedup_key,
            source_revision=source_revision,
            source_revision_resolved=source_revision_resolved,
            attempt=attempt,
        )
        now = datetime.now(UTC).isoformat()

        def patch(state: RunStateV2) -> RunStateV2:
            prior = _current_lifecycle(state)
            if _latest_completed(prior, dedup_key) is not None and completed is None:
                return state
            if prior.intake_preflight_pending is not None:
                if prior.intake_preflight_pending.dedup_key != dedup_key:
                    raise StateBackendError(
                        f"{org_repo!r} acquired another intake while waiting for CAS"
                    )
                return state
            history = prior.history
            next_status = prior.status
            if prior.status in {"DISCOVERED", "INTAKE_READY", "SYSTEM_FAILURE"}:
                next_status = "INTAKE_PREFLIGHTING"
                history = [
                    *history,
                    ReadmePocTransitionV2(
                        from_status=prior.status,
                        to_status="INTAKE_PREFLIGHTING",
                        reason="claimed source-bound read-only intake preflight",
                        observed_by="registry_intake",
                        occurred_at=now,
                        source_revision=source_revision,
                    ),
                ]
            updated = prior.model_copy(
                update={
                    "status": next_status,
                    "updated_at": now,
                    "history": history,
                    "intake_preflight_pending": reservation,
                }
            )
            return state.model_copy(update={"readme_poc_lifecycle": updated})

        saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
        saved_lifecycle = _current_lifecycle(saved)
        saved_pending = saved_lifecycle.intake_preflight_pending
        if saved_pending is None:
            raced = _latest_completed(saved_lifecycle, dedup_key)
            if raced is None:
                raise StateBackendError(f"{org_repo!r} intake reservation disappeared")
            return IntakePreflightAcceptance(None, raced, should_execute=False)
        return IntakePreflightAcceptance(saved_pending, None, should_execute=True)
    finally:
        safe_release_lock(backend.release_lock, lock, label="README-intake-lock")


def complete_readonly_intake_preflight(
    backend: StateBackend,
    org_repo: str,
    *,
    dedup_key: str,
    source_revision: str,
    outcome: IntakePreflightOutcomeV1,
    result_hash: str,
    reason: str,
    evidence_refs: list[str],
    observed_by: str = "registry_intake",
    max_retries: int = 5,
) -> IntakePreflightBindingV1:
    """Persist one terminal receipt and clear its matching reservation."""

    lock = acquire_lifecycle_lock(backend, org_repo, max_attempts=max_retries)
    try:
        current = backend.load(org_repo)
        lifecycle = _current_lifecycle(current)
        completed = _latest_completed(lifecycle, dedup_key)
        if completed is not None and completed.outcome != "SYSTEM_FAILURE":
            return completed
        pending = lifecycle.intake_preflight_pending
        if pending is None or pending.dedup_key != dedup_key:
            raise StateBackendError(f"{org_repo!r} has no matching intake reservation to complete")
        if pending.source_revision != source_revision:
            raise StateBackendError(f"{org_repo!r} intake completion revision is inconsistent")
        binding = IntakePreflightBindingV1(
            dedup_key=dedup_key,
            source_revision=source_revision,
            source_revision_resolved=pending.source_revision_resolved,
            outcome=outcome,
            result_hash=result_hash,
            reason=reason,
            evidence_refs=evidence_refs,
            observed_by=observed_by,
            attempt=pending.attempt,
        )
        now = datetime.now(UTC).isoformat()

        def patch(state: RunStateV2) -> RunStateV2:
            prior = _current_lifecycle(state)
            existing = _latest_completed(prior, dedup_key)
            if existing is not None and existing.outcome != "SYSTEM_FAILURE":
                return state
            active = prior.intake_preflight_pending
            if active is None or active.dedup_key != dedup_key:
                raise StateBackendError(
                    f"{org_repo!r} intake reservation changed before completion"
                )
            next_status = prior.status
            transition_history = prior.history
            if prior.status == "INTAKE_PREFLIGHTING":
                next_status = "SYSTEM_FAILURE" if outcome == "SYSTEM_FAILURE" else "INTAKE_READY"
                transition_history = [
                    *transition_history,
                    ReadmePocTransitionV2(
                        from_status=prior.status,
                        to_status=next_status,
                        reason=f"read-only intake classified {outcome}",
                        evidence_refs=evidence_refs,
                        observed_by=observed_by,
                        occurred_at=now,
                        source_revision=source_revision,
                    ),
                ]
            updated = prior.model_copy(
                update={
                    "status": next_status,
                    "updated_at": now,
                    "history": transition_history,
                    "intake_preflight_pending": None,
                    "intake_preflight_history": [*prior.intake_preflight_history, binding],
                }
            )
            return state.model_copy(update={"readme_poc_lifecycle": updated})

        saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
        saved_binding = _latest_completed(_current_lifecycle(saved), dedup_key)
        if saved_binding is None:
            raise StateBackendError(f"{org_repo!r} intake completion disappeared")
        return saved_binding
    finally:
        safe_release_lock(backend.release_lock, lock, label="README-intake-lock")


def _current_lifecycle(state: RunStateV2 | None) -> ReadmePocLifecycleStateV2:
    stored = state.readme_poc_lifecycle if state is not None else None
    if isinstance(stored, ReadmePocLifecycleStateV1):
        return migrate_readme_poc_lifecycle(stored)
    return stored or ReadmePocLifecycleStateV2()


def _latest_completed(
    lifecycle: ReadmePocLifecycleStateV2,
    dedup_key: str,
) -> IntakePreflightBindingV1 | None:
    return next(
        (
            binding
            for binding in reversed(lifecycle.intake_preflight_history)
            if binding.dedup_key == dedup_key
        ),
        None,
    )
