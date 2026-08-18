"""Compare an anchor's visible platform claim against its destination's real platforms.

T10 (freshness-service plan): the existing link-occurrence machinery
(`occurrences.py`) tracks every Aspose URL and its position, but never captures the
*anchor text* for a markdown-form link -- so nothing has ever compared what an anchor
says ("Aspose.PDF for .NET") against what its destination catalog record actually
serves (`platforms=["java"]`). Two shipped org-side PDF README defects were exactly
this: an anchor naming one platform, linking to a page for another. This module adds
that comparison as a deterministic, catalog-driven check.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.links.catalog import lookup_verified_target
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1

# Catalog `platforms` values are the short lowercase keys used across data/products.json
# and data/platform_priorities.json (python, net, java, cpp, typescript, rust, go).
# This maps every natural-language form that could appear in visitor-facing anchor
# text to that canonical key. Deliberately conservative: an unmapped platform word
# in an anchor is not flagged (never a false accusation), only a mapped one that
# disagrees with the destination's actual platforms is.
_PLATFORM_ALIASES: dict[str, str] = {
    ".net": "net",
    "dotnet": "net",
    "c#": "net",
    "java": "java",
    "python": "python",
    "c++": "cpp",
    "cpp": "cpp",
    "typescript": "typescript",
    "node.js": "typescript",
    "nodejs": "typescript",
    "rust": "rust",
    "go": "go",
    "golang": "go",
}
_ALIAS_PATTERN = re.compile(
    "|".join(re.escape(alias) for alias in sorted(_PLATFORM_ALIASES, key=len, reverse=True)),
    re.IGNORECASE,
)
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_VIA_ANCHOR = re.compile(r"\bvia\b", re.IGNORECASE)


class AnchorDestinationMismatchV1(BaseModel):
    """One anchor whose visible platform claim disagrees with its destination."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_text: str
    url: str
    claimed_platform: str = Field(description="canonical platform key parsed from anchor_text")
    destination_platforms: tuple[str, ...]
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=0)


def find_anchor_destination_mismatches(
    markdown: str,
    catalogs: AsposeLinkCatalogSetV1,
) -> list[AnchorDestinationMismatchV1]:
    """Find every markdown-form Aspose link whose anchor names a platform absent
    from its destination's verified catalog record.

    Fails soft (no finding) when the destination is not in the catalog at all --
    that is a different, already-covered failure (`candidate contains non-linkable
    Aspose target` in contextual_validation.py); this check only fires when there
    IS a verified record and it disagrees with the anchor's own claim.
    """

    findings: list[AnchorDestinationMismatchV1] = []
    for match in _MARKDOWN_LINK.finditer(markdown):
        anchor_text, url = match.group(1), match.group(2)
        if "aspose.com" not in url and "aspose.org" not in url:
            continue
        alias_match = _ALIAS_PATTERN.search(anchor_text)
        if alias_match is None:
            continue
        claimed = _PLATFORM_ALIASES[alias_match.group(0).casefold()]
        record = lookup_verified_target(catalogs, url)
        if record is None or not record.platforms:
            continue
        if claimed not in {p.casefold() for p in record.platforms}:
            findings.append(
                AnchorDestinationMismatchV1(
                    anchor_text=anchor_text,
                    url=url,
                    claimed_platform=claimed,
                    destination_platforms=tuple(record.platforms),
                    character_start=match.start(),
                    character_end=match.end(),
                )
            )
    return findings


class ViaAnchorFindingV1(BaseModel):
    """One Aspose anchor phrased with the prohibited 'via' bridge-disclosure form.

    Binding rule (MT044, carried into this plan's §4 contract): anchors are
    destination-driven, never phrased as "via {platform}" -- that framing was
    revoked after MT043 shipped it and then had to be walked back.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_text: str
    url: str
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=0)


def find_via_anchor_findings(markdown: str) -> list[ViaAnchorFindingV1]:
    """Find every Aspose-domain anchor whose visible text contains ' via '."""

    findings: list[ViaAnchorFindingV1] = []
    for match in _MARKDOWN_LINK.finditer(markdown):
        anchor_text, url = match.group(1), match.group(2)
        if "aspose.com" not in url and "aspose.org" not in url:
            continue
        if _VIA_ANCHOR.search(anchor_text):
            findings.append(
                ViaAnchorFindingV1(
                    anchor_text=anchor_text,
                    url=url,
                    character_start=match.start(),
                    character_end=match.end(),
                )
            )
    return findings


__all__ = [
    "AnchorDestinationMismatchV1",
    "ViaAnchorFindingV1",
    "find_anchor_destination_mismatches",
    "find_via_anchor_findings",
]
