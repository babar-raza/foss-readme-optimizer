"""Regression for PWD-031: opaque `repair_rerouted`/`repair_exhausted` status strings."""

from __future__ import annotations

from readme_agent.specialists.independent_readme_review import (
    IndependentReadmeReviewResultV1,
    RepairLoopOutcomeV1,
)
from readme_agent.specialists.readme_presentation_review import (
    _independent_review_error_status,
)

_REJECT_REPAIRABLE_REVIEW = IndependentReadmeReviewResultV1(
    verdict="REJECT_REPAIRABLE",
    reasoning="the installation section overclaims a bundled CLI",
    failed_criteria=["factual_grounding"],
    sections_affected=["installation"],
    required_repair="remove the CLI claim or cite a supporting fact",
)


def test_repair_rerouted_status_surfaces_the_real_escalation_reason():
    """Real bug: three repositories (`aspose-3d-foss/Aspose.3D-FOSS-for-Python`,
    `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, `aspose-slides-foss/Aspose.Slides-FOSS-
    for-Python`) all showed the byte-identical, zero-detail
    `ERROR:independent_review_repair_rerouted:REJECT_REPAIRABLE`, even though
    `reroute_unchanged_repair()` already computes a specific reason (before/after candidate
    hashes, unresolved finding ids) into `escalation["reason"]`."""

    outcome = RepairLoopOutcomeV1(
        outcome_kind="repair_rerouted",
        final_review=_REJECT_REPAIRABLE_REVIEW,
        attempts=1,
        review_call_count=2,
        escalation={
            "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            "status": "README_ASSESSED",
            "reason": (
                "agent_fixable: reviewer-directed repair did not materially change every "
                "responsible span/operation; before=aaaa after=aaaa; unresolved=finding-1"
            ),
        },
    )

    status = _independent_review_error_status(outcome)

    assert status == (
        "ERROR:independent_review_repair_rerouted:REJECT_REPAIRABLE: "
        "agent_fixable: reviewer-directed repair did not materially change every "
        "responsible span/operation; before=aaaa after=aaaa; unresolved=finding-1"
    )


def test_repair_exhausted_status_surfaces_the_real_escalation_reason():
    outcome = RepairLoopOutcomeV1(
        outcome_kind="repair_exhausted",
        final_review=_REJECT_REPAIRABLE_REVIEW,
        attempts=2,
        review_call_count=3,
        escalation={
            "repository": "org/repo",
            "status": "AGENT_REVIEW_REJECTED",
            "reason": (
                "independent_readme_review: repair attempts exhausted (2/2), "
                "still REJECT_REPAIRABLE"
            ),
        },
    )

    status = _independent_review_error_status(outcome)

    assert status == (
        "ERROR:independent_review_repair_exhausted:REJECT_REPAIRABLE: "
        "independent_readme_review: repair attempts exhausted (2/2), still REJECT_REPAIRABLE"
    )


def test_blocked_outcome_without_escalation_keeps_the_original_bare_status():
    """Negative control: `blocked`/`accepted` outcomes never populate `escalation` (only the
    repair loop does), so the fix must not invent a reason where none exists -- this is the
    exact pre-fix call shape and must still produce the original bare string."""

    outcome = RepairLoopOutcomeV1(
        outcome_kind="blocked",
        final_review=IndependentReadmeReviewResultV1(
            verdict="BLOCKED_MISSING_EVIDENCE",
            reasoning="no accepted fact supports this claim",
            failed_criteria=["factual_grounding"],
            sections_affected=["scope-and-limitations"],
        ),
        attempts=0,
        review_call_count=1,
        escalation=None,
    )

    status = _independent_review_error_status(outcome)

    assert status == "ERROR:independent_review_blocked:BLOCKED_MISSING_EVIDENCE"
