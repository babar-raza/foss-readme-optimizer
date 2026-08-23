"""Reconcile blind-review findings only where deterministic evidence settles the premise."""

from __future__ import annotations

from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_finding_grounding import (
    deterministically_disproven_finding_ids,
)
from readme_agent.specialists.review_role_normalization import normalize_redundant_role_fields


def reconcile_deterministically_disproven_blind_findings(
    parsed: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    errors: list[str],
) -> tuple[BlindQualityReviewResultV1 | FactualPlanReviewResultV1, tuple[str, ...]]:
    """Remove deterministically disproven blind findings and retain grounded siblings."""

    if not isinstance(parsed, BlindQualityReviewResultV1) or parsed.verdict == "SYSTEM_FAILURE":
        return parsed, ()
    disproven_ids = deterministically_disproven_finding_ids(errors)
    invalid_ids = {error.split(":", maxsplit=1)[0] for error in errors if ":" in error}
    invalid_ids.update(disproven_ids)
    finding_ids = {finding.finding_id for finding in parsed.findings}
    removable_ids = invalid_ids & finding_ids
    if not removable_ids:
        return parsed, ()
    retained = [finding for finding in parsed.findings if finding.finding_id not in removable_ids]
    if not retained:
        if finding_ids and finding_ids <= disproven_ids:
            supporting_findings = [
                finding.model_copy(
                    update={
                        "claim": (
                            "Deterministic validation disproved the proposed "
                            f"{finding.criterion} defect for this quoted candidate span."
                        ),
                        "disposition": "supports_acceptance",
                        "required_repair": "",
                    }
                )
                for finding in parsed.findings
            ]
            accepted = normalize_redundant_role_fields(
                "blind_quality",
                {
                    **parsed.model_dump(mode="json"),
                    "verdict": "ACCEPT",
                    "reasoning": (
                        "Deterministic grounding disproved every proposed quality defect; "
                        "no independently proposed repair finding remains."
                    ),
                    "findings": [item.model_dump(mode="json") for item in supporting_findings],
                },
            )
            return BlindQualityReviewResultV1.model_validate(accepted), tuple(sorted(removable_ids))
        return parsed, ()
    disposition = "repair" if parsed.verdict == "REJECT_REPAIRABLE" else "acceptance"
    normalized = normalize_redundant_role_fields(
        "blind_quality",
        {
            **parsed.model_dump(mode="json"),
            "reasoning": (
                "Deterministic grounding removed ungrounded quality findings and retained "
                f"{len(retained)} independently proposed {disposition} finding(s)."
            ),
            "findings": [finding.model_dump(mode="json") for finding in retained],
        },
    )
    return BlindQualityReviewResultV1.model_validate(normalized), tuple(sorted(removable_ids))


def clear_irrelevant_mechanical_references(
    parsed: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    errors: list[str],
) -> tuple[BlindQualityReviewResultV1 | FactualPlanReviewResultV1, tuple[str, ...]]:
    """Clear mechanical fields that the deterministic premise parser proved irrelevant."""

    if not isinstance(parsed, BlindQualityReviewResultV1):
        return parsed, ()
    irrelevant_ids = {
        error.split(":", maxsplit=1)[0]
        for error in errors
        if ":mechanical premise cites unrelated check " in error
    }
    if not irrelevant_ids:
        return parsed, ()
    findings = [
        finding.model_copy(update={"mechanical_check_id": None, "reported_observed_value": None})
        if finding.finding_id in irrelevant_ids
        else finding
        for finding in parsed.findings
    ]
    return (
        BlindQualityReviewResultV1.model_validate(
            {**parsed.model_dump(mode="json"), "findings": findings}
        ),
        tuple(sorted(irrelevant_ids)),
    )


__all__ = [
    "clear_irrelevant_mechanical_references",
    "reconcile_deterministically_disproven_blind_findings",
]
