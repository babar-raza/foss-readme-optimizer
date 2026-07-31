"""Runtime wiring for context-isolated README reviewer roles."""

import json

import pytest

from readme_agent.errors import LLMError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.specialists.review_candidate_anchors import build_candidate_review_anchors
from readme_agent.specialists.review_finding_grounding import (
    GroundedReviewFindingV1,
    grounding_retry_context,
    validate_review_findings,
)
from readme_agent.specialists.review_role_execution import (
    normalize_redundant_role_fields,
    run_grounded_role,
)
from readme_agent.specialists.separated_readme_review import run_separated_readme_review

ORG_REPO = "example/example-foss"
ORIGINAL = "# Example\n\nOriginal material.\n"
CANDIDATE = "# Example\n\nSpecific, useful candidate.\n"
FACTS = {
    "schema_version": 2,
    "selected_fact_ids": {"product.identity": "fact-1"},
    "facts": [
        {
            "fact_id": "fact-1",
            "field": "product.identity",
            "value": "Example",
            "verification_state": "verified",
            "source": {"location": "README.md"},
            "conflicts": [],
            "evidence_assessments": [
                {
                    "expected_polarity": "positive_implementation",
                    "observed_polarity": "explicit_constraint",
                    "exact_excerpt": "Example is not supported",
                    "context_excerpt": "Example is not supported",
                    "anchor": "not supported",
                    "accepted": False,
                }
            ],
        }
    ],
}
PLAN = {"operations": [{"operation_id": "readme.overview", "operation": "replace"}]}


class CapturingClient:
    def __init__(self, parsed):
        self.parsed = parsed
        self.messages = None

    def analyze(self, messages):
        self.messages = messages
        return AnalysisResult(parsed=self.parsed, meta=LLMResponseMeta())


class SequenceClient(CapturingClient):
    def __init__(self, parsed_items):
        self.parsed_items = parsed_items
        self.messages_seen = []

    def analyze(self, messages):
        self.messages_seen.append(messages)
        return AnalysisResult(
            parsed=self.parsed_items[len(self.messages_seen) - 1],
            meta=LLMResponseMeta(),
        )


def test_blind_grounding_rejects_findings_that_contradict_configured_presentation() -> None:
    candidate = (
        "# Widget\n\n"
        "![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)\n\n"
        "A focused open-source library.\n\n"
        "## At a glance\n\n```mermaid\nflowchart LR\n  A --> B\n```\n\n"
        "## Navigation\n\n- [Usage](#usage)\n\n"
        "## Usage\n\nUse the library.\n\n"
        "The [Enterprise Edition](https://products.aspose.com/widget/) extends the product.\n"
    )
    base = {
        "kind": "quality",
        "disposition": "requires_repair",
        "fact_id": None,
        "evidence_excerpt": None,
        "evidence_location": None,
        "expected_polarity": None,
        "observed_polarity": None,
        "polarity_result": "not_applicable",
    }
    findings = [
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "badge-spacing",
                "criterion": "hierarchy",
                "section": "Header",
                "claim": "The badge must appear immediately after the H1 without a blank line.",
                "quoted_candidate_span": "# Widget",
                "required_repair": "Remove the blank line after the H1.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "navigation-placement",
                "criterion": "navigation",
                "section": "At a glance",
                "claim": "The Navigation label is missing under the At a glance section.",
                "quoted_candidate_span": "## At a glance",
                "required_repair": (
                    "Add the required Navigation label under the At a glance section."
                ),
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "enterprise-opening",
                "criterion": "internal_terminology",
                "section": "Header",
                "claim": "Enterprise Edition must appear in the first paragraph after the badge.",
                "quoted_candidate_span": "A focused open-source library.",
                "required_repair": "Insert Enterprise Edition in the first paragraph.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "contextual-link-count",
                "criterion": "promotional_balance",
                "section": "Usage",
                "claim": "The README exceeds the configured contextual link maximum of three.",
                "quoted_candidate_span": "[Enterprise Edition](https://products.aspose.com/widget/)",
                "required_repair": "Reduce the contextual links to at most three.",
            }
        ),
    ]
    visitor_contract = {
        "configured_standards": [
            {"standard_id": "readme.badges", "parameters": {}},
            {"standard_id": "readme.navigation", "parameters": {}},
            {
                "standard_id": "readme.enterprise_edition_terminology",
                "parameters": {"required_term": "Enterprise Edition"},
            },
            {
                "standard_id": "readme.contextual_links",
                "parameters": {"max_total": 3, "domain_maxima": {"aspose.com": 2}},
            },
        ]
    }

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract=visitor_contract,
    )

    assert result.valid is False
    assert len(result.errors) == 4
    assert any("badge-spacing premise" in error for error in result.errors)
    assert any("navigation premise" in error for error in result.errors)
    assert any("opening-placement premise" in error for error in result.errors)
    assert any("link-budget premise" in error for error in result.errors)
    retry = json.loads(
        grounding_retry_context(
            errors=result.errors,
            candidate_text=candidate,
            product_facts=None,
            findings=tuple(findings),
            visitor_contract=visitor_contract,
        )
    )
    assert {item["disposition"] for item in retry["invalid_findings"]} == {
        "deterministically_disproven"
    }
    assert all("claim" not in item for item in retry["invalid_findings"])


def test_blind_acceptance_support_can_describe_satisfied_link_budget() -> None:
    candidate = (
        "# Widget\n\n"
        "See the [Enterprise Edition](https://products.aspose.com/widget/) when relevant.\n"
    )
    finding = GroundedReviewFindingV1.model_validate(
        {
            "finding_id": "contextual-link",
            "kind": "quality",
            "criterion": "promotional_balance",
            "section": "Resources",
            "claim": "The contextual link stays within the configured link budget.",
            "quoted_candidate_span": ("[Enterprise Edition](https://products.aspose.com/widget/)"),
            "disposition": "supports_acceptance",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "not_applicable",
            "required_repair": "",
        }
    )
    visitor_contract = {
        "configured_standards": [
            {
                "standard_id": "readme.contextual_links",
                "parameters": {"max_total": 1, "domain_maxima": {"aspose.com": 1}},
            }
        ]
    }

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=visitor_contract,
    )

    assert result.valid is True
    assert result.errors == []


def test_blind_reviewer_cannot_call_a_descriptive_enterprise_link_bare() -> None:
    enterprise_url = "https://products.aspose.com/note/"
    paragraph = (
        "For broader requirements, use the "
        f"[Aspose.Note for Python Enterprise Edition]({enterprise_url})."
    )
    candidate = f"# Aspose.Note FOSS\n\n## Project scope and limitations\n\n{paragraph}\n"
    finding = GroundedReviewFindingV1.model_validate(
        {
            "finding_id": "bare-enterprise-link",
            "kind": "quality",
            "criterion": "hierarchy",
            "section": "Project scope and limitations",
            "claim": "The Enterprise Edition link appears as a bare URL.",
            "quoted_candidate_span": paragraph,
            "disposition": "requires_repair",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "not_applicable",
            "required_repair": "Replace the bare URL with a descriptive link label.",
        }
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.contextual_links",
                    "parameters": {
                        "required_enterprise_url": enterprise_url,
                        "required_aspose_com_occurrences": 1,
                    },
                }
            ]
        },
    )

    assert result.valid is False
    assert result.errors == [
        "bare-enterprise-link:bare-URL premise contradicts configured candidate",
    ]


def test_blind_reviewer_cannot_turn_required_navigation_floor_into_ceiling() -> None:
    navigation = (
        "- [At a glance](#at-a-glance)\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [Installation](#installation)\n"
        "- [Quick start](#quick-start)\n"
        "- [License](#license)"
    )
    candidate = f"# Widget\n\n## Navigation\n\n{navigation}\n\n## License\n\nMIT.\n"
    finding = GroundedReviewFindingV1.model_validate(
        {
            "finding_id": "navigation-floor",
            "kind": "quality",
            "criterion": "navigation",
            "section": "Navigation",
            "claim": "Navigation includes non-required labels, exceeding the required set.",
            "quoted_candidate_span": navigation,
            "disposition": "requires_repair",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "not_applicable",
            "required_repair": "Remove non-required labels and retain only the required set.",
        }
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.navigation",
                    "parameters": {
                        "required_labels": [
                            "At a glance",
                            "Key capabilities",
                            "Installation",
                            "Quick start",
                        ]
                    },
                },
                {
                    "standard_id": "readme.header",
                    "parameters": {
                        "required_h2_prefix": [
                            "At a glance",
                            "Navigation",
                            "Key capabilities",
                            "Installation",
                            "Quick start",
                        ]
                    },
                },
            ]
        },
    )

    assert result.valid is False
    assert result.errors == [
        "navigation-floor:navigation prefix-only premise is unconfigured",
    ]


def test_blind_reviewer_cannot_report_present_navigation_label_as_omitted() -> None:
    navigation = (
        "- [At a glance](#at-a-glance)\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [Installation](#installation)\n"
        "- [Quick start](#quick-start)"
    )
    finding = GroundedReviewFindingV1.model_validate(
        {
            "finding_id": "navigation-omission",
            "kind": "quality",
            "criterion": "navigation",
            "section": "Navigation",
            "claim": "Navigation omits the required Key capabilities label.",
            "quoted_candidate_span": navigation,
            "disposition": "requires_repair",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "not_applicable",
            "required_repair": "Add the missing required label.",
        }
    )

    result = validate_review_findings(
        candidate_text=f"# Widget\n\n## Navigation\n\n{navigation}\n",
        product_facts=None,
        findings=[finding],
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.navigation",
                    "parameters": {
                        "required_labels": [
                            "At a glance",
                            "Key capabilities",
                            "Installation",
                            "Quick start",
                        ]
                    },
                }
            ]
        },
    )

    assert result.errors == [
        "navigation-omission:required-navigation premise contradicts candidate",
    ]


def test_blind_reviewer_cannot_miss_blank_line_after_cited_code_fence() -> None:
    code = "for page in pages:\n    print(page)"
    candidate = f"# Widget\n\n## Quick start\n\n```python\n{code}\n```\n\n### Next example\n"
    finding = GroundedReviewFindingV1.model_validate(
        {
            "finding_id": "code-spacing",
            "kind": "quality",
            "criterion": "hierarchy",
            "section": "Quick start",
            "claim": "The first code block is missing the required blank line after it.",
            "quoted_candidate_span": code,
            "disposition": "requires_repair",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "not_applicable",
            "required_repair": "Add a blank line after the first code block.",
        }
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract={"configured_standards": []},
    )

    assert result.errors == [
        "code-spacing:blank-line premise contradicts candidate structure",
    ]


def test_blind_role_drops_disproven_sibling_and_keeps_grounded_repair() -> None:
    candidate = (
        "# Widget\n\n"
        "A library.\n\n"
        "See the [Enterprise Edition](https://products.aspose.com/widget/) when relevant.\n"
    )
    base = {
        "kind": "quality",
        "disposition": "requires_repair",
        "fact_id": None,
        "evidence_excerpt": None,
        "evidence_location": None,
        "expected_polarity": None,
        "observed_polarity": None,
        "polarity_result": "not_applicable",
    }
    parsed = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The opening is vague and the link budget is exceeded.",
        "failed_criteria": ["product_specificity", "promotional_balance"],
        "sections_affected": ["Overview", "Resources"],
        "required_repair": "Clarify the opening and remove links.",
        "findings": [
            {
                **base,
                "finding_id": "opening-specificity",
                "criterion": "product_specificity",
                "section": "Overview",
                "claim": "The opening does not identify the product's concrete purpose.",
                "quoted_candidate_span": "A library.",
                "required_repair": "State the concrete purpose and intended user.",
            },
            {
                **base,
                "finding_id": "contextual-link-count",
                "criterion": "promotional_balance",
                "section": "Resources",
                "claim": "The README exceeds the configured contextual link maximum of three.",
                "quoted_candidate_span": (
                    "[Enterprise Edition](https://products.aspose.com/widget/)"
                ),
                "required_repair": "Reduce contextual links to at most three.",
            },
        ],
    }
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="blind_quality",
        prompt_id="blind_readme_quality_review",
        client=client,
        messages=[],
        candidate_text=candidate,
        product_facts=None,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.contextual_links",
                    "parameters": {"max_total": 3, "domain_maxima": {"aspose.com": 2}},
                }
            ]
        },
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert [finding.finding_id for finding in result.findings] == ["opening-specificity"]
    assert result.failed_criteria == ["product_specificity"]
    assert result.sections_affected == ["Overview"]
    assert result.required_repair == "State the concrete purpose and intended user."
    assert grounding.valid is True
    assert len(client.messages_seen) == 1
    assert history[0]["valid"] is True
    assert history[0]["deterministically_dismissed_finding_ids"] == ["contextual-link-count"]
    assert "link-budget premise" in history[0]["pre_normalization_errors"][0]


def test_blind_rejection_derives_redundant_summary_from_detailed_findings() -> None:
    result = normalize_redundant_role_fields(
        "blind_quality",
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "The visible heading is duplicated.",
            "failed_criteria": ["hierarchy"],
            "sections_affected": ["Wrong section"],
            "required_repair": "Wrong aggregate repair.",
            "findings": [
                {
                    "finding_id": "duplicate-heading",
                    "kind": "quality",
                    "criterion": "visible_duplication",
                    "section": "Formats",
                    "claim": "The OBJ heading appears twice.",
                    "quoted_candidate_span": "### OBJ Format",
                    "disposition": "requires_repair",
                    "required_repair": "Remove the duplicate OBJ heading.",
                }
            ],
        },
    )

    assert result["failed_criteria"] == ["visible_duplication"]
    assert result["sections_affected"] == ["Formats"]
    assert result["required_repair"] == "Remove the duplicate OBJ heading."


def test_blind_rejection_derives_missing_finding_repair_from_its_claim() -> None:
    result = normalize_redundant_role_fields(
        "blind_quality",
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "The visible heading is duplicated.",
            "findings": [
                {
                    "finding_id": "duplicate-heading",
                    "kind": "quality",
                    "criterion": "visible_duplication",
                    "section": "Formats",
                    "claim": "The OBJ heading appears twice.",
                    "quoted_candidate_span": "### OBJ Format",
                    "disposition": "requires_repair",
                    "required_repair": "",
                }
            ],
        },
    )

    assert result["findings"][0]["required_repair"] == (
        "Repair the quoted Formats presentation defect: The OBJ heading appears twice."
    )
    assert result["required_repair"] == result["findings"][0]["required_repair"]


def _blind_accept(reason):
    return {
        "verdict": "ACCEPT",
        "reasoning": reason,
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "quality.clear-opening",
                "kind": "quality",
                "criterion": "clarity",
                "section": "overview",
                "claim": "The opening is clear.",
                "quoted_candidate_span": "Specific, useful candidate.",
                "disposition": "supports_acceptance",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "",
            }
        ],
    }


def _factual_accept(reason):
    return {
        "verdict": "ACCEPT",
        "reasoning": reason,
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "factual.identity-supported",
                "kind": "factual",
                "criterion": "factuality",
                "section": "title",
                "claim": "The candidate identity is supported.",
                "quoted_candidate_span": "Example",
                "disposition": "supports_acceptance",
                "fact_id": "fact-1",
                "evidence_excerpt": "Example",
                "evidence_location": "README.md",
                "expected_polarity": "positive_implementation",
                "observed_polarity": "positive_implementation",
                "polarity_result": "supports",
                "required_repair": "",
            }
        ],
    }


def test_two_accepts_produce_hash_bound_separate_records():
    blind = CapturingClient(_blind_accept("visitor-ready"))
    factual = CapturingClient(_factual_accept("facts and plan agree"))

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=blind,
        factual_client=factual,
    )

    assert result.verdict == "ACCEPT"
    assert result.combined_review.identity_separation_valid
    assert result.blind_quality_review.input_sha256 != result.factual_plan_review.input_sha256
    assert result.blind_quality_review.identity.prompt_id == "blind_readme_quality_review"
    assert result.factual_plan_review.identity.prompt_id == "factual_readme_plan_review"
    assert result.blind_quality_review.grounding_validation.valid
    assert result.factual_plan_review.grounding_validation.valid
    assert result.blind_quality_review.findings[0].disposition == "supports_acceptance"
    assert result.factual_plan_review.findings[0].evidence_location == "README.md"

    blind_context = "\n".join(message["content"] for message in blind.messages)
    factual_context = "\n".join(message["content"] for message in factual.messages)
    assert ORIGINAL in blind_context
    assert "fact-1" not in blind_context
    assert "readme.overview" not in blind_context
    assert ORIGINAL not in factual_context
    assert "fact-1" in factual_context
    assert "readme.overview" in factual_context


def test_factual_finding_identifier_is_canonicalized_without_changing_evidence():
    blind = CapturingClient(_blind_accept("visitor-ready"))
    factual_payload = _factual_accept("facts and plan agree")
    factual_payload["findings"][0]["finding_id"] = "readme.example:repair:heading:1702"
    factual = CapturingClient(factual_payload)

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=blind,
        factual_client=factual,
    )

    finding = result.factual_plan_review.findings[0]
    assert finding.finding_id == "readme.example-repair-heading-1702"
    assert finding.claim == "The candidate identity is supported."
    assert finding.fact_id == "fact-1"
    assert finding.evidence_excerpt == "Example"
    assert finding.evidence_location == "README.md"


def test_non_repair_finding_discards_inert_repair_text_without_changing_verdict():
    blind = CapturingClient(_blind_accept("visitor-ready"))
    factual_payload = _factual_accept("facts and plan agree")
    factual_payload["findings"][0]["required_repair"] = (
        "No repair is required because the candidate agrees with the plan."
    )

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=blind,
        factual_client=CapturingClient(factual_payload),
    )

    finding = result.factual_plan_review.findings[0]
    assert finding.disposition == "supports_acceptance"
    assert finding.required_repair == ""
    assert finding.claim == "The candidate identity is supported."


def test_supported_factual_polarity_is_derived_from_the_accepted_fact():
    factual_payload = _factual_accept("facts and plan agree")
    factual_payload["findings"][0]["expected_polarity"] = "ambiguous_occurrence"
    factual_payload["findings"][0]["observed_polarity"] = "ambiguous_occurrence"
    client = SequenceClient([factual_payload])

    result, history, grounding = run_grounded_role(
        role="factual_plan",
        prompt_id="factual_readme_plan_review",
        client=client,
        messages=[],
        candidate_text=CANDIDATE,
        product_facts=FACTS,
    )

    finding = result.findings[0]
    assert finding.disposition == "supports_acceptance"
    assert finding.expected_polarity == "positive_implementation"
    assert finding.observed_polarity == "positive_implementation"
    assert finding.polarity_result == "supports"
    assert grounding.valid is True
    assert len(client.messages_seen) == 1
    assert history[0]["reconciled_factual_polarity_ids"] == ["factual.identity-supported"]


def test_blind_rejection_vetoes_factual_acceptance():
    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=CapturingClient(
            {
                "verdict": "REJECT_REPAIRABLE",
                "reasoning": "The opening is generic.",
                "failed_criteria": ["product_specificity"],
                "sections_affected": ["overview"],
                "required_repair": "Name the concrete purpose.",
                "findings": [
                    {
                        "finding_id": "quality.generic-opening",
                        "kind": "quality",
                        "criterion": "product_specificity",
                        "section": "overview",
                        "claim": "The opening is generic.",
                        "quoted_candidate_span": "Specific, useful candidate.",
                        "disposition": "requires_repair",
                        "fact_id": None,
                        "evidence_excerpt": None,
                        "evidence_location": None,
                        "expected_polarity": None,
                        "observed_polarity": None,
                        "polarity_result": "not_applicable",
                        "required_repair": "Name the concrete purpose.",
                    }
                ],
            }
        ),
        factual_client=CapturingClient(_factual_accept("facts and plan agree")),
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert result.failed_criteria == ["product_specificity"]
    assert result.required_repair == (
        "Revise overview for product_specificity around exact span: Specific, useful candidate."
    )
    assert result.blind_quality_review.findings[0].finding_id == "quality.generic-opening"
    assert "Name the concrete purpose." not in result.required_repair
    assert "product_specificity" in result.required_repair


def test_factual_conflict_vetoes_blind_acceptance():
    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=CapturingClient(_blind_accept("visitor-ready")),
        factual_client=CapturingClient(
            {
                "verdict": "BLOCKED_FACT_CONFLICT",
                "reasoning": "The acquisition claim contradicts fact-1.",
                "failed_criteria": ["factuality"],
                "sections_affected": ["installation"],
                "required_repair": "",
                "findings": [
                    {
                        "finding_id": "factual.unsupported-installation",
                        "kind": "factual",
                        "criterion": "factuality",
                        "section": "installation",
                        "claim": "The candidate makes an unsupported acquisition claim.",
                        "quoted_candidate_span": "Specific, useful candidate.",
                        "disposition": "blocks",
                        "fact_id": "fact-1",
                        "evidence_excerpt": "Example is not supported",
                        "evidence_location": "README.md",
                        "expected_polarity": "positive_implementation",
                        "observed_polarity": "explicit_constraint",
                        "polarity_result": "contradicts",
                        "required_repair": "",
                    }
                ],
            }
        ),
    )

    assert result.verdict == "BLOCKED_FACT_CONFLICT"
    assert result.combined_review.verdict == "BLOCKED_FACT_CONFLICT"


def test_reviewer_standard_binds_both_role_prompts_not_legacy_prompt():
    from readme_agent.llm import prompt_registry

    standard = separated_reviewer_standard_hash()

    assert len(standard) == 64
    assert standard != prompt_registry.prompt_hash("independent_readme_review")


def test_ungrounded_quality_premise_gets_one_bounded_correction_turn():
    invalid = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The opening is generic.",
        "failed_criteria": ["product_specificity"],
        "sections_affected": ["overview"],
        "required_repair": "Name the purpose.",
        "findings": [
            {
                "finding_id": "quality.generic-opening",
                "kind": "quality",
                "criterion": "product_specificity",
                "section": "overview",
                "claim": "The opening is generic.",
                "quoted_candidate_span": "text that is not in the candidate",
                "disposition": "requires_repair",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "Name the purpose.",
            }
        ],
    }
    corrected = {
        **invalid,
        "findings": [
            {
                **invalid["findings"][0],
                "quoted_candidate_span": "Specific, useful candidate.",
            }
        ],
    }
    blind = SequenceClient([invalid, corrected])

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=blind,
        factual_client=CapturingClient(_factual_accept("facts and plan agree")),
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert len(blind.messages_seen) == 2
    assert result.grounding_retry_history[0]["valid"] is False
    assert result.grounding_retry_history[1]["valid"] is True
    assert "validation_errors" in blind.messages_seen[1][-1]["content"]


def test_whitespace_equivalent_candidate_quote_is_reconciled_without_retry() -> None:
    parsed = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The opening is too generic.",
        "failed_criteria": ["product_specificity"],
        "sections_affected": ["overview"],
        "required_repair": "Name the concrete product purpose.",
        "findings": [
            {
                "finding_id": "quality.generic-opening",
                "kind": "quality",
                "criterion": "product_specificity",
                "section": "overview",
                "claim": "The opening is generic.",
                "quoted_candidate_span": "Specific,\n  useful   candidate.",
                "disposition": "requires_repair",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "Name the concrete product purpose.",
            }
        ],
    }
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="blind_quality",
        prompt_id="blind_readme_quality_review",
        client=client,
        messages=[],
        candidate_text=CANDIDATE,
        product_facts=None,
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert result.findings[0].quoted_candidate_span == "Specific, useful candidate."
    assert grounding.valid is True
    assert len(client.messages_seen) == 1
    assert history[0]["reconciled_candidate_span_ids"] == ["quality.generic-opening"]


def test_uniquely_fused_markdown_quote_is_reconciled_without_retry() -> None:
    candidate = "# Example\n\n## Installation\n\nUse pip.\n"
    parsed = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The installation guidance is too thin.",
        "failed_criteria": ["installation_presentation"],
        "sections_affected": ["Installation"],
        "required_repair": "Add one concise prerequisite.",
        "findings": [
            {
                "finding_id": "quality.thin-installation",
                "kind": "quality",
                "criterion": "installation_presentation",
                "section": "Installation",
                "claim": "The installation guidance is too thin.",
                "quoted_candidate_span": "## InstallationUse pip.",
                "disposition": "requires_repair",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "Add one concise prerequisite.",
            }
        ],
    }
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="blind_quality",
        prompt_id="blind_readme_quality_review",
        client=client,
        messages=[],
        candidate_text=candidate,
        product_facts=None,
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert result.findings[0].quoted_candidate_span == "## Installation\n\nUse pip."
    assert grounding.valid is True
    assert len(client.messages_seen) == 1
    assert history[0]["reconciled_candidate_span_ids"] == ["quality.thin-installation"]


def test_blind_finding_uses_stable_candidate_anchor_instead_of_freehand_quote() -> None:
    candidate = "# Example\n\n## Quick start\n\nRun the focused example.\n"
    anchor = next(
        item
        for item in build_candidate_review_anchors(candidate)
        if item.text == "Run the focused example."
    )
    parsed = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The example lacks an outcome.",
        "failed_criteria": ["example_presentation"],
        "sections_affected": ["Quick start"],
        "required_repair": "State the expected outcome.",
        "findings": [
            {
                "finding_id": "quality.example-outcome",
                "kind": "quality",
                "criterion": "example_presentation",
                "section": "Quick start",
                "claim": "The example lacks an expected outcome.",
                "quoted_candidate_span": "Run the example ...",
                "candidate_anchor_id": anchor.anchor_id,
                "disposition": "requires_repair",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "State the expected outcome.",
            }
        ],
    }
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="blind_quality",
        prompt_id="blind_readme_quality_review",
        client=client,
        messages=[],
        candidate_text=candidate,
        product_facts=None,
    )

    assert result.findings[0].candidate_anchor_id == anchor.anchor_id
    assert result.findings[0].quoted_candidate_span == "Run the focused example."
    assert grounding.valid is True
    assert history[0]["valid"] is True


def test_blind_accept_drops_one_absent_quote_when_grounded_support_remains() -> None:
    parsed = {
        "verdict": "ACCEPT",
        "reasoning": "The candidate is specific and examples are clean.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "quality-specific",
                "kind": "quality",
                "criterion": "product_specificity",
                "section": "overview",
                "claim": "The opening is specific.",
                "quoted_candidate_span": "Specific, useful candidate.",
                "disposition": "supports_acceptance",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "",
            },
            {
                "finding_id": "quality-example",
                "kind": "quality",
                "criterion": "example_presentation",
                "section": "examples",
                "claim": "The example is clean.",
                "quoted_candidate_span": "barcode = code128(  )",
                "disposition": "supports_acceptance",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "",
            },
        ],
    }
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="blind_quality",
        prompt_id="blind_readme_quality_review",
        client=client,
        messages=[],
        candidate_text=CANDIDATE,
        product_facts=None,
    )

    assert result.verdict == "ACCEPT"
    assert [finding.finding_id for finding in result.findings] == ["quality-specific"]
    assert grounding.valid is True
    assert len(client.messages_seen) == 1
    assert history[0]["deterministically_dismissed_finding_ids"] == ["quality-example"]
    assert history[0]["invalid_findings"] == []
    assert "quoted candidate span is absent" in history[0]["pre_normalization_errors"][0]


def test_free_form_acceptance_without_grounded_spans_fails_closed():
    ungrounded_accept = {
        "verdict": "ACCEPT",
        "reasoning": "Everything looks good.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [],
    }

    with pytest.raises(LLMError, match="repeatedly returned ungrounded findings"):
        run_separated_readme_review(
            ORG_REPO,
            ORIGINAL,
            CANDIDATE,
            PLAN,
            FACTS,
            blind_client=SequenceClient([ungrounded_accept, ungrounded_accept, ungrounded_accept]),
            factual_client=CapturingClient(_factual_accept("facts and plan agree")),
        )


def test_literal_accepted_fact_false_block_gets_bounded_correction():
    false_missing = {
        "verdict": "BLOCKED_MISSING_EVIDENCE",
        "reasoning": "The Example identity lacks evidence.",
        "failed_criteria": ["factuality"],
        "sections_affected": ["title"],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "factual.false-missing",
                "kind": "factual",
                "criterion": "factuality",
                "section": "title",
                "claim": "The Example identity lacks evidence.",
                "quoted_candidate_span": "Example",
                "disposition": "blocks",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "missing",
                "required_repair": "",
            }
        ],
    }
    factual = SequenceClient([false_missing, _factual_accept("accepted fact is present")])

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=CapturingClient(_blind_accept("visitor-ready")),
        factual_client=factual,
    )

    assert result.verdict == "ACCEPT"
    factual_history = [
        item for item in result.grounding_retry_history if item["role"] == "factual_plan"
    ]
    assert factual_history[0]["valid"] is False
    assert "contradicts accepted facts" in factual_history[0]["errors"][0]
    assert factual_history[1]["validation_result"]["valid"] is True
    assert '"evidence_location": "README.md"' in factual.messages_seen[1][-1]["content"]
