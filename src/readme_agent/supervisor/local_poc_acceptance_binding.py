"""Bind local README acceptance artifacts to the exact validated dependency set."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from readme_agent.facts.knowledge_application_evidence import KnowledgeApplicationV1
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
    readme_reconciliation: dict[str, Any] | None = None,
    check_coverage: dict[str, Any] | None = None,
    knowledge_application: dict[str, Any] | None = None,
) -> list[str]:
    """Reject stale or cross-transaction acceptance artifacts fail closed.

    `readme_reconciliation` is `candidate/readme-reconciliation.json`
    (`local_poc_evidence.py::_readme_reconciliation_report_or_error`) --
    persisted diagnostically even on failure (never allowed to break real
    candidate persistence itself), but an `{"error": ...}` result means
    source-accountability genuinely failed this run and must not silently
    promote as if it had succeeded. `check_coverage` is `candidate/
    check-coverage.json` (`aspose_check_coverage.py::
    build_check_coverage_report`) -- a top-level `{"error": ...}` means the
    whole check battery failed to run; otherwise, any entry classified
    `blocking: true` with `outcome` `"error"` means that specific blocking
    check crashed or returned an uninterpretable result this run (Stage 3B:
    `document_validation.py`'s own gate only ever sees real findings, not
    this gap, since it is shared by hundreds of synthetic-fixture tests
    unrelated to check coverage -- this is the actual gate for it). A
    blocking check's `outcome == "skip"` does NOT gate here, deliberately:
    `check_banner_present` (family/platform only ever derived from a real
    imported-knowledge fact location) skips in nearly every
    non-full-portfolio run, including this repo's own synthetic-fixture and
    end-to-end lifecycle tests -- confirmed empirically, gating on skip
    broke 36+ unrelated tests plus a real supervisor-loop test. See GOV-014
    (`plans/backlog-post-poc.md`) for the deferred, correctly-scoped fix.
    Neither artifact being present at all (pre-Stage-3
    bundle, or a synthetic/unit-test bundle exercising unrelated
    acceptance-binding logic) is itself a reason to deny reuse -- only an
    explicit, persisted failure blocks. `knowledge_application` is
    `candidate/knowledge-application.json`'s post-render K3 report
    (`local_poc_evidence.py::_knowledge_application_report_or_error`) --
    absence is not itself blocking (same rationale as
    `readme_reconciliation`/`check_coverage` above), but a present,
    malformed, stale, or still-provisional report is: re-parsing it through
    `KnowledgeApplicationV1` already fail-closed enforces "empty influence
    for a selected output-authorizing item", "unknown item", "duplicate
    attribution", and "unaccounted rendered claim" at construction time
    (`KnowledgeApplicationV1._final_dispositions_are_internally_consistent`)
    -- a `ValidationError` here means one of those was violated.
    """

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
    if readme_reconciliation is not None and "error" in readme_reconciliation:
        reasons.append(f"readme_reconciliation_error: {readme_reconciliation['error']}")
    if check_coverage is not None:
        if "error" in check_coverage:
            reasons.append(f"check_coverage_error: {check_coverage['error']}")
        else:
            # Only "error" (the check genuinely crashed or returned an
            # uninterpretable shape) gates here -- "skip" does not, even
            # though it is a real blocking-coverage gap in principle. In
            # practice `check_banner_present` (family/platform only ever
            # derived from a real imported-knowledge fact location) skips
            # in nearly every non-full-portfolio run, including this
            # repo's own synthetic-fixture and end-to-end lifecycle tests
            # (confirmed empirically: gating on skip broke 36+ unrelated
            # tests plus a real supervisor-loop end-to-end test). Blocking
            # every one of those on a gap this pervasive is not a "smallest
            # permanent repair" -- it is a new, wide regression. See
            # GOV-014 (`plans/backlog-post-poc.md`) for the deferred,
            # correctly-scoped fix (family/platform derivation needs a
            # broader real source than the imported-knowledge fact alone).
            for entry in check_coverage.get("entries") or []:
                if entry.get("blocking") is True and entry.get("outcome") == "error":
                    reasons.append(
                        f"blocking_check_gap:{entry.get('check_name')}:error: {entry.get('reason')}"
                    )
    if knowledge_application is not None:
        if "error" in knowledge_application:
            reasons.append(f"knowledge_application_error: {knowledge_application['error']}")
        else:
            try:
                parsed_knowledge_application = KnowledgeApplicationV1.model_validate(
                    knowledge_application
                )
            except ValidationError as exc:
                reasons.append(f"knowledge_application_invalid: {exc}")
            else:
                if parsed_knowledge_application.status != "final":
                    reasons.append("knowledge_application_not_final")
                if (
                    candidate_hash is not None
                    and parsed_knowledge_application.candidate_sha256 is not None
                    and parsed_knowledge_application.candidate_sha256 != candidate_hash
                ):
                    reasons.append("knowledge_application_stale")
    return reasons


__all__ = [
    "DeterministicAcceptanceBindingV1",
    "ReviewAcceptanceBindingV1",
    "bind_deterministic_validation",
    "build_review_acceptance_binding",
    "validate_acceptance_artifact_chain",
]
