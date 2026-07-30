"""Prove trusted-candidate Enterprise Edition normalization boundaries."""

from __future__ import annotations

from readme_agent.readme.trusted_candidate_terminology import (
    normalize_enterprise_edition_terminology,
    unlink_duplicate_opening_promotional_links,
    unnamed_enterprise_product_references,
)


def test_product_reference_normalization_does_not_rewrite_code() -> None:
    markdown = (
        "[Aspose.Note for .NET](https://products.aspose.com/note/net/)\n\n"
        "```python\n"
        'url = "https://products.aspose.com/note/net/"\n'
        "```\n"
    )

    normalized = normalize_enterprise_edition_terminology(markdown)

    assert (
        "[Aspose.Note Enterprise Edition for .NET](https://products.aspose.com/note/net/)"
    ) in normalized
    assert 'url = "https://products.aspose.com/note/net/"' in normalized
    assert unnamed_enterprise_product_references(normalized) == ()


def test_labeled_raw_aspose_urls_become_budgetable_links() -> None:
    markdown = (
        "- Product: https://products.aspose.com/note/net/\n"
        "- Documentation: https://docs.aspose.com/note/net/\n"
    )

    normalized = normalize_enterprise_edition_terminology(markdown)

    assert "[Enterprise Edition](https://products.aspose.com/note/net/)" in normalized
    assert "[Documentation](https://docs.aspose.com/note/net/)" in normalized
    assert unnamed_enterprise_product_references(normalized) == ()


def test_duplicate_promotional_link_is_unlinked_only_in_opening() -> None:
    markdown = (
        "# Widget\n\n"
        "Inspired by [Aspose.Note Enterprise Edition for .NET]"
        "(https://products.aspose.com/note/net/).\n\n"
        "## Related products\n\n"
        "[Aspose.Note Enterprise Edition for .NET]"
        "(https://products.aspose.com/note/net/)\n"
    )

    normalized = unlink_duplicate_opening_promotional_links(markdown)

    opening, below_fold = normalized.split("## Related products", maxsplit=1)
    assert "https://products.aspose.com" not in opening
    assert "Aspose.Note Enterprise Edition for .NET" in opening
    assert "https://products.aspose.com/note/net/" in below_fold


def test_unique_opening_promotional_link_remains_for_fail_closed_validation() -> None:
    markdown = (
        "# Widget\n\n"
        "[Aspose.Note Enterprise Edition for .NET]"
        "(https://products.aspose.com/note/net/)\n\n"
        "## Usage\n\nRun it.\n"
    )

    assert unlink_duplicate_opening_promotional_links(markdown) == markdown
