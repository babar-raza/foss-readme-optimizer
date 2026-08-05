"""Staged human acceptance and portfolio-wide publication eligibility."""

from __future__ import annotations

from datetime import UTC, datetime

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import (
    HumanAcceptanceBindingV1,
    HumanAcceptanceBoundaryV1,
    HumanAcceptanceDecisionV1,
    PublicationEligibilityBindingV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.schema import RunStateV2

_HUMAN_REVIEWABLE_STATUSES = {
    "NO_OP_PROVEN",
    "HUMAN_REVIEW_READY",
    "HUMAN_ACCEPTED",
    "PR_ELIGIBLE",
    "PR_PROOF_COMPLETE",
}


def _lifecycle(state: RunStateV2, org_repo: str) -> ReadmePocLifecycleStateV2:
    lifecycle = state.readme_poc_lifecycle
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise StateBackendError(f"publication axes require current V2 lifecycle {org_repo!r}")
    return lifecycle


def record_human_acceptance(
    backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    presentation_version: str,
    boundary: HumanAcceptanceBoundaryV1,
    decision: HumanAcceptanceDecisionV1,
    reviewer_identity: str,
    evidence_identity: str,
    reason: str,
    max_retries: int = 5,
) -> ReadmePocLifecycleStateV2:
    """Append one staged human decision; agent approval can never substitute for it."""

    now = datetime.now(UTC).isoformat()

    def patch(state: RunStateV2) -> RunStateV2:
        lifecycle = _lifecycle(state, org_repo)
        if lifecycle.status not in _HUMAN_REVIEWABLE_STATUSES:
            raise StateBackendError("human acceptance requires completed independent local proof")
        presentation = lifecycle.presentation_validity
        if (
            presentation.status not in {"VALID", "VALID_UPDATE_AVAILABLE"}
            or presentation.source_revision != source_revision
            or presentation.presentation_version != presentation_version
        ):
            raise StateBackendError("human decision does not bind the current valid presentation")
        binding = HumanAcceptanceBindingV1(
            source_revision=source_revision,
            presentation_version=presentation_version,
            boundary=boundary,
            decision=decision,
            reviewer_identity=reviewer_identity,
            evidence_identity=evidence_identity,
            reason=reason,
            occurred_at=now,
        )
        updated = lifecycle.model_copy(
            update={
                "updated_at": now,
                "human_acceptance_history": [*lifecycle.human_acceptance_history, binding],
                "publication_eligibility": PublicationEligibilityBindingV1(
                    rejection_reasons=["human acceptance changed"],
                    observed_by=reviewer_identity,
                    occurred_at=now,
                ),
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": updated})

    saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
    return _lifecycle(saved, org_repo)


def _current_human_acceptance(
    lifecycle: ReadmePocLifecycleStateV2,
    boundary: HumanAcceptanceBoundaryV1,
) -> bool:
    decision = next(
        (
            item
            for item in reversed(lifecycle.human_acceptance_history)
            if item.boundary == boundary
        ),
        None,
    )
    presentation = lifecycle.presentation_validity
    return bool(
        decision is not None
        and decision.decision == "ACCEPTED"
        and decision.source_revision == lifecycle.source_revision == presentation.source_revision
        and decision.presentation_version == presentation.presentation_version
    )


def portfolio_publication_rejection_reasons(
    backend: StateBackend,
    admitted_repositories: list[str],
) -> list[str]:
    """Recompute every current Gate-B prerequisite for an effect-time guard."""

    reasons: list[str] = []
    calibration_accepted = False
    representative_cohort_accepted = False
    for repository in admitted_repositories:
        state = backend.load(repository)
        lifecycle = state.readme_poc_lifecycle if state is not None else None
        if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
            reasons.append(f"{repository}:missing_current_lifecycle")
            continue
        factual = lifecycle.factual_validity
        presentation = lifecycle.presentation_validity
        if lifecycle.status not in _HUMAN_REVIEWABLE_STATUSES:
            reasons.append(f"{repository}:local_acceptance_stage_incomplete")
        if (
            factual.status != "VALID"
            or factual.source_revision != lifecycle.source_revision
            or factual.facts_hash != lifecycle.facts_hash
        ):
            reasons.append(f"{repository}:factual_validity_missing_or_stale")
        if (
            presentation.status not in {"VALID", "VALID_UPDATE_AVAILABLE"}
            or presentation.source_revision != lifecycle.source_revision
            or presentation.candidate_hash != lifecycle.candidate_hash
        ):
            reasons.append(f"{repository}:presentation_validity_missing_or_stale")
        calibration_accepted = calibration_accepted or _current_human_acceptance(
            lifecycle, "calibration"
        )
        representative_cohort_accepted = (
            representative_cohort_accepted
            or _current_human_acceptance(lifecycle, "representative_cohort")
        )
        if not _current_human_acceptance(lifecycle, "final_portfolio"):
            reasons.append(f"{repository}:final_human_acceptance_missing_or_stale")
    if not calibration_accepted:
        reasons.append("portfolio:calibration_acceptance_missing_or_stale")
    if not representative_cohort_accepted:
        reasons.append("portfolio:representative_cohort_acceptance_missing_or_stale")
    return reasons


def record_publication_eligibility(
    backend: StateBackend,
    org_repo: str,
    *,
    admitted_repositories: list[str],
    registry_revision: str,
    evidence_identity: str,
    observed_by: str,
    max_retries: int = 5,
) -> ReadmePocLifecycleStateV2:
    """Persist eligibility only after every dynamic registry member has final acceptance."""

    if not admitted_repositories or len(set(admitted_repositories)) != len(admitted_repositories):
        raise StateBackendError("admitted repository denominator must be nonempty and unique")
    admitted = sorted(admitted_repositories)
    if org_repo not in admitted:
        raise StateBackendError("publication target is absent from the admitted registry revision")
    reasons = portfolio_publication_rejection_reasons(backend, admitted)
    now = datetime.now(UTC).isoformat()
    binding = PublicationEligibilityBindingV1(
        status="ELIGIBLE" if not reasons else "INELIGIBLE",
        registry_revision=registry_revision,
        admitted_repositories=admitted,
        rejection_reasons=reasons,
        evidence_identity=evidence_identity,
        observed_by=observed_by,
        occurred_at=now,
    )

    def patch(state: RunStateV2) -> RunStateV2:
        lifecycle = _lifecycle(state, org_repo)
        updated = lifecycle.model_copy(
            update={
                "updated_at": now,
                "publication_eligibility": binding,
                "publication_eligibility_history": [
                    *lifecycle.publication_eligibility_history,
                    binding,
                ],
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": updated})

    saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
    return _lifecycle(saved, org_repo)
