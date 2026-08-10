"""Bind local README acceptance artifacts to the exact validated dependency set."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.supervisor.portfolio_scheduler.contracts import canonical_sha256
from readme_agent.verification.mermaid_render import MERMAID_RENDER_CONTRACT_VERSION


class DeterministicAcceptanceBindingV1(BaseModel):
    """Identity of the candidate and validator contract accepted by one proof."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_stage_dependency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    mermaid_render_contract_version: str | None = None


class ReviewAcceptanceBindingV1(DeterministicAcceptanceBindingV1):
    """Extend deterministic identity through independent review and no-op proof."""

    deterministic_validation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_standard_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


def bind_deterministic_validation(
    validation: dict[str, Any],
    *,
    candidate_hash: str,
    candidate_stage_dependency_key: str,
) -> tuple[dict[str, Any], DeterministicAcceptanceBindingV1]:
    """Attach the current candidate/validator identity before hashing validation."""

    render = validation.get("official_mermaid_render")
    render_contract: str | None = None
    if isinstance(render, dict) and render.get("status") == "passed":
        render_contract = str(render.get("contract_version") or "")
        if render_contract != MERMAID_RENDER_CONTRACT_VERSION:
            raise ValueError(
                "official Mermaid proof does not use the current render contract: "
                f"expected {MERMAID_RENDER_CONTRACT_VERSION}, observed {render_contract or '-'}"
            )
    binding = DeterministicAcceptanceBindingV1(
        candidate_hash=candidate_hash,
        candidate_stage_dependency_key=candidate_stage_dependency_key,
        mermaid_render_contract_version=render_contract,
    )
    return {
        **validation,
        "acceptance_binding": binding.model_dump(mode="json"),
    }, binding


def build_review_acceptance_binding(
    deterministic_validation: dict[str, Any],
    deterministic_binding: DeterministicAcceptanceBindingV1,
    *,
    reviewer_standard_hash: str,
) -> ReviewAcceptanceBindingV1:
    """Create the non-circular identity shared by review and no-op artifacts."""

    return ReviewAcceptanceBindingV1(
        **deterministic_binding.model_dump(mode="json"),
        deterministic_validation_hash=canonical_sha256(deterministic_validation),
        reviewer_standard_hash=reviewer_standard_hash,
    )


def validate_acceptance_artifact_chain(
    *,
    manifest: dict[str, Any],
    deterministic_validation: dict[str, Any] | None,
    independent_review: dict[str, Any] | None,
    final_verdict: dict[str, Any] | None,
    no_op_proof: dict[str, Any] | None,
    candidate_hash: str | None,
    manifest_candidate_stage_dependency_key: str,
    reviewer_standard_hash: str,
    require_no_op: bool,
) -> list[str]:
    """Reject stale or cross-transaction acceptance artifacts fail closed."""

    if deterministic_validation is None:
        return ["deterministic_validation_missing_or_invalid"]
    try:
        deterministic_binding = DeterministicAcceptanceBindingV1.model_validate(
            deterministic_validation.get("acceptance_binding")
        )
    except ValueError:
        return ["deterministic_acceptance_binding_missing_or_invalid"]

    reasons: list[str] = []
    if deterministic_validation.get("verdict") != "accept":
        reasons.append("deterministic_validation_not_accepted")
    if deterministic_binding.candidate_hash != candidate_hash:
        reasons.append("deterministic_candidate_hash_mismatch")
    if (
        deterministic_binding.candidate_stage_dependency_key
        != manifest_candidate_stage_dependency_key
    ):
        reasons.append("deterministic_manifest_dependency_key_mismatch")
    render = deterministic_validation.get("official_mermaid_render")
    if isinstance(render, dict) and render.get("status") == "passed":
        if render.get("contract_version") != deterministic_binding.mermaid_render_contract_version:
            reasons.append("mermaid_render_binding_mismatch")

    deterministic_hash = canonical_sha256(deterministic_validation)
    if manifest.get("deterministic_validation_hash") != deterministic_hash:
        reasons.append("manifest_deterministic_validation_hash_mismatch")
    expected_review_binding = ReviewAcceptanceBindingV1(
        **deterministic_binding.model_dump(mode="json"),
        deterministic_validation_hash=deterministic_hash,
        reviewer_standard_hash=reviewer_standard_hash,
    )
    expected_payload = expected_review_binding.model_dump(mode="json")

    if independent_review is None:
        reasons.append("independent_review_missing_or_invalid")
    elif independent_review.get("acceptance_binding") != expected_payload:
        reasons.append("independent_review_acceptance_binding_mismatch")
    if final_verdict is None:
        reasons.append("final_verdict_missing_or_invalid")
    elif final_verdict.get("acceptance_binding") != expected_payload:
        reasons.append("final_verdict_acceptance_binding_mismatch")
    if require_no_op:
        if no_op_proof is None:
            reasons.append("no_op_proof_missing_or_invalid")
        elif no_op_proof.get("acceptance_binding") != expected_payload:
            reasons.append("no_op_acceptance_binding_mismatch")
    return reasons


__all__ = [
    "DeterministicAcceptanceBindingV1",
    "ReviewAcceptanceBindingV1",
    "bind_deterministic_validation",
    "build_review_acceptance_binding",
    "validate_acceptance_artifact_chain",
]
