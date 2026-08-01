"""Tests for parser-owned blind-review observations."""

from readme_agent.specialists.review_finding_grounding import (
    GroundedReviewFindingV1,
    validate_review_findings,
)
from readme_agent.specialists.review_mechanical_observations import (
    build_candidate_mechanical_observations,
)


def _visitor_contract() -> dict:
    return {
        "configured_standards": [
            {
                "standard_id": "readme.header",
                "parameters": {
                    "brand_contract_version": "v1",
                    "required_h2_prefix": ["Quick start", "Additional examples"],
                },
            },
            {
                "standard_id": "readme.badges",
                "parameters": {"badge_rows": 1},
            },
            {
                "standard_id": "readme.primary_example",
                "parameters": {
                    "maximum_fenced_blocks": 1,
                    "maximum_nonblank_code_lines": 8,
                },
            },
        ]
    }


def _candidate() -> str:
    return """# Product

[![Package](https://img.shields.io/badge/package-ready-blue)](https://example.test)

## Quick start

```python
from package import Product

print(Product())
```

## Additional examples

```python
print("outside Quick start")
```
"""


def test_candidate_mechanical_observations_are_section_scoped() -> None:
    observations = {
        item.check_id: item
        for item in build_candidate_mechanical_observations(
            _candidate(),
            _visitor_contract(),
        )
    }

    assert observations["document.h1_blocks"].observed_value == 1
    assert observations["document.duplicate_h2_headings"].observed_value == 0
    assert observations["document.required_h2_prefix"].observed_value is True
    assert observations["header.badge_rows"].observed_value == 1
    assert observations["quick_start.fenced_blocks"].observed_value == 1
    assert observations["quick_start.max_nonblank_code_lines"].observed_value == 2
    assert all(item.compliant for item in observations.values())


def test_mechanical_repair_finding_cannot_reinterpret_compliant_parser_value() -> None:
    quote = """```python
from package import Product

print(Product())
```"""
    finding = GroundedReviewFindingV1(
        finding_id="example-presentation-1",
        kind="quality",
        criterion="example_presentation",
        section="Quick start",
        claim="Two fenced code blocks in Quick start exceed the configured maximum.",
        quoted_candidate_span=quote,
        candidate_anchor_id=None,
        disposition="requires_repair",
        polarity_result="not_applicable",
        mechanical_check_id="quick_start.fenced_blocks",
        reported_observed_value=2,
        required_repair="Consolidate the two Quick start code blocks.",
    )

    result = validate_review_findings(
        candidate_text=_candidate(),
        product_facts=None,
        findings=[finding],
        visitor_contract=_visitor_contract(),
    )

    assert not result.valid
    assert any("contradicts parser value 1" in error for error in result.errors)


def test_mechanical_repair_finding_cannot_omit_typed_check() -> None:
    quote = """```python
from package import Product

print(Product())
```"""
    finding = GroundedReviewFindingV1(
        finding_id="example-presentation-1",
        kind="quality",
        criterion="example_presentation",
        section="Quick start",
        claim="Two fenced code blocks in Quick start exceed the configured maximum.",
        quoted_candidate_span=quote,
        candidate_anchor_id=None,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Consolidate the two Quick start code blocks.",
    )

    result = validate_review_findings(
        candidate_text=_candidate(),
        product_facts=None,
        findings=[finding],
        visitor_contract=_visitor_contract(),
    )

    assert not result.valid
    assert any("lacks required typed check" in error for error in result.errors)


def test_duplicate_h2_claim_requires_and_obeys_parser_count() -> None:
    finding = GroundedReviewFindingV1(
        finding_id="license-duplicate",
        kind="quality",
        criterion="visible_duplication",
        section="License",
        claim="The License section appears twice.",
        quoted_candidate_span="## Additional examples",
        candidate_anchor_id=None,
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Remove the duplicate License section.",
    )

    result = validate_review_findings(
        candidate_text=_candidate(),
        product_facts=None,
        findings=[finding],
        visitor_contract=_visitor_contract(),
    )

    assert not result.valid
    assert any(
        "lacks required typed check document.duplicate_h2_headings" in error
        for error in result.errors
    )


def test_quality_quote_must_belong_to_its_named_visible_section() -> None:
    candidate = """# Product

## Why Product

- Create documents

## Key capabilities

- Read documents
"""
    finding = GroundedReviewFindingV1(
        finding_id="misbound-capabilities",
        kind="quality",
        criterion="visible_duplication",
        section="Key capabilities",
        claim="Why Product duplicates Key capabilities.",
        quoted_candidate_span="- Create documents",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Merge the Why Product content into Key capabilities.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=_visitor_contract(),
    )

    assert not result.valid
    assert any("outside the named candidate section" in error for error in result.errors)


def test_heading_only_quote_cannot_prove_another_sections_order() -> None:
    candidate = """# Product

## Navigation

- [Why Product](#why-product)

## Why Product

Details.
"""
    finding = GroundedReviewFindingV1(
        finding_id="misbound-order",
        kind="quality",
        criterion="hierarchy",
        section="Navigation",
        claim="Why Product appears before Installation and violates the section order.",
        quoted_candidate_span="## Navigation",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Remove the Why Product section.",
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=_visitor_contract(),
    )

    assert not result.valid
    assert any("heading-only quote" in error for error in result.errors)


def test_note_reviewer_cannot_invent_navigation_prefix_failure() -> None:
    candidate = """# Aspose.Note FOSS for Python

## Navigation

- [At a glance](#at-a-glance)

## At a glance

```mermaid
flowchart LR
  navigation["Navigation"]
```

## Key capabilities

- Read OneNote files.
"""
    contract = _visitor_contract()
    contract["configured_standards"][0]["parameters"]["required_h2_prefix"] = [
        "Navigation",
        "At a glance",
        "Key capabilities",
    ]
    finding = GroundedReviewFindingV1(
        finding_id="note-navigation-prefix",
        kind="quality",
        criterion="hierarchy",
        section="Navigation",
        claim=(
            "Navigation must be the first labeled section after the header, but the candidate "
            "places it after At a glance and does not follow the required prefix order."
        ),
        quoted_candidate_span="## Navigation",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair=(
            "Ensure Navigation is the first H2 section after the header, before At a glance."
        ),
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract=contract,
    )

    assert not result.valid
    assert any("document.required_h2_prefix" in error for error in result.errors)
