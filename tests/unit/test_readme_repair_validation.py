"""Candidate-delta and source-operation controls for reviewer-directed repair."""

import hashlib
from types import SimpleNamespace

import pytest

from readme_agent.specialists.readme_repair_validation import (
    build_repair_attempt_receipt,
    finalize_repair_receipt,
    repair_findings,
    validate_repair_source_binding,
)

BEFORE = "# Product\n\n## Overview\n\nGeneric overview.\n"
AFTER = "# Product\n\n## Overview\n\nRepository-specific overview.\n"


def _operation(replacement: str) -> dict:
    return {
        "operation_id": "replace-overview",
        "operation": "replace",
        "rationale": "Repair Overview product_specificity finding.",
        "replacement_text": replacement,
        "replacement_sha256": replacement,
    }


def _context(candidate: str, replacement: str) -> dict:
    return {
        "final_text": candidate,
        "presentation_plan": {
            "readme_document_plan": {
                "operations": [_operation(replacement)],
            }
        },
    }


def _grounded_review():
    finding = SimpleNamespace(
        finding_id="quality.generic-overview",
        section="Overview",
        criterion="product_specificity",
        quoted_candidate_span="Generic overview.",
        required_repair="Replace the generic overview with repository-specific content.",
        disposition="requires_repair",
    )
    return SimpleNamespace(
        blind_quality_review=SimpleNamespace(findings=[finding]),
        factual_plan_review=SimpleNamespace(findings=[]),
        failed_criteria=["product_specificity"],
        sections_affected=["Overview"],
        required_repair=finding.required_repair,
    )


def test_changed_bound_operation_authorizes_rereview_and_records_resolution():
    review = _grounded_review()

    receipt = build_repair_attempt_receipt(
        prior_context=_context(BEFORE, "Generic overview."),
        repaired_context=_context(AFTER, "Repository-specific overview."),
        review=review,
        repair_attempt=1,
        reviewer_call_count=1,
    )

    assert receipt.candidate_changed is True
    assert receipt.changed_spans
    assert receipt.changed_operation_ids == ["replace-overview"]
    assert receipt.addressed_finding_ids == ["quality.generic-overview"]
    assert receipt.rereview_authorized is True
    assert receipt.finding_resolutions[0].changed_bound_operation_ids == ["replace-overview"]

    resolved = finalize_repair_receipt(
        receipt,
        rereview_verdict="ACCEPT",
        reviewer_call_count=2,
    )
    assert resolved.resolved_finding_ids == ["quality.generic-overview"]
    assert resolved.unresolved_finding_ids == []
    assert resolved.reviewer_call_count_after_rereview == 2


def test_byte_identical_or_unbound_change_denies_rereview():
    review = _grounded_review()
    identical = build_repair_attempt_receipt(
        prior_context=_context(BEFORE, "Generic overview."),
        repaired_context=_context(BEFORE, "Generic overview."),
        review=review,
        repair_attempt=1,
        reviewer_call_count=1,
    )
    unbound = build_repair_attempt_receipt(
        prior_context={
            "final_text": BEFORE,
            "presentation_plan": {
                "readme_document_plan": {
                    "operations": [
                        {
                            **_operation("Original footer."),
                            "operation_id": "replace-unrelated-footer",
                            "rationale": "Preserve an unrelated footer.",
                        }
                    ]
                }
            },
        },
        repaired_context={
            "final_text": AFTER,
            "presentation_plan": {
                "readme_document_plan": {
                    "operations": [
                        {
                            **_operation("Footer changed."),
                            "operation_id": "replace-unrelated-footer",
                            "rationale": "Change an unrelated footer.",
                        }
                    ]
                }
            },
        },
        review=review,
        repair_attempt=1,
        reviewer_call_count=1,
    )

    assert identical.rereview_authorized is False
    assert identical.changed_spans == []
    assert identical.unresolved_finding_ids == ["quality.generic-overview"]
    assert unbound.candidate_changed is True
    assert unbound.rereview_authorized is False
    assert unbound.unresolved_finding_ids == ["quality.generic-overview"]


def test_candidate_change_without_source_operations_denies_rereview():
    receipt = build_repair_attempt_receipt(
        prior_context={"final_text": BEFORE, "presentation_plan": {}},
        repaired_context={"final_text": AFTER, "presentation_plan": {}},
        review=_grounded_review(),
        repair_attempt=1,
        reviewer_call_count=1,
    )

    assert receipt.candidate_changed is True
    assert receipt.changed_operation_ids == []
    assert receipt.rereview_authorized is False
    assert receipt.unresolved_finding_ids == ["quality.generic-overview"]


def test_every_cited_finding_must_have_a_responsible_delta_before_rereview():
    before = (
        "# Product\n\n## Overview\n\nGeneric overview.\n\n## Usage\n\nGeneric usage guidance.\n"
    )
    after_one = (
        "# Product\n\n## Overview\n\nRepository-specific overview.\n\n"
        "## Usage\n\nGeneric usage guidance.\n"
    )
    after_both = (
        "# Product\n\n## Overview\n\nRepository-specific overview.\n\n"
        "## Usage\n\nRun the verified repository example.\n"
    )
    findings = [
        SimpleNamespace(
            finding_id="quality.generic-overview",
            section="Overview",
            criterion="product_specificity",
            quoted_candidate_span="Generic overview.",
            required_repair="Replace the generic overview.",
            disposition="requires_repair",
        ),
        SimpleNamespace(
            finding_id="quality.generic-usage",
            section="Usage",
            criterion="actionability",
            quoted_candidate_span="Generic usage guidance.",
            required_repair="Replace the generic usage guidance.",
            disposition="requires_repair",
        ),
    ]
    review = SimpleNamespace(
        blind_quality_review=SimpleNamespace(findings=findings),
        factual_plan_review=SimpleNamespace(findings=[]),
        failed_criteria=["product_specificity", "actionability"],
        sections_affected=["Overview", "Usage"],
        required_repair="Repair every cited section.",
    )
    before_context = {
        "final_text": before,
        "presentation_plan": {
            "readme_document_plan": {
                "operations": [
                    {
                        **_operation("Generic overview."),
                        "operation_id": "replace-overview",
                    },
                    {
                        **_operation("Generic usage guidance."),
                        "operation_id": "replace-usage",
                        "rationale": "Repair Usage actionability finding.",
                    },
                ]
            }
        },
    }
    after_one_context = {
        "final_text": after_one,
        "presentation_plan": {
            "readme_document_plan": {
                "operations": [
                    _operation("Repository-specific overview."),
                    {
                        **_operation("Generic usage guidance."),
                        "operation_id": "replace-usage",
                        "rationale": "Repair Usage actionability finding.",
                    },
                ]
            }
        },
    }
    after_both_context = {
        "final_text": after_both,
        "presentation_plan": {
            "readme_document_plan": {
                "operations": [
                    _operation("Repository-specific overview."),
                    {
                        **_operation("Run the verified repository example."),
                        "operation_id": "replace-usage",
                        "rationale": "Repair Usage actionability finding.",
                    },
                ]
            }
        },
    }

    partial = build_repair_attempt_receipt(
        prior_context=before_context,
        repaired_context=after_one_context,
        review=review,
        repair_attempt=1,
        reviewer_call_count=1,
    )
    complete = build_repair_attempt_receipt(
        prior_context=before_context,
        repaired_context=after_both_context,
        review=review,
        repair_attempt=1,
        reviewer_call_count=1,
    )
    resolved = finalize_repair_receipt(
        complete,
        rereview_verdict="ACCEPT",
        reviewer_call_count=2,
    )

    assert partial.rereview_authorized is False
    assert partial.addressed_finding_ids == ["quality.generic-overview"]
    assert partial.unresolved_finding_ids == ["quality.generic-usage"]
    assert complete.rereview_authorized is True
    assert complete.changed_operation_ids == ["replace-overview", "replace-usage"]
    assert resolved.resolved_finding_ids == [
        "quality.generic-overview",
        "quality.generic-usage",
    ]
    assert resolved.unresolved_finding_ids == []


def test_repair_request_preserves_grounded_finding_identity():
    findings = repair_findings(_grounded_review())

    assert [finding.finding_id for finding in findings] == ["quality.generic-overview"]
    assert findings[0].quoted_candidate_span == "Generic overview."


def test_stale_reviewer_candidate_hash_is_rejected_before_composition():
    review = _grounded_review()
    review.blind_quality_review.candidate_sha256 = "0" * 64
    review.factual_plan_review.candidate_sha256 = hashlib.sha256(BEFORE.encode()).hexdigest()

    with pytest.raises(ValueError, match="stale against the source candidate"):
        validate_repair_source_binding(review, BEFORE)
