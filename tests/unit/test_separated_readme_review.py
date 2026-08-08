"""Runtime wiring for context-isolated README reviewer roles."""

import json

import pytest

from readme_agent.errors import LLMError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.readme.document_structure import parse_headings
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
    ReviewActorIdentityV1,
)
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


def test_visible_structure_disproves_three_live_reviewer_false_premises() -> None:
    candidate = """# Aspose.Note FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-note.svg)](https://pypi.org/project/aspose-note/)

Repository-specific product summary.

## Navigation

- [At a glance](#at-a-glance)
- [Quick start](#quick-start)

## At a glance

```mermaid
flowchart LR
  subgraph Inputs["Inputs and formats"]
    I1["Microsoft OneNote (.one)"]
  end
  PRODUCT["Aspose.Note FOSS for Python"]
  subgraph Capabilities["Core capabilities"]
    direction TB
    C1["Read documents"]
    C2["Traverse pages"]
    C3["Export PDF"]
  end
  subgraph Outputs["Outputs"]
    O1["Text and PDF"]
  end
  I1 --- PRODUCT
  PRODUCT --- Capabilities
  Capabilities --- Outputs
```

## Quick start

```python
from aspose.note import Document

document = Document("input.one")
```

## Additional examples

<details>
<summary>Show additional examples</summary>

More curated guidance.

</details>
"""
    base = {
        "kind": "quality",
        "criterion": "hierarchy",
        "section": "Header",
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
                "finding_id": "header-spacing",
                "claim": "The H1 is missing the required blank line before badges.",
                "quoted_candidate_span": "# Aspose.Note FOSS for Python",
                "required_repair": "Insert a blank line after the H1.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "mermaid-roles",
                "criterion": "navigation",
                "section": "At a glance",
                "claim": (
                    "The Mermaid diagram is missing Inputs, Product/API, Capabilities, "
                    "and Outputs labels."
                ),
                "quoted_candidate_span": "```mermaid",
                "required_repair": "Add the missing grammar labels.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "quick-start-duplicates",
                "criterion": "example_presentation",
                "section": "Quick start",
                "claim": "Quick start contains two separate example blocks.",
                "quoted_candidate_span": "## Quick start",
                "required_repair": "Keep one Quick start example.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "quick-start-complexity",
                "criterion": "example_presentation",
                "section": "Quick start",
                "claim": "The Quick start example should be simpler and more direct.",
                "quoted_candidate_span": "## Quick start",
                "required_repair": (
                    "Replace the 'Quick start' minimal example with a simpler, more direct example."
                ),
            }
        ),
    ]

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert len(result.errors) == 4
    assert any("header-spacing premise" in error for error in result.errors)
    assert any("Mermaid-grammar premise" in error for error in result.errors)
    assert any("Quick-start duplication premise" in error for error in result.errors)
    assert any("Quick-start complexity premise" in error for error in result.errors)


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


def test_blind_grounding_uses_visible_counts_and_scope_placement() -> None:
    badges = (
        "[![PyPI](https://img.shields.io/pypi/v/example.svg)](https://pypi.org/) "
        "[![Python](https://img.shields.io/pypi/pyversions/example.svg)](https://pypi.org/) "
        "[![MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE) "
        "[![Contributors](https://img.shields.io/github/contributors/example/repo.svg)]"
        "(https://github.com/example/repo/graphs/contributors)"
    )
    candidate = (
        f"# Example FOSS for Python\n\n{badges}\n\n"
        "Example FOSS for Python reads example files.\n\n"
        "## At a glance\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        '  subgraph Inputs["Inputs and formats"]\n'
        '    input_1["Example files"]\n'
        "  end\n"
        '  product["Example FOSS for Python"]\n'
        '  subgraph Capabilities["Core capabilities"]\n'
        '    capability_1["Read"]\n'
        '    capability_2["Inspect"]\n'
        '    capability_3["Export"]\n'
        "  end\n"
        '  subgraph Outputs["Outputs and accessible content"]\n'
        '    output_1["Document model"]\n'
        "  end\n"
        "  input_1 --- product\n"
        "  product --- capability_1\n"
        "  capability_1 --- output_1\n"
        "```\n\n"
        "## Quick start\n\n"
        "```python\nfrom example import Document\n\nprint(Document('input.example'))\n```\n\n"
        "## Scope and limitations\n\n"
        "[Example FOSS for Python](https://products.aspose.org/example/python/) and "
        "[Example for Python Enterprise Edition](https://products.aspose.com/example/python/) "
        "are separate products. This README documents the FOSS implementation.\n"
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
                "finding_id": "badge-count",
                "criterion": "markdown_integrity",
                "section": "Header",
                "claim": (
                    "The contributors badge exceeds the allowed badge_rows=1 and violates "
                    "the configured badge standard."
                ),
                "quoted_candidate_span": badges,
                "required_repair": "Remove the contributors badge.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "fence-count",
                "criterion": "markdown_integrity",
                "section": "Quick start",
                "claim": (
                    "The Quick start contains two separate fenced code blocks, exceeding the "
                    "maximum_fenced_blocks=1."
                ),
                "quoted_candidate_span": "```python",
                "required_repair": "Consolidate the Quick start examples into one fence.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "enterprise-placement",
                "criterion": "promotional_balance",
                "section": "Scope and limitations",
                "claim": (
                    "The Enterprise Edition relationship should appear naturally below the "
                    "opening value proposition."
                ),
                "quoted_candidate_span": (
                    "[Example for Python Enterprise Edition]"
                    "(https://products.aspose.com/example/python/)"
                ),
                "required_repair": "Move it after the opening value proposition.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "badge-title",
                "criterion": "markdown_integrity",
                "section": "Header",
                "claim": "The PyPI badge has a non-empty title attribute.",
                "quoted_candidate_span": badges,
                "required_repair": "Remove the non-empty title attribute.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "example-line-count",
                "criterion": "example_presentation",
                "section": "Quick start",
                "claim": "The Quick start exceeds the maximum of 12 nonblank code lines.",
                "quoted_candidate_span": "```python",
                "required_repair": "Reduce it to 12 nonblank code lines or fewer.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "enterprise-term",
                "criterion": "internal_terminology",
                "section": "Scope and limitations",
                "claim": "The section is missing the required Enterprise Edition term.",
                "quoted_candidate_span": (
                    "[Example for Python Enterprise Edition]"
                    "(https://products.aspose.com/example/python/)"
                ),
                "required_repair": "Add the Enterprise Edition term.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "mermaid-direction",
                "criterion": "hierarchy",
                "section": "At a glance",
                "claim": "The Mermaid diagram uses a directional workflow.",
                "quoted_candidate_span": "```mermaid",
                "required_repair": "Replace directional Mermaid with non-directional grammar.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **base,
                "finding_id": "mermaid-layout-direction",
                "criterion": "hierarchy",
                "section": "At a glance",
                "claim": (
                    "The Mermaid diagram uses directional workflow language ('flowchart LR') "
                    "even though the map should not imply a sequence."
                ),
                "quoted_candidate_span": "flowchart LR",
                "required_repair": "Replace flowchart LR with non-directional graph grammar.",
            }
        ),
    ]

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("badge-row premise" in error for error in result.errors)
    assert any("Quick-start duplication premise" in error for error in result.errors)
    assert any("placement contradicts configured section" in error for error in result.errors)
    assert any("badge-title premise" in error for error in result.errors)
    assert any("Quick-start line-count premise" in error for error in result.errors)
    assert any("Enterprise Edition term premise" in error for error in result.errors)
    assert any("Mermaid-direction premise" in error for error in result.errors)
    assert any(
        error.startswith("mermaid-layout-direction:Mermaid-direction premise")
        for error in result.errors
    )


def test_blind_reviewer_cannot_confuse_mermaid_node_id_with_visible_product_label() -> None:
    candidate = """# Aspose.Page FOSS for Python

## At a glance

```mermaid
flowchart LR
  subgraph Inputs["Inputs and formats"]
    input_1["PS/EPS input"]
  end
  product["Aspose.Page FOSS for Python"]
  subgraph Capabilities["Core capabilities"]
    capability_1["PS/EPS to PDF conversion"]
  end
  subgraph Outputs["Outputs and accessible content"]
    output_1["PDF output"]
  end
  input_1 --- product
  product --- capability_1
  product --- output_1
```
"""
    finding = GroundedReviewFindingV1.model_validate(
        {
            "finding_id": "mermaid-product-node-id",
            "kind": "quality",
            "criterion": "clarity",
            "section": "At a glance",
            "claim": (
                "The Mermaid diagram uses generic labels like 'product' instead of the "
                "product name."
            ),
            "quoted_candidate_span": "```mermaid",
            "disposition": "requires_repair",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "not_applicable",
            "required_repair": "Replace the generic product label with the product name.",
        }
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert result.valid is False
    assert result.errors == [
        "mermaid-product-node-id:Mermaid-product-label premise contradicts visible candidate label"
    ]


def test_blind_reviewer_cannot_invert_configured_note_presentation_standards() -> None:
    mermaid = """```mermaid
flowchart LR
  subgraph Inputs["Inputs and formats"]
    input_1["Microsoft OneNote (.one) files"]
    input_2["Binary streams"]
  end
  product["Aspose.Note FOSS for Python"]
  subgraph Capabilities["Core capabilities"]
    capability_1["Document traversal"]
    capability_2["PDF export"]
    capability_3["Image extraction"]
  end
  subgraph Outputs["Outputs and accessible content"]
    output_1["Document object model"]
    output_2["PDF documents"]
  end
  input_1 --- product
  product --- capability_1
  product --- output_1
```"""
    details = "<details>\n<summary>Show additional examples</summary>\n\nExample.\n</details>"
    relationship = (
        "[Aspose.Note FOSS for Python](https://products.aspose.org/note/python/) and "
        "[Aspose.Note for Python Enterprise Edition](https://products.aspose.com/note/) "
        "are separate products. This README documents the FOSS implementation; do not "
        "assume API or feature parity beyond verified behavior."
    )
    candidate = (
        "# Aspose.Note FOSS for Python\n\n"
        f"## At a glance\n\n{mermaid}\n\n"
        f"## Additional examples\n\n{details}\n\n"
        f"## Scope and limitations\n\n{relationship}\n"
    )
    common = {
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
                **common,
                "finding_id": "collapsed-examples",
                "criterion": "example_presentation",
                "section": "Additional examples",
                "claim": "Secondary examples are collapsed, violating the configured rule.",
                "quoted_candidate_span": details,
                "required_repair": "Move secondary examples out of the details block.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **common,
                "finding_id": "directional-mermaid",
                "criterion": "markdown_integrity",
                "section": "At a glance",
                "claim": "The Mermaid diagram uses directional arrows.",
                "quoted_candidate_span": mermaid,
                "required_repair": "Replace directional arrows with --- connectors.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **common,
                "finding_id": "thin-mermaid",
                "criterion": "product_specificity",
                "section": "At a glance",
                "claim": "The Mermaid diagram does not show three capabilities or input/output.",
                "quoted_candidate_span": mermaid,
                "required_repair": "Add three capabilities and an input/output pair.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **common,
                "finding_id": "promotional-scope",
                "criterion": "promotional_balance",
                "section": "Scope and limitations",
                "claim": (
                    "The Enterprise Edition relationship is a promotional link rather than "
                    "scope context."
                ),
                "quoted_candidate_span": relationship,
                "required_repair": "Rewrite it as compatibility context rather than promotion.",
            }
        ),
    ]

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert result.valid is False
    assert result.errors == [
        "collapsed-examples:collapsed-example premise contradicts configured presentation",
        "directional-mermaid:Mermaid-direction premise contradicts parsed connectors",
        "thin-mermaid:Mermaid-role-count premise contradicts parsed candidate",
        "promotional-scope:Enterprise-scope premise contradicts configured candidate context",
    ]


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


def test_live_header_and_navigation_ceiling_phrases_are_disproven() -> None:
    badge = "[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)"
    navigation = (
        "- [At a glance](#at-a-glance)\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [Quick start](#quick-start)\n"
        "- [Installation](#installation)\n"
        "- [Development](#development)\n"
        "- [Scope and limitations](#scope-and-limitations)\n"
        "- [License](#license)"
    )
    candidate = (
        f"# Widget\n\n{badge}\n\n## Navigation\n\n{navigation}\n\n## At a glance\n\nSummary.\n"
    )
    common = {
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
                **common,
                "finding_id": "header-live-phrase",
                "criterion": "hierarchy",
                "section": "Header",
                "claim": "Badge row must directly follow H1 title without blank line.",
                "quoted_candidate_span": "# Widget",
                "required_repair": (
                    "Remove the blank line between the H1 title and the badge row."
                ),
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **common,
                "finding_id": "navigation-live-phrase",
                "criterion": "navigation",
                "section": "Navigation",
                "claim": "Navigation section includes non-required labels.",
                "quoted_candidate_span": navigation,
                "required_repair": (
                    "Remove non-required labels from the Navigation section to ensure only "
                    "required labels are present."
                ),
            }
        ),
    ]

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert result.valid is False
    assert any("badge-spacing premise" in error for error in result.errors)
    assert any("navigation prefix-only premise" in error for error in result.errors)


def test_qwen_mechanical_count_and_link_false_premises_are_disproven() -> None:
    badges = " ".join(
        f"[![{label}](https://img.shields.io/badge/{label}-ok-blue)](https://example.test/{label})"
        for label in ("package", "platform", "license", "contributors")
    )
    example = "```python\nprint('ready')\n```"
    relationship = (
        "[Widget FOSS](https://products.aspose.org/widget/) and "
        "[Widget Enterprise Edition](https://products.aspose.com/widget/) are separate products."
    )
    candidate = (
        f"# Widget\n\n{badges}\n\n## Quick start\n\n{example}\n\n"
        f"## Scope and limitations\n\n{relationship}\n"
    )
    common = {
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
                **common,
                "finding_id": "badge-count-live",
                "criterion": "navigation",
                "section": "Header",
                "claim": (
                    "Badge row contains four badges, exceeding the configured maximum of one "
                    "badge row with allowed kinds."
                ),
                "quoted_candidate_span": badges,
                "required_repair": "Reduce the badge row to one badge.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **common,
                "finding_id": "fence-count-live",
                "criterion": "example_presentation",
                "section": "Quick start",
                "claim": (
                    "Quick start section contains two fenced code blocks, exceeding the maximum "
                    "of one."
                ),
                "quoted_candidate_span": example,
                "required_repair": "Consolidate Quick start to one fenced code block.",
            }
        ),
        GroundedReviewFindingV1.model_validate(
            {
                **common,
                "finding_id": "bare-link-live",
                "criterion": "promotional_balance",
                "section": "Scope and limitations",
                "claim": "Enterprise Edition link is presented as a bare URL.",
                "quoted_candidate_span": relationship,
                "required_repair": "Use a descriptive Markdown link label.",
            }
        ),
    ]

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert result.valid is False
    assert any("badge-row premise" in error for error in result.errors)
    assert any("Quick-start fence-count premise" in error for error in result.errors)
    assert any("bare-URL premise" in error for error in result.errors)


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
    assert any("link-budget premise" in error for error in history[0]["pre_normalization_errors"])


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


def test_blind_role_canonicalizes_only_empty_shared_schema_factual_placeholders() -> None:
    parsed = _blind_accept("The opening is visibly clear.")
    finding = parsed["findings"][0]
    finding.update(
        {
            "fact_id": "",
            "evidence_excerpt": "   ",
            "evidence_location": "",
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "",
        }
    )

    normalized = normalize_redundant_role_fields("blind_quality", parsed)
    result = BlindQualityReviewResultV1.model_validate(normalized)

    assert result.findings[0].claim == "The opening is clear."
    assert result.findings[0].quoted_candidate_span == "Specific, useful candidate."
    assert result.findings[0].fact_id is None
    assert result.findings[0].evidence_excerpt is None
    assert result.findings[0].evidence_location is None
    assert result.findings[0].expected_polarity is None
    assert result.findings[0].observed_polarity is None
    assert result.findings[0].polarity_result == "not_applicable"


def test_blind_role_does_not_erase_substantive_cross_role_factual_fields() -> None:
    parsed = _blind_accept("The opening is visibly clear.")
    parsed["findings"][0].update(
        {
            "fact_id": "out-of-role-fact",
            "evidence_excerpt": "out-of-role evidence",
            "evidence_location": "README.md",
            "expected_polarity": "positive_implementation",
            "observed_polarity": "positive_implementation",
            "polarity_result": "supports",
        }
    )

    normalized = normalize_redundant_role_fields("blind_quality", parsed)

    with pytest.raises(ValueError, match="quality finding cannot carry factual evidence fields"):
        BlindQualityReviewResultV1.model_validate(normalized)


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


def test_factual_accept_clears_stale_redundant_failure_summaries() -> None:
    parsed = _factual_accept("The accepted fact supports the candidate.")
    parsed["failed_criteria"] = ["stale-model-summary"]
    parsed["sections_affected"] = ["stale-model-section"]
    parsed["required_repair"] = "This must not survive an ACCEPT verdict."

    normalized = normalize_redundant_role_fields("factual_plan", parsed)
    result = FactualPlanReviewResultV1.model_validate(normalized)

    assert result.verdict == "ACCEPT"
    assert result.failed_criteria == []
    assert result.sections_affected == []
    assert result.required_repair == ""


def test_factual_accept_cannot_launder_a_repair_finding() -> None:
    parsed = _factual_accept("The candidate needs repair despite the stated verdict.")
    parsed["findings"][0]["disposition"] = "requires_repair"
    parsed["findings"][0]["required_repair"] = "Correct the unsupported claim."

    normalized = normalize_redundant_role_fields("factual_plan", parsed)

    with pytest.raises(ValueError, match="requires grounded supporting findings"):
        FactualPlanReviewResultV1.model_validate(normalized)


def test_factual_block_derives_redundant_summary_from_blocking_findings() -> None:
    parsed = _factual_accept("The candidate claim contradicts repository evidence.")
    parsed["verdict"] = "BLOCKED_FACT_CONFLICT"
    parsed["failed_criteria"] = ["wrong-summary"]
    parsed["sections_affected"] = ["wrong-section"]
    parsed["required_repair"] = "A blocked verdict cannot prescribe prose repair."
    finding = parsed["findings"][0]
    finding["disposition"] = "blocks"
    finding["criterion"] = "factuality"
    finding["section"] = "Installation"
    finding["polarity_result"] = "contradicts"

    normalized = normalize_redundant_role_fields("factual_plan", parsed)
    result = FactualPlanReviewResultV1.model_validate(normalized)

    assert result.failed_criteria == ["factuality"]
    assert result.sections_affected == ["Installation"]
    assert result.required_repair == ""


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
    assert ORIGINAL not in blind_context
    assert "Complete candidate README block catalog" in blind_context
    assert "candidate.anchor." in blind_context
    assert "fact-1" not in blind_context
    assert "readme.overview" not in blind_context
    assert ORIGINAL not in factual_context
    assert "fact-1" in factual_context
    assert "readme.overview" in factual_context


def test_default_merged_client_makes_one_call_and_binds_two_grounded_facets():
    merged = SequenceClient(
        [{"quality": _blind_accept("visitor-ready"), "factual": _factual_accept("grounded")}]
    )

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        merged_client=merged,
    )

    assert result.verdict == "ACCEPT"
    assert len(merged.messages_seen) == 1
    assert result.combined_review.identity_separation_valid
    receipt = result.combined_review.merged_call_receipt
    assert receipt is not None
    assert receipt.actor_id == "llm-route:merged-readme-review"
    assert result.blind_quality_review.identity.actor_id == receipt.actor_id
    assert result.factual_plan_review.identity.actor_id == receipt.actor_id
    assert result.blind_quality_review.identity.prompt_id == "merged_readme_review"
    assert result.factual_plan_review.identity.prompt_id == "merged_readme_review"
    serialized = "\n".join(message["content"] for message in merged.messages_seen[0])
    assert "Complete candidate README block catalog" in serialized
    assert "fact-1" in serialized
    assert ORIGINAL not in serialized


def test_merged_cross_role_quality_leakage_uses_one_isolated_blind_fallback():
    leaked_quality = _blind_accept("visitor-ready")
    leaked_quality["findings"][0].update(
        {
            "fact_id": "fact-1",
            "evidence_excerpt": "Example",
            "evidence_location": "README.md",
            "expected_polarity": "positive_implementation",
            "observed_polarity": "positive_implementation",
            "polarity_result": "supports",
        }
    )
    merged = SequenceClient([{"quality": leaked_quality, "factual": _factual_accept("grounded")}])
    fallback = SequenceClient([_blind_accept("visitor-ready after isolated retry")])

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        merged_client=merged,
        blind_fallback_client=fallback,
    )

    assert result.verdict == "ACCEPT"
    assert len(merged.messages_seen) == 1
    assert len(fallback.messages_seen) == 1
    assert result.combined_review.merged_call_receipt is None
    assert result.blind_quality_review.identity.prompt_id == "blind_readme_quality_review"
    assert result.factual_plan_review.identity.prompt_id == "merged_readme_review"
    assert result.combined_review.identity_separation_valid
    fallback_context = "\n".join(message["content"] for message in fallback.messages_seen[0])
    assert "fact-1" not in fallback_context
    assert "readme.overview" not in fallback_context
    event = result.grounding_retry_history[0]
    assert event["fallback"] == "isolated_blind_quality"
    assert event["trigger"] == "merged_quality_contract_failure"
    assert event["merged_raw_output_sha256"]


def test_merged_false_missing_premise_fails_closed_without_repeating_call():
    false_missing = _factual_accept("The accepted identity is missing evidence.")
    false_missing["verdict"] = "BLOCKED_MISSING_EVIDENCE"
    false_missing["findings"][0].update(
        {
            "finding_id": "factual.false-missing",
            "disposition": "blocks",
            "fact_id": None,
            "evidence_excerpt": None,
            "evidence_location": None,
            "expected_polarity": None,
            "observed_polarity": None,
            "polarity_result": "missing",
        }
    )
    merged = SequenceClient([{"quality": _blind_accept("visitor-ready"), "factual": false_missing}])

    with pytest.raises(LLMError, match="repeatedly returned ungrounded findings"):
        run_separated_readme_review(
            ORG_REPO,
            ORIGINAL,
            CANDIDATE,
            PLAN,
            FACTS,
            merged_client=merged,
        )

    assert len(merged.messages_seen) == 1


def test_merged_reviewer_cannot_self_approve_author_output():
    merged = SequenceClient(
        [{"quality": _blind_accept("visitor-ready"), "factual": _factual_accept("grounded")}]
    )
    author = ReviewActorIdentityV1(
        actor_id="llm-route:merged-readme-review",
        role="author",
        prompt_id="plan_readme_composition",
        prompt_sha256="0" * 64,
    )

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        merged_client=merged,
        author_identity=author,
    )

    assert result.verdict == "SYSTEM_FAILURE"
    assert not result.combined_review.identity_separation_valid


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


def test_wrong_quick_start_metric_retries_once_and_preserves_attempt_history() -> None:
    quote = "```python\nfirst()\n```\n\n```python\nsecond()\n```"
    candidate = f"# Product\n\n## Quick start\n\n{quote}\n"
    common = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "Quick start has two primary examples.",
        "failed_criteria": ["example_presentation"],
        "sections_affected": ["Quick start"],
        "required_repair": "Consolidate Quick start to one fenced code block.",
    }
    finding = {
        "finding_id": "quick-start-fences",
        "kind": "quality",
        "criterion": "example_presentation",
        "section": "Quick start",
        "claim": "Quick start contains two fenced code blocks, exceeding the configured maximum.",
        "quoted_candidate_span": quote,
        "disposition": "requires_repair",
        "fact_id": None,
        "evidence_excerpt": None,
        "evidence_location": None,
        "expected_polarity": None,
        "observed_polarity": None,
        "polarity_result": "not_applicable",
        "required_repair": "Consolidate Quick start to one fenced code block.",
    }
    invalid = {
        **common,
        "findings": [
            {
                **finding,
                "mechanical_check_id": "quick_start.max_nonblank_code_lines",
                "reported_observed_value": 1,
            }
        ],
    }
    corrected = {
        **common,
        "findings": [
            {
                **finding,
                "mechanical_check_id": "quick_start.fenced_blocks",
                "reported_observed_value": 2,
            }
        ],
    }
    client = SequenceClient([invalid, corrected])

    result, history, grounding = run_grounded_role(
        role="blind_quality",
        prompt_id="blind_readme_quality_review",
        client=client,
        messages=[],
        candidate_text=candidate,
        product_facts=None,
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert grounding.valid
    assert len(client.messages_seen) == 2
    assert len(history) == 2
    assert history[0]["valid"] is False
    assert history[0]["errors"] == [
        "quick-start-fences:mechanical premise cites "
        "quick_start.max_nonblank_code_lines instead of quick_start.fenced_blocks"
    ]
    assert history[1]["valid"] is True


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


def test_reviewer_standard_binds_visible_grounding_and_both_role_prompts(monkeypatch):
    from readme_agent.llm import prompt_registry, verification_prompts

    standard = separated_reviewer_standard_hash()

    assert len(standard) == 64
    assert standard != prompt_registry.prompt_hash("independent_readme_review")
    monkeypatch.setattr(
        verification_prompts,
        "BLIND_GROUNDING_CONTRACT_VERSION",
        "different-visible-grounding-contract",
    )
    assert separated_reviewer_standard_hash() != standard


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


def test_factual_finding_uses_stable_candidate_anchor_instead_of_freehand_quote() -> None:
    anchor = next(
        item for item in build_candidate_review_anchors(CANDIDATE) if item.text == "# Example"
    )
    parsed = _factual_accept("The product identity is supported.")
    parsed["findings"][0]["quoted_candidate_span"] = "Example product heading"
    parsed["findings"][0]["candidate_anchor_id"] = anchor.anchor_id
    parsed["findings"][0]["evidence_excerpt"] = "Approximate evidence"
    parsed["findings"][0]["evidence_location"] = "invented://location"
    parsed["findings"][0]["expected_polarity"] = "explicit_constraint"
    parsed["findings"][0]["observed_polarity"] = "ambiguous_occurrence"
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="factual_plan",
        prompt_id="factual_readme_plan_review",
        client=client,
        messages=[],
        candidate_text=CANDIDATE,
        product_facts=FACTS,
    )

    assert result.findings[0].candidate_anchor_id == anchor.anchor_id
    assert result.findings[0].quoted_candidate_span == "# Example"
    assert result.findings[0].evidence_excerpt == "Example"
    assert result.findings[0].evidence_location == "README.md"
    assert result.findings[0].expected_polarity == "positive_implementation"
    assert result.findings[0].observed_polarity == "positive_implementation"
    assert grounding.valid is True
    assert history[0]["valid"] is True
    assert history[0]["reconciled_factual_polarity_ids"] == ["factual.identity-supported"]


def test_duplicate_model_finding_ids_are_made_unique_before_grounding() -> None:
    parsed = _factual_accept("Two premises cite the same accepted fact.")
    parsed["findings"].append(dict(parsed["findings"][0]))
    client = SequenceClient([parsed])

    result, history, grounding = run_grounded_role(
        role="factual_plan",
        prompt_id="factual_readme_plan_review",
        client=client,
        messages=[],
        candidate_text=CANDIDATE,
        product_facts=FACTS,
    )

    assert [finding.finding_id for finding in result.findings] == [
        "factual.identity-supported",
        "factual.identity-supported.2",
    ]
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
    assert factual_history[0]["context_mode"] == "full_review_packet"
    assert factual_history[1]["context_mode"] == "compact_grounding_retry"
    assert factual_history[1]["input_character_count"] < factual_history[0]["input_character_count"]
    assert factual_history[1]["validation_result"]["valid"] is True
    assert '"evidence_location": "README.md"' in factual.messages_seen[1][-1]["content"]


def test_page_reviewer_cannot_remove_real_h2_sections_as_non_required() -> None:
    navigation = (
        "- [At a glance](#at-a-glance)\n"
        "- [Example Results](#example-results)\n"
        "- [MCP Server](#mcp-server)\n"
        "- [Build and Test (Developers)](#build-and-test-developers)\n"
        "- [License](#license)\n"
        "- [Scope and limitations](#scope-and-limitations)"
    )
    candidate = (
        f"# Aspose.Page FOSS for Python\n\n## Navigation\n\n{navigation}\n\n"
        "## At a glance\n\nSummary.\n\n## License\n\nMIT.\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="page-navigation-floor",
        kind="quality",
        criterion="hierarchy",
        section="Navigation",
        claim="Navigation lists non-required H2 sections that violate the required sequence.",
        quoted_candidate_span=navigation,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Remove non-required H2 sections from Navigation.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert result.errors == ["page-navigation-floor:navigation prefix-only premise is unconfigured"]


def test_page_reviewer_cannot_invent_duplicate_license_from_one_heading() -> None:
    candidate = "# Product\n\n## License\n\nMIT.\n"
    finding = GroundedReviewFindingV1(
        finding_id="page-license-duplicate",
        kind="quality",
        criterion="visible_duplication",
        section="License",
        claim="License section appears twice.",
        quoted_candidate_span="## License",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Remove the duplicate License section.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("heading-only quote" in error for error in result.errors)
    assert any(
        "lacks required typed check document.duplicate_h2_headings" in error
        for error in result.errors
    )


def test_page_reviewer_cannot_move_enterprise_term_already_in_scope() -> None:
    candidate = (
        "# Product\n\n## License\n\nMIT.\n\n## Scope and limitations\n\n"
        "[Product Enterprise Edition](https://products.aspose.com/page/python/) "
        "is a separate product.\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="page-enterprise-placement",
        kind="quality",
        criterion="internal_terminology",
        section="Scope and limitations",
        claim=(
            "The section contains Enterprise Edition language but it must be placed "
            "below the fold and not in the License section."
        ),
        quoted_candidate_span="## Scope and limitations",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair=(
            "Ensure Enterprise Edition language is placed below the fold and not in "
            "the License section."
        ),
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("heading-only quote" in error for error in result.errors)
    assert any("already satisfies contract" in error for error in result.errors)


def test_pdf_reviewer_cannot_claim_visible_enterprise_relationship_is_missing() -> None:
    candidate = (
        "# Aspose.PDF FOSS for Python\n\n## Scope and limitations\n\n"
        "- OCR and layout reflow are not implemented.\n\n"
        "[Aspose.PDF FOSS for Python](https://products.aspose.org/pdf/) and "
        "[Aspose.PDF for Python Enterprise Edition](https://products.aspose.com/pdf/) "
        "are separate products. This README documents the FOSS implementation.\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="pdf-enterprise-context",
        kind="quality",
        criterion="template_genericity",
        section="Scope and limitations",
        claim=(
            "The 'Scope and limitations' section does not explicitly contain the required term "
            "'Enterprise Edition'."
        ),
        quoted_candidate_span="## Scope and limitations",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair=(
            "Update the '## Scope and limitations' section to include the phrase "
            "'Enterprise Edition' explicitly, as required by the contract."
        ),
        mechanical_check_id="document.required_h2_prefix",
        reported_observed_value=False,
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("heading-only quote" in error for error in result.errors)
    assert any(
        "Enterprise Edition term premise contradicts candidate" in error for error in result.errors
    )


def test_quality_reviewer_cannot_launder_prose_judgment_through_unrelated_check() -> None:
    scope = "This README documents the verified FOSS implementation."
    candidate = f"# Product\n\n## Scope and limitations\n\n{scope}\n"
    finding = GroundedReviewFindingV1(
        finding_id="scope-clarity",
        kind="quality",
        criterion="clarity",
        section="Scope and limitations",
        claim="The scope explanation is unclear.",
        quoted_candidate_span=scope,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Clarify the scope explanation.",
        mechanical_check_id="document.required_h2_prefix",
        reported_observed_value=False,
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert result.errors == [
        "scope-clarity:mechanical premise cites unrelated check document.required_h2_prefix"
    ]


def test_pdf_reviewer_cannot_remove_required_mit_benefits_as_promotion() -> None:
    license_prose = (
        "This project is available under the [MIT License](LICENSE). It permits use, "
        "modification, distribution, and commercial use when the license and copyright "
        "notice are retained."
    )
    candidate = f"# Aspose.PDF FOSS for Python\n\n## License\n\n{license_prose}\n"
    finding = GroundedReviewFindingV1(
        finding_id="pdf-license-benefits",
        kind="quality",
        criterion="promotional_balance",
        section="License",
        claim="License section contains promotional language beyond a simple license reference.",
        quoted_candidate_span=license_prose,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair=(
            "Trim the License section to a single sentence referencing the MIT License without "
            "promotional language."
        ),
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("license-benefits repair" in error for error in result.errors)


def test_pdf_reviewer_cannot_move_enterprise_text_already_in_scope_section() -> None:
    relationship = (
        "[Aspose.PDF FOSS for Python](https://products.aspose.org/pdf/) and "
        "[Aspose.PDF for Python Enterprise Edition](https://products.aspose.com/pdf/) "
        "are separate products."
    )
    candidate = (
        "# Aspose.PDF FOSS for Python\n\n## Scope and limitations\n\n"
        "- OCR and layout reflow are not implemented.\n\n"
        f"{relationship}\n\n## License\n\n[MIT License](LICENSE)\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="pdf-enterprise-section",
        kind="quality",
        criterion="hierarchy",
        section="Scope and limitations",
        claim=(
            "Enterprise Edition relationship language is misplaced in the License section "
            "instead of the Scope and limitations section."
        ),
        quoted_candidate_span=relationship,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair=(
            "Move the Enterprise Edition relationship language from the License section to the "
            "Scope and limitations section."
        ),
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=build_presentation_visitor_contract(),
    )

    assert not result.valid
    assert any("claimed source section" in error for error in result.errors)


def test_pdf_reviewer_cannot_demand_withheld_sections_or_remove_applicable_navigation() -> None:
    navigation = (
        "- [At a glance](#at-a-glance)\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [Requirements](#requirements)\n"
        "- [Feature Boundaries](#feature-boundaries)\n"
        "- [License](#license)\n"
        "- [Scope and limitations](#scope-and-limitations)"
    )
    candidate = (
        f"# Aspose.PDF FOSS for Python\n\n## Navigation\n\n{navigation}\n\n"
        "## At a glance\n\nSummary.\n\n## Key capabilities\n\n- Create PDFs.\n\n"
        "## Requirements\n\nPython 3.11+.\n\n## Feature Boundaries\n\nBounded.\n\n"
        "## License\n\nMIT.\n\n## Scope and limitations\n\nOCR is unavailable.\n"
    )
    finding = GroundedReviewFindingV1(
        finding_id="pdf-navigation-applicability",
        kind="quality",
        criterion="navigation",
        section="Navigation",
        claim=(
            "Navigation must list the required labels 'At a glance', 'Key capabilities', "
            "'Installation', 'Quick start', 'Scope and limitations', 'License'; the candidate "
            "omits 'Installation' and 'Quick start'."
        ),
        quoted_candidate_span=navigation,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair=(
            "Add 'Installation' and 'Quick start' to the Navigation list and remove "
            "'Requirements' and 'Feature Boundaries' as they are not required labels."
        ),
    )
    visitor_contract = build_presentation_visitor_contract(
        applicable_h2_headings=[
            heading.title for heading in parse_headings(candidate) if heading.level == 2
        ]
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=visitor_contract,
    )

    assert not result.valid
    assert any("required-navigation premise" in error for error in result.errors)
    assert any("navigation removal" in error for error in result.errors)
