"""Durable factual, presentation, human-review, and publication acceptance axes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import (
    FactualValidityBindingV1,
    PresentationValidityBindingV1,
    PresentationValidityStatusV1,
    PublicationEligibilityBindingV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.schema import RunStateV2


def _lifecycle(state: RunStateV2, org_repo: str) -> ReadmePocLifecycleStateV2:
    lifecycle = state.readme_poc_lifecycle
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise StateBackendError(f"acceptance axes require current V2 lifecycle {org_repo!r}")
    return lifecycle


def record_factual_validity(
    backend: StateBackend,
    org_repo: str,
    *,
    status: Literal["VALID", "INVALID"],
    source_revision: str,
    facts_hash: str,
    acceptance_contract_hash: str,
    evidence_identity: str,
    observed_by: str,
    reason: str,
    max_retries: int = 5,
) -> ReadmePocLifecycleStateV2:
    """Append a source-bound factual decision without altering presentation history."""

    now = datetime.now(UTC).isoformat()

    def patch(state: RunStateV2) -> RunStateV2:
        lifecycle = _lifecycle(state, org_repo)
        if lifecycle.source_revision != source_revision or lifecycle.facts_hash != facts_hash:
            raise StateBackendError("factual validity does not bind the current source and facts")
        if lifecycle.fact_acceptance_contract_hash != acceptance_contract_hash:
            raise StateBackendError("factual validity uses a stale acceptance contract")
        binding = FactualValidityBindingV1(
            status=status,
            source_revision=source_revision,
            facts_hash=facts_hash,
            acceptance_contract_hash=acceptance_contract_hash,
            evidence_identity=evidence_identity,
            reason=reason,
            observed_by=observed_by,
            occurred_at=now,
        )
        updated = lifecycle.model_copy(
            update={
                "updated_at": now,
                "factual_validity": binding,
                "factual_validity_history": [*lifecycle.factual_validity_history, binding],
                "publication_eligibility": PublicationEligibilityBindingV1(
                    rejection_reasons=["factual validity changed"],
                    observed_by=observed_by,
                    occurred_at=now,
                ),
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": updated})

    saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
    return _lifecycle(saved, org_repo)


def record_presentation_validity(
    backend: StateBackend,
    org_repo: str,
    *,
    status: PresentationValidityStatusV1,
    source_revision: str,
    candidate_hash: str,
    presentation_version: str,
    component_manifest_hash: str,
    evidence_identity: str,
    observed_by: str,
    reason: str,
    available_component_manifest_hash: str | None = None,
    max_retries: int = 5,
) -> ReadmePocLifecycleStateV2:
    """Record independent presentation validity while retaining factual proof."""

    if status == "UNKNOWN":
        raise StateBackendError("explicit presentation updates cannot record UNKNOWN")
    now = datetime.now(UTC).isoformat()

    def patch(state: RunStateV2) -> RunStateV2:
        lifecycle = _lifecycle(state, org_repo)
        if (
            lifecycle.source_revision != source_revision
            or lifecycle.candidate_hash != candidate_hash
        ):
            raise StateBackendError("presentation validity does not bind the current candidate")
        if status in {"VALID", "VALID_UPDATE_AVAILABLE"} and (
            lifecycle.factual_validity.status != "VALID"
            or lifecycle.factual_validity.source_revision != source_revision
            or lifecycle.factual_validity.facts_hash != lifecycle.facts_hash
        ):
            raise StateBackendError("valid presentation requires current factual validity")
        binding = PresentationValidityBindingV1(
            status=status,
            source_revision=source_revision,
            candidate_hash=candidate_hash,
            presentation_version=presentation_version,
            component_manifest_hash=component_manifest_hash,
            available_component_manifest_hash=available_component_manifest_hash,
            evidence_identity=evidence_identity,
            reason=reason,
            observed_by=observed_by,
            occurred_at=now,
        )
        updated = lifecycle.model_copy(
            update={
                "updated_at": now,
                "presentation_validity": binding,
                "presentation_validity_history": [
                    *lifecycle.presentation_validity_history,
                    binding,
                ],
                "publication_eligibility": PublicationEligibilityBindingV1(
                    rejection_reasons=["presentation validity changed"],
                    observed_by=observed_by,
                    occurred_at=now,
                ),
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": updated})

    saved = save_state_patch(backend, org_repo, patch, max_retries=max_retries)
    return _lifecycle(saved, org_repo)
