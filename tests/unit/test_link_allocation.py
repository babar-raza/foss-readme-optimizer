"""Prove deterministic README content measurement and link-allocation ceilings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from readme_agent.links.allocation import code_sha256, resolve_link_budget
from readme_agent.links.occurrences import (
    count_aspose_link_occurrences,
    find_aspose_link_occurrences,
)
from readme_agent.registry.models import LinkAllocationPolicyV1


def _markdown_with_words(count: int) -> str:
    return " ".join(f"word{index}" for index in range(count)) + "\n"


@pytest.mark.parametrize(
    ("words", "expected"),
    [(600, 2), (601, 3), (1_200, 3), (1_201, 4), (2_000, 4), (2_001, 5), (3_000, 5), (3_001, 6)],
)
def test_auto_budget_uses_exact_content_unit_tiers(words: int, expected: int) -> None:
    budget = resolve_link_budget(LinkAllocationPolicyV1(), _markdown_with_words(words))

    assert budget.measurement.total_content_units == words
    assert budget.max_total == expected


def test_verified_code_block_adds_exactly_one_hundred_units() -> None:
    code = "from product import Widget\nWidget().save('out.bin')"
    markdown = f"# Product\n\nWords here.\n\n```python\n{code}\n```\n"

    unverified = resolve_link_budget(LinkAllocationPolicyV1(), markdown)
    verified = resolve_link_budget(
        LinkAllocationPolicyV1(),
        markdown,
        verified_code_sha256s={code_sha256(code)},
    )

    assert unverified.measurement.verified_code_units == 0
    assert verified.measurement.verified_code_units == 100
    assert verified.measurement.total_content_units == (
        unverified.measurement.total_content_units + 100
    )


def test_measurement_excludes_urls_badges_html_and_mermaid_source() -> None:
    markdown = """# Product

Visible words [help](https://docs.aspose.org/cells/python/example/) remain.

[![Badge](https://img.shields.io/badge/test-blue)](https://products.aspose.org/cells/)

<!-- hidden words should not count -->

```mermaid
flowchart LR
  hidden["many hidden words"]
```
"""

    budget = resolve_link_budget(LinkAllocationPolicyV1(), markdown)

    assert budget.measurement.visible_prose_words == 5


def test_configured_policy_replaces_every_auto_ceiling() -> None:
    policy = LinkAllocationPolicyV1.model_validate(
        {
            "mode": "configured",
            "max_total": 3,
            "domain_maxima": {"aspose.org": 1, "aspose.com": 2},
            "surface_maxima": {
                "products": 1,
                "docs": 2,
                "kb": 1,
                "blog": 0,
                "reference": 1,
            },
        }
    )

    budget = resolve_link_budget(policy, _markdown_with_words(5_000))

    assert budget.mode == "configured"
    assert budget.max_total == 3
    assert budget.domain_maxima == {"aspose.org": 1, "aspose.com": 2}
    assert budget.surface_maxima["blog"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "configured"},
        {
            "mode": "configured",
            "max_total": -1,
            "domain_maxima": {"aspose.org": 0, "aspose.com": 0},
            "surface_maxima": {
                "products": 0,
                "docs": 0,
                "kb": 0,
                "blog": 0,
                "reference": 0,
            },
        },
        {
            "mode": "configured",
            "max_total": 1,
            "domain_maxima": {"aspose.org": 2, "aspose.com": 0},
            "surface_maxima": {
                "products": 0,
                "docs": 0,
                "kb": 0,
                "blog": 0,
                "reference": 0,
            },
        },
        {"mode": "auto", "max_total": 2},
    ],
)
def test_invalid_configured_or_mixed_policies_fail_closed(payload: dict) -> None:
    with pytest.raises(ValidationError):
        LinkAllocationPolicyV1.model_validate(payload)


def test_every_url_form_and_repeat_consumes_one_occurrence() -> None:
    target = "https://docs.aspose.org/cells/python/example/"
    markdown = f"""[Markdown]({target})
![Image]({target})
<{target}>
<a href="{target}">HTML</a>
Raw: {target}
"""

    occurrences = find_aspose_link_occurrences(markdown)
    counts = count_aspose_link_occurrences(markdown)

    assert [item.form for item in occurrences] == [
        "markdown",
        "image",
        "autolink",
        "html",
        "raw",
    ]
    assert counts.total == 5
    assert counts.by_parent_domain["aspose.org"] == 5
    assert counts.by_surface["docs"] == 5
    assert counts.repeated_targets[target] == 5
