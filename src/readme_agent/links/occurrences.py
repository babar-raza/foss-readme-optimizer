"""Count every rendered Aspose URL occurrence and classify its surface."""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.links.catalog import normalize_target_url

AsposeUrlForm = Literal["markdown", "image", "autolink", "html", "raw"]
CountedSurface = Literal["products", "docs", "kb", "blog", "reference", "other"]

_ASPOSE_URL = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*aspose\.(?:com|org)(?:/[^\s<>)\"']*)?",
    re.IGNORECASE,
)


class AsposeLinkOccurrenceV1(BaseModel):
    """One exact visitor-visible URL occurrence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    normalized_url: str
    parent_domain: Literal["aspose.org", "aspose.com"]
    surface: CountedSurface
    form: AsposeUrlForm
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=0)


class AsposeLinkOccurrenceCountsV1(BaseModel):
    """Final candidate counts checked against a resolved budget."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total: int = Field(ge=0)
    by_parent_domain: dict[Literal["aspose.org", "aspose.com"], int]
    by_surface: dict[CountedSurface, int]
    repeated_targets: dict[str, int]


def _surface(hostname: str) -> CountedSurface:
    prefix = hostname.casefold().split(".", 1)[0]
    if prefix in {"products", "docs", "kb", "blog", "reference"}:
        return prefix  # type: ignore[return-value]
    return "other"


def _form(markdown: str, start: int, end: int) -> AsposeUrlForm:
    before = markdown[max(0, start - 160) : start]
    after = markdown[end : min(len(markdown), end + 3)]
    if re.search(r"!\[[^\]]*\]\([^)]*$", before):
        return "image"
    if re.search(r"\[[^\]]*\]\([^)]*$", before):
        return "markdown"
    if before.endswith("<") and after.startswith(">"):
        return "autolink"
    if re.search(r"(?:href|src)\s*=\s*[\"'][^\"']*$", before, re.IGNORECASE):
        return "html"
    return "raw"


def find_aspose_link_occurrences(markdown: str) -> list[AsposeLinkOccurrenceV1]:
    """Find each literal occurrence once, irrespective of Markdown/HTML form."""

    occurrences: list[AsposeLinkOccurrenceV1] = []
    for match in _ASPOSE_URL.finditer(markdown):
        url = match.group(0).rstrip(".,;:")
        end = match.start() + len(url)
        hostname = (urlparse(url).hostname or "").casefold()
        parent: Literal["aspose.org", "aspose.com"] = (
            "aspose.org" if hostname.endswith("aspose.org") else "aspose.com"
        )
        occurrences.append(
            AsposeLinkOccurrenceV1(
                url=url,
                normalized_url=normalize_target_url(url),
                parent_domain=parent,
                surface=_surface(hostname),
                form=_form(markdown, match.start(), end),
                character_start=match.start(),
                character_end=end,
            )
        )
    return occurrences


def count_aspose_link_occurrences(markdown: str) -> AsposeLinkOccurrenceCountsV1:
    """Aggregate all occurrences; repeated targets consume repeated slots."""

    occurrences = find_aspose_link_occurrences(markdown)
    domains: dict[Literal["aspose.org", "aspose.com"], int] = {
        "aspose.org": 0,
        "aspose.com": 0,
    }
    surfaces: dict[CountedSurface, int] = {
        "products": 0,
        "docs": 0,
        "kb": 0,
        "blog": 0,
        "reference": 0,
        "other": 0,
    }
    targets: dict[str, int] = {}
    for occurrence in occurrences:
        domains[occurrence.parent_domain] += 1
        surfaces[occurrence.surface] += 1
        targets[occurrence.normalized_url] = targets.get(occurrence.normalized_url, 0) + 1
    return AsposeLinkOccurrenceCountsV1(
        total=len(occurrences),
        by_parent_domain=domains,
        by_surface=surfaces,
        repeated_targets={url: count for url, count in targets.items() if count > 1},
    )
