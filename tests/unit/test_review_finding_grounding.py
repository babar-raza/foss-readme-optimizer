"""Deterministic grounding controls for fallible reviewer findings."""

import json

from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
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


def test_reviewer_cannot_require_one_edge_per_input_when_grouped_topology_is_valid():
    mermaid = """```mermaid
flowchart LR
  subgraph INPUTS["Inputs & Formats"]
    I1["OBJ"]
    I2["GLTF"]
  end
  PRODUCT["Aspose.3D FOSS<br/>for Python"]
  subgraph CORE["Core Capabilities"]
    C1["Create scenes"]
  end
  subgraph OUTPUTS["Outputs"]
    O1["GLTF"]
  end
  I1 --> PRODUCT
  PRODUCT --> CORE
  CORE --> O1
```"""
    candidate = f"# Product\n\n## At a Glance\n\n{mermaid}\n"
    finding = GroundedReviewFindingV1(
        finding_id="quality.false-mermaid-topology",
        kind="quality",
        criterion="markdown_integrity",
        section="at-a-glance",
        claim=(
            "The Mermaid diagram omits required input-to-product edges for I2 and omits "
            "the product-to-capabilities edge."
        ),
        quoted_candidate_span=mermaid,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Add I2 --> PRODUCT and a group-level PRODUCT --> CORE edge.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("input-edge premise" in error for error in result.errors)
    assert any("product-to-capabilities premise" in error for error in result.errors)


def test_reviewer_cannot_claim_configured_workflow_preview_is_missing():
    preview = (
        "The examples below demonstrate loading OBJ files with materials, exporting a scene "
        "to binary GLTF, and converting a parametric primitive to a mesh."
    )
    candidate = (
        "# Product\n\n## Additional Examples\n\n"
        f"{preview}\n\n<details>\n<summary>View additional examples and results</summary>\n\n"
        "### Load OBJ Files with Materials\n\nExample.\n</details>\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="quality.false-example-intro",
        kind="quality",
        criterion="example_presentation",
        section="additional-examples",
        claim="The section lacks a brief introductory sentence that contextualizes workflows.",
        quoted_candidate_span="### Load OBJ Files with Materials",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Add a concise, natural-language overview paragraph before the heading.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("intro premise contradicts" in error for error in result.errors)


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


def test_provenance_bound_finding_resolves_when_the_bound_fact_fully_grounds_it():
    """PWD-004: `aspose-cells-foss/…Cpp` cited a real
    `template.section.api_reference.claim:*` content-provenance ID as if it were a
    fact ID -- previously rejected outright as "unknown fact ID" even though claim
    accountability had already independently bound that exact span to a real, verified
    fact. A provenance-cited finding must earn acceptance through the identical checks
    a direct fact citation always has, not a relaxed path."""

    facts = {
        **FACTS,
        "content_provenance": [
            {
                "provenance_id": "template.section.api_reference.claim:427:deadbeef",
                "fact_ids": ["fact.install"],
            }
        ],
    }
    finding = _finding(fact_id="template.section.api_reference.claim:427:deadbeef")

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=facts,
        findings=[finding],
    )

    assert result.valid


def test_provenance_bound_finding_still_rejects_when_no_bound_fact_fully_grounds_it():
    facts = {
        **FACTS,
        "content_provenance": [
            {
                "provenance_id": "template.section.api_reference.claim:427:deadbeef",
                "fact_ids": ["fact.install"],
            }
        ],
    }
    finding = _finding(
        fact_id="template.section.api_reference.claim:427:deadbeef",
        evidence_location="wrong/location",
    )

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=facts,
        findings=[finding],
    )

    assert not result.valid
    assert any(
        "no fact bound to provenance" in error and "fully grounds this finding" in error
        for error in result.errors
    )


def test_provenance_binding_accepts_if_at_least_one_of_several_bound_facts_grounds_it():
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
                "source": {"location": "wrong/location"},
                "conflicts": [],
            },
        ],
        "content_provenance": [
            {
                "provenance_id": "template.section.api_reference.claim:427:deadbeef",
                "fact_ids": ["fact.docs", "fact.install"],
            }
        ],
    }
    finding = _finding(fact_id="template.section.api_reference.claim:427:deadbeef")

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=facts,
        findings=[finding],
    )

    assert result.valid


def test_invented_provenance_id_absent_from_content_provenance_is_still_unknown():
    facts = {
        **FACTS,
        "content_provenance": [
            {
                "provenance_id": "template.section.api_reference.claim:427:deadbeef",
                "fact_ids": ["fact.install"],
            }
        ],
    }
    finding = _finding(fact_id="template.section.api_reference.claim:999:invented")

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=facts,
        findings=[finding],
    )

    assert not result.valid
    assert any("unknown fact ID" in error for error in result.errors)


def test_provenance_binding_with_no_fact_ids_at_all_is_rejected_not_vacuously_accepted():
    facts = {
        **FACTS,
        "content_provenance": [
            {"provenance_id": "template.section.api_reference.claim:427:deadbeef", "fact_ids": []}
        ],
    }
    finding = _finding(fact_id="template.section.api_reference.claim:427:deadbeef")

    result = validate_review_findings(
        candidate_text=CANDIDATE,
        product_facts=facts,
        findings=[finding],
    )

    assert not result.valid
    assert any("binds no facts" in error for error in result.errors)


def test_claim_literal_mismatch_retry_gets_an_explicit_correction_rule():
    """PWD-016: this error had no bespoke retry guidance at all -- the model saw only the
    generic error text and its own prior claim/quote, with nothing explaining *how* to widen
    quoted_candidate_span to cover every literal its claim names. Live on
    aspose-cells-foss/…Python, the same repository regenerated a new claim tripping this
    identical check on every one of 3 retry attempts."""

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

    retry = json.loads(
        grounding_retry_context(
            errors=[
                "quality.misaligned-summary:quoted span does not contain the exact literal "
                "named by the claim"
            ],
            candidate_text="irrelevant",
            product_facts=None,
            findings=(finding,),
        )
    )

    assert any(
        "literally present inside that finding's own quoted_candidate_span" in rule
        for rule in retry["required_correction"]["output_contract_rules"]
    )


def test_unrelated_retry_errors_do_not_add_the_claim_literal_correction_rule():
    retry = json.loads(
        grounding_retry_context(
            errors=["factual.install:evidence location disagrees with cited fact"],
            candidate_text="irrelevant",
            product_facts=None,
            findings=(),
        )
    )

    assert not any(
        "literally present inside that finding's own quoted_candidate_span" in rule
        for rule in retry["required_correction"]["output_contract_rules"]
    )


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
