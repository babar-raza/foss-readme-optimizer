"""Deterministic grounding controls for fallible reviewer findings."""

import json

from readme_agent.specialists.review_finding_grounding import (
    GroundedReviewFindingV1,
    grounding_retry_context,
    validate_review_findings,
)

CANDIDATE = (
    "# Example\n\nInstall with `dotnet add package Example`.\nProcesses 10,000 files per second.\n"
)
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
        "disposition": "blocks",
        "fact_id": "fact.install",
        "evidence_excerpt": "throw new NotSupportedException()",
        "evidence_location": "src/Example.cs",
        "expected_polarity": "positive_implementation",
        "observed_polarity": "explicit_constraint",
        "polarity_result": "contradicts",
        "required_repair": "",
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
        findings=[
            _finding(
                disposition="supports_acceptance",
                polarity_result="supports",
            )
        ],
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


def test_evidence_binding_retry_exposes_every_bounded_packet_fact():
    facts = {
        "selected_fact_ids": {
            "installation.coordinates": "fact.install",
            "documentation.links": "fact.docs",
        },
        "facts": [
            *FACTS["facts"],
            {
                "fact_id": "fact.docs",
                "field": "documentation.links",
                "value": "https://docs.example.test/",
                "verification_state": "verified",
                "source": {"location": "data/links.json"},
                "conflicts": [],
            },
        ],
    }
    wrong_choice = _finding(
        fact_id="fact.docs",
        evidence_excerpt="https://docs.example.test/",
        evidence_location="data/links.json",
    )

    retry = json.loads(
        grounding_retry_context(
            errors=[
                "factual.install:evidence location disagrees with cited fact",
                "factual.install:evidence excerpt is not bound to cited fact",
            ],
            candidate_text=CANDIDATE,
            product_facts=facts,
            findings=(wrong_choice,),
        )
    )

    assert retry["selected_fact_ids"] == {
        "documentation.links": "fact.docs",
        "installation.coordinates": "fact.install",
    }
    assert {fact["fact_id"] for fact in retry["accepted_fact_evidence"]} == {
        "fact.docs",
        "fact.install",
    }


def test_genuinely_unsupported_claim_remains_valid_missing_evidence():
    finding = GroundedReviewFindingV1(
        finding_id="factual.unsupported-throughput",
        kind="factual",
        criterion="factuality",
        section="Performance",
        claim="The candidate claims unsupported throughput.",
        quoted_candidate_span="Processes 10,000 files per second.",
        disposition="blocks",
        fact_id=None,
        evidence_excerpt=None,
        evidence_location=None,
        expected_polarity=None,
        observed_polarity=None,
        polarity_result="missing",
        required_repair="",
    )

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[finding],
    )

    assert result.valid


def test_quality_claim_cannot_name_a_literal_outside_its_supporting_quote():
    candidate = (
        "# Example\n\n## Additional Examples\n\n"
        "The examples cover loading models and exporting scenes.\n\n"
        "<details>\n<summary>View additional examples and results</summary>\n</details>\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="quality.misaligned-summary",
        kind="quality",
        criterion="clarity",
        section="additional-examples",
        claim="The summary 'View additional examples and results' is generic.",
        quoted_candidate_span="The examples cover loading models and exporting scenes.",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Replace the summary with a workflow preview.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
    )

    assert not result.valid
    assert any("exact literal named by the claim" in error for error in result.errors)


def test_blind_factual_accuracy_criterion_cannot_control_review():
    finding = GroundedReviewFindingV1(
        finding_id="quality.package-availability",
        kind="quality",
        criterion="installation_instruction_accuracy",
        section="Installation",
        claim="The package is not published.",
        quoted_candidate_span="dotnet add package Example",
        disposition="requires_repair",
        fact_id=None,
        evidence_excerpt=None,
        evidence_location=None,
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


def test_missing_evidence_cannot_deny_literal_selected_fact():
    finding = GroundedReviewFindingV1(
        finding_id="factual.false-missing",
        kind="factual",
        criterion="factuality",
        section="Installation",
        claim="The Example package lacks accepted evidence.",
        quoted_candidate_span="dotnet add package Example",
        disposition="blocks",
        fact_id=None,
        evidence_excerpt=None,
        evidence_location=None,
        expected_polarity=None,
        observed_polarity=None,
        polarity_result="missing",
        required_repair="",
    )

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[finding],
    )

    assert not result.valid
    assert "missing-evidence premise contradicts accepted facts" in result.errors[0]


def test_identity_literal_cannot_disprove_a_broader_unsupported_capability_claim():
    facts = {
        "selected_fact_ids": {"product.identity": "fact.identity"},
        "facts": [
            {
                "fact_id": "fact.identity",
                "field": "product.identity",
                "verification_state": "verified",
                "value": "Widget",
                "source": {"location": "pyproject.toml"},
                "conflicts": [],
            }
        ],
    }
    broad_claim = {
        "finding_id": "factual.unsupported-export",
        "kind": "factual",
        "criterion": "factuality",
        "section": "Capabilities",
        "claim": "Widget exports PDF but the capability lacks accepted evidence.",
        "disposition": "blocks",
        "polarity_result": "missing",
        "required_repair": "",
    }

    for quote in ("Widget exports PDF", "Widget"):
        finding = GroundedReviewFindingV1.model_validate(
            {**broad_claim, "quoted_candidate_span": quote}
        )
        candidate = f"# Widget\n\n{quote}\n"
        result = validate_review_findings(
            candidate_text=candidate,
            product_facts=facts,
            findings=[finding],
        )

        assert result.valid


def test_api_false_missing_retry_projects_every_symbol_in_the_bounded_unit():
    candidate = (
        "| `BoundingBox` | Supports retrieving infinite and retrieving null. |\n"
        "| `Vector3` | Supports angling between. |"
    )
    finding = GroundedReviewFindingV1(
        finding_id="factual.api-missing",
        kind="factual",
        criterion="factuality",
        section="API Reference",
        claim="The BoundingBox and Vector3 rows lack accepted evidence.",
        quoted_candidate_span="`BoundingBox`",
        disposition="blocks",
        polarity_result="missing",
        required_repair="",
    )
    facts = {
        "selected_fact_ids": {"api.public_surface": "fact.api"},
        "facts": [
            {
                "fact_id": "fact.api",
                "field": "api.public_surface",
                "verification_state": "verified",
                "value": {
                    "modules": [
                        {
                            "module": "example.utilities",
                            "exports": ["BoundingBox", "Vector3", "Unmentioned"],
                            "source_path": "example/utilities/__init__.py",
                        }
                    ],
                    "classes": [
                        {
                            "name": "BoundingBox",
                            "module": "example.utilities",
                            "qualified_name": "example.utilities.BoundingBox",
                            "constructor": {"surface": "BoundingBox()"},
                            "members": [
                                {
                                    "name": "get_infinite",
                                    "surface": "get_infinite()",
                                    "implemented": True,
                                },
                                {
                                    "name": "get_null",
                                    "surface": "get_null()",
                                    "implemented": True,
                                },
                            ],
                            "source_path": "example/utilities/BoundingBox.py",
                        },
                        {
                            "name": "Vector3",
                            "module": "example.utilities",
                            "qualified_name": "example.utilities.Vector3",
                            "constructor": {"surface": "Vector3()"},
                            "members": [
                                {
                                    "name": "angle_between",
                                    "surface": "angle_between(a, b)",
                                    "implemented": True,
                                }
                            ],
                            "source_path": "example/utilities/Vector3.py",
                        },
                        {"name": "Unmentioned", "module": "example.utilities"},
                    ],
                },
                "source": {"location": "repository://example/utilities"},
                "conflicts": [],
            }
        ],
    }

    retry = json.loads(
        grounding_retry_context(
            errors=[
                "factual.api-missing:missing-evidence premise contradicts accepted facts "
                "['fact.api']"
            ],
            candidate_text=candidate,
            product_facts=facts,
            findings=(finding,),
        )
    )

    value = retry["accepted_fact_evidence"][0]["value"]
    assert value["projection_contextual"] is True
    assert value["module_exports"][0]["exports"] == ["BoundingBox", "Vector3"]
    assert [item["name"] for item in value["classes"]] == ["BoundingBox", "Vector3"]
    assert [item["name"] for item in value["classes"][0]["public_members"]] == [
        "get_infinite",
        "get_null",
    ]


def test_supported_finding_requires_exact_fact_location():
    supported = _finding(
        disposition="supports_acceptance",
        polarity_result="supports",
        expected_polarity="positive_implementation",
        observed_polarity="positive_implementation",
        evidence_location="wrong/location",
        required_repair="",
    )

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=FACTS,
        findings=[supported],
    )

    assert not result.valid
    assert any("evidence location disagrees" in error for error in result.errors)
