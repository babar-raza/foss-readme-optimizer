"""Revalidate fidelity after one provenance-complete exact removal."""

from __future__ import annotations

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_candidate_ownership_models import TrustedRepairActionV1
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.specialists.trusted_fidelity_validation import (
    normalize_trusted_fidelity_output,
    validate_trusted_fidelity_result,
)
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
    TrustedReviewRoleRecordV1,
)

_RESULT_FIELDS = frozenset(TrustedFidelityReviewResultV1.model_fields)


def derive_fidelity_after_exact_removal(
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    prior_record: TrustedReviewRoleRecordV1,
    action: TrustedRepairActionV1,
) -> TrustedFidelityReviewResultV1:
    """Reconcile accepted fact checks after an exact action removes bytes."""

    if action.action != "remove_exact" or action.replacement_text:
        raise LLMError("fidelity delta proof supports only exact byte removal")
    if (
        action.org_repo != graph.org_repo
        or action.source_revision != graph.source_revision
        or action.candidate_sha256_before != prior_record.candidate_sha256
        or action.candidate_sha256_after != composition.candidate_sha256
    ):
        raise LLMError("fidelity delta proof inputs belong to different candidates")
    prior = TrustedFidelityReviewResultV1.model_validate(
        {key: value for key, value in prior_record.result.items() if key in _RESULT_FIELDS}
    )
    if prior.verdict == "SYSTEM_FAILURE":
        raise LLMError("fidelity delta proof requires a completed prior fidelity review")
    normalized = normalize_trusted_fidelity_output(
        prior.model_dump(mode="json"),
        graph=graph,
        candidate_text=composition.candidate_markdown,
    )
    if not isinstance(normalized, dict):
        raise LLMError("fidelity delta normalization returned an invalid payload")
    normalized["reasoning"] = (
        "Every inherited source unit was rechecked against the repaired candidate; "
        "no unsupported addition survived the provenance-bound removal."
        if normalized.get("verdict") == "ACCEPT"
        else "The repaired candidate was rechecked against every inherited source unit and "
        "surviving unsupported addition; bounded fidelity repair remains required."
    )
    result = TrustedFidelityReviewResultV1.model_validate(normalized)
    errors = validate_trusted_fidelity_result(
        result,
        graph,
        composition.candidate_markdown,
        authorization_graph=graph,
    )
    if errors:
        raise LLMError(f"fidelity delta proof failed deterministic validation: {errors}")
    return result
