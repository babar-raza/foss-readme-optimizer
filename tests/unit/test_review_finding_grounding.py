"""Deterministic grounding controls for fallible reviewer findings."""

from readme_agent.specialists.review_finding_grounding import (
    GroundedReviewFindingV1,
    validate_review_findings,
)

CANDIDATE = "# Example\n\nInstall with `dotnet add package Example`.\n"
FACTS = {
    "selected_fact_ids": {"installation.coordinates": "fact.install"},
    "facts": [
        {
            "fact_id": "fact.install",
            "verification_state": "verified",
            "value": "Example",
            "source": {"location": "src/Example.cs"},
            "conflicts": [],
            "evidence_assessments": [
                {
                    "expected_polarity": "positive_implementation",
                    "observed_polarity": "explicit_constraint",
                    "exact_excerpt": "throw new NotSupportedException()",
                    "context_excerpt": "Install is not supported.",
                    "anchor": "NotSupportedException",
                    "accepted": False,
                }
            ],
        }
    ],
}


def _finding(**updates):
    value = {
        "finding_id": "factual.install",
        "kind": "factual",
        "criterion": "factuality",
        "section": "Installation",
        "claim": "The install command is contradicted.",
        "quoted_candidate_span": "dotnet add package Example",
        "fact_id": "fact.install",
        "evidence_excerpt": "throw new NotSupportedException()",
        "expected_polarity": "positive_implementation",
        "observed_polarity": "explicit_constraint",
        "polarity_result": "contradicts",
        "required_repair": "Remove the unsupported command.",
    }
    value.update(updates)
    return GroundedReviewFindingV1.model_validate(value)


def test_exact_span_fact_evidence_and_wrong_direction_are_checked():
    valid = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[_finding()],
    )
    absent = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[_finding(quoted_candidate_span="invented candidate content")],
    )
    wrong_polarity = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[_finding(polarity_result="supports")],
    )

    assert valid.valid
    assert "quoted candidate span is absent" in absent.errors[0]
    assert any("wrong direction" in error for error in wrong_polarity.errors)


def test_unknown_or_unselected_fact_cannot_control_review():
    unknown = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[_finding(fact_id="fact.unknown")],
    )

    assert not unknown.valid
    assert any("unknown fact ID" in error for error in unknown.errors)


def test_genuinely_unsupported_claim_remains_valid_missing_evidence():
    finding = GroundedReviewFindingV1(
        finding_id="factual.unsupported-throughput",
        kind="factual",
        criterion="factuality",
        section="Performance",
        claim="The candidate claims unsupported throughput.",
        quoted_candidate_span="dotnet add package Example",
        fact_id=None,
        evidence_excerpt=None,
        expected_polarity=None,
        observed_polarity=None,
        polarity_result="missing",
        required_repair="Remove the unsupported claim.",
    )

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[finding],
    )

    assert result.valid


def test_blind_factual_accuracy_criterion_cannot_control_review():
    finding = GroundedReviewFindingV1(
        finding_id="quality.package-availability",
        kind="quality",
        criterion="installation_instruction_accuracy",
        section="Installation",
        claim="The package is not published.",
        quoted_candidate_span="dotnet add package Example",
        fact_id=None,
        evidence_excerpt=None,
        expected_polarity=None,
        observed_polarity=None,
        polarity_result="not_applicable",
        required_repair="Remove the package command.",
    )

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=None,
        findings=[finding],
    )

    assert not result.valid
    assert "outside blind visible-quality authority" in result.errors[0]
