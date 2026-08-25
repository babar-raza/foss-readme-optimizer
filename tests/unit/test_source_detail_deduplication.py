"""Prove routed source detail is not spliced in where the section already presents it."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.presentation.verified_source_detail_deduplication import (
    drop_already_presented_blocks,
    routed_block_title,
    section_presented_titles,
)


@dataclass(frozen=True)
class _Block:
    markdown: str


_COMPOSED = (
    "# Product\n\n"
    "## Key Capabilities\n\n"
    "- **Read and write cell values and formulas** - Use Cell.PutValue() to insert strings.\n"
    "- **Apply cell styles** - Retrieve and apply a Style object.\n\n"
    "## License\n\nMIT.\n"
)

_DUPLICATE = _Block(
    "- **Read and write cell values and formulas**: `Cell.PutValue()` accepts strings,\n  doubles."
)
_SOURCE_ONLY = _Block("- **Create or load `.xlsx` workbooks**: construct a blank `Workbook`.")


def test_title_is_compared_across_renderings() -> None:
    """The authored cluster and the inherited bullet render the same capability
    differently, so only the normalized bold title is compared."""

    assert routed_block_title(_DUPLICATE.markdown) == "read and write cell values and formulas"
    assert routed_block_title(_SOURCE_ONLY.markdown) == "create or load .xlsx workbooks"
    assert section_presented_titles(_COMPOSED, "Key Capabilities") == frozenset(
        {"read and write cell values and formulas", "apply cell styles"}
    )


def test_duplicate_capability_is_not_routed_but_source_only_survives() -> None:
    kept = drop_already_presented_blocks(
        _COMPOSED,
        "Key Capabilities",
        [_DUPLICATE, _SOURCE_ONLY],
    )

    assert [routed_block_title(block.markdown) for block in kept] == [
        "create or load .xlsx workbooks"
    ]


def test_section_the_candidate_does_not_present_keeps_every_block() -> None:
    """Negative control: dedupe never reaches beyond the destination section."""

    blocks = [_DUPLICATE, _SOURCE_ONLY]

    assert drop_already_presented_blocks(_COMPOSED, "Installation", blocks) == blocks


def test_block_without_a_bold_title_is_always_kept() -> None:
    """A routed block that is not a titled capability bullet has no title to
    compare, so it is never dropped by this rule."""

    prose = _Block("The samples directory builds a standalone executable.")

    assert drop_already_presented_blocks(_COMPOSED, "Key Capabilities", [prose]) == [prose]


def test_empty_destination_section_keeps_every_block() -> None:
    composed = "# Product\n\n## Key Capabilities\n\n## License\n\nMIT.\n"
    blocks = [_DUPLICATE, _SOURCE_ONLY]

    assert drop_already_presented_blocks(composed, "Key Capabilities", blocks) == blocks
