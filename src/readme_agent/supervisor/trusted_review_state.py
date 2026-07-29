"""Persist trusted review outcomes without duplicate lifecycle events."""

from __future__ import annotations

from typing import Literal, cast

from readme_agent.errors import StateBackendError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.specialists.trusted_transform_review_models import TrustedReviewExecutionV1
from readme_agent.state.assurance import TrustedReadmePocStatusV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.readme_poc_lifecycle import transition_trusted_readme_poc_status

_ACCEPTED_OR_LATER = frozenset(
    {
        "TRUSTED_TRANSFORM_APPROVED",
        "TRUSTED_NO_OP_PROVEN",
        "TRUSTED_PR_ELIGIBLE",
        "TRUSTED_PR_OPEN",
    }
)


def record_trusted_review_execution(
    backend: StateBackend,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    execution: TrustedReviewExecutionV1,
    *,
    evidence_refs: list[str],
) -> ReadmePocLifecycleStateV2:
    """Advance validation and review once; make exact accepted retries a durable no-op."""

    review = execution.review
    org_repo = graph.org_repo
    if (
        composition.org_repo != org_repo
        or review.org_repo != org_repo
        or review.candidate_sha256 != composition.candidate_sha256
    ):
        raise StateBackendError("trusted review inputs belong to different repositories or bytes")
    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise StateBackendError("trusted review requires a durable V2 README lifecycle")
    if lifecycle.content_assurance != "trusted_inherited":
        raise StateBackendError("trusted review cannot advance repository-verified lifecycle state")
    if (
        lifecycle.source_revision != graph.source_revision
        or lifecycle.facts_hash != graph.canonical_hash()
        or lifecycle.candidate_hash != composition.candidate_sha256
    ):
        raise StateBackendError(
            "trusted review inputs do not match durable source, facts, or candidate"
        )

    target = cast(
        TrustedReadmePocStatusV1 | Literal["SYSTEM_FAILURE"],
        {
            "TRUSTED_TRANSFORM_APPROVED": "TRUSTED_TRANSFORM_APPROVED",
            "REJECT_REPAIRABLE": "TRUSTED_REVIEW_REJECTED",
            "SYSTEM_FAILURE": "SYSTEM_FAILURE",
        }[review.verdict],
    )
    if lifecycle.status == target or (
        target == "TRUSTED_TRANSFORM_APPROVED" and lifecycle.status in _ACCEPTED_OR_LATER
    ):
        return lifecycle
    prompt_hash = review.cache_identity_sha256
    if lifecycle.status == "TRUSTED_CANDIDATE_GENERATED":
        lifecycle = transition_trusted_readme_poc_status(
            backend,
            org_repo,
            "TRUSTED_DETERMINISTIC_VALIDATED",
            observed_by="trusted_review",
            reason="trusted candidate passed deterministic presentation and safety validation",
            evidence_refs=evidence_refs,
            source_revision=graph.source_revision,
            facts_hash=graph.canonical_hash(),
            candidate_hash=composition.candidate_sha256,
            prompt_hash=prompt_hash,
        )
    if lifecycle.status == "TRUSTED_DETERMINISTIC_VALIDATED":
        lifecycle = transition_trusted_readme_poc_status(
            backend,
            org_repo,
            "TRUSTED_REVIEWING",
            observed_by="trusted_review",
            reason="begin independent blind-quality and inheritance-fidelity review",
            evidence_refs=evidence_refs,
            source_revision=graph.source_revision,
            facts_hash=graph.canonical_hash(),
            candidate_hash=composition.candidate_sha256,
            prompt_hash=prompt_hash,
        )
    if lifecycle.status != "TRUSTED_REVIEWING":
        raise StateBackendError(
            f"trusted review cannot persist {review.verdict!r} from {lifecycle.status!r}"
        )
    return transition_trusted_readme_poc_status(
        backend,
        org_repo,
        target,
        observed_by="trusted_review",
        reason=f"independent trusted review reduced to {review.verdict}",
        evidence_refs=evidence_refs,
        source_revision=graph.source_revision,
        facts_hash=graph.canonical_hash(),
        candidate_hash=composition.candidate_sha256,
        prompt_hash=prompt_hash,
    )
