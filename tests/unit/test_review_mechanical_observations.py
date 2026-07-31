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
                "parameters": {"brand_contract_version": "v1"},
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
