"""Drop routed source detail whose destination section already presents it."""

from __future__ import annotations

import re

from readme_agent.readme.document_structure import heading_identity, parse_headings

_LEAD_TITLE = re.compile(r"^\s*[-*+]\s+\*\*(?P<title>[^*]+)\*\*")
_BOLD = re.compile(r"\*\*(?P<title>[^*]+)\*\*")


def _normalized_title(value: str) -> str:
    """Normalize a bold capability title for cross-rendering comparison.

    The authored cluster and the inherited source bullet render the same
    capability differently (`- **Title** - prose` vs `- **Title**: prose`,
    backticked symbols vs plain), so only the bold title itself is compared,
    case- and punctuation-insensitively.
    """

    text = value.replace("`", " ")
    return " ".join(text.casefold().split()).strip(" .:;,-")


def routed_block_title(block_markdown: str) -> str | None:
    """Return the bold capability title leading one routed source block."""

    match = _LEAD_TITLE.match(block_markdown)
    if match is None:
        return None
    title = _normalized_title(match.group("title"))
    return title or None


def section_presented_titles(composed: str, target_title: str) -> frozenset[str]:
    """Return the bold titles a composed section already presents to visitors."""

    target = heading_identity(target_title)
    for heading in parse_headings(composed):
        if heading.level != 2 or heading_identity(heading.title) != target:
            continue
        body = composed[heading.heading_end : heading.section_end]
        return frozenset(title for raw in _BOLD.findall(body) if (title := _normalized_title(raw)))
    return frozenset()


def drop_already_presented_blocks(composed: str, target_title: str, blocks: list):
    """Return only the routed blocks the destination does not already present.

    idea.md: "Competing sections may not repeat the same capability inventory."
    The authored cluster owns the section's organization and wording (source
    tone and prose structure are explicitly not preservation obligations), so
    an inherited bullet whose capability the section already presents must not
    also be spliced in verbatim -- every material source unit maps exactly once.

    A block is dropped only when its own bold title is already presented in the
    destination. A capability the section does not present is still routed, so
    source-only material is never silently lost here; and a dropped block stops
    surviving in the candidate, which sends it through the ordinary source-claim
    disposition path rather than out of the accounting.
    """

    presented = section_presented_titles(composed, target_title)
    if not presented:
        return blocks
    return [
        block
        for block in blocks
        if (title := routed_block_title(block.markdown)) is None or title not in presented
    ]


__all__ = [
    "drop_already_presented_blocks",
    "routed_block_title",
    "section_presented_titles",
]
