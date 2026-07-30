"""Normalize and inspect Enterprise Edition terminology in trusted candidates."""

from __future__ import annotations

import re

_FENCE = re.compile(r"(?m)^(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)$")
_PRODUCT_MARKDOWN_LINK = re.compile(
    r"(?<!!)\[(?P<label>[^\]]+)\]\("
    r"(?P<url>https://products\.aspose\.com/[^)\s]+)"
    r"(?P<title>\s+\"[^\"]*\")?\)"
)
_PROMOTIONAL_MARKDOWN_LINK = re.compile(
    r"(?<!!)\[(?P<label>[^\]]+)\]\("
    r"(?P<url>https://(?:[^/]+\.)?aspose\.(?:com|org)/[^)\s]+)"
    r"(?P<title>\s+\"[^\"]*\")?\)",
    re.IGNORECASE,
)
_RAW_ASPOSE_LABEL = re.compile(
    r"(?im)^(?P<prefix>[ \t]*(?:[-*+][ \t]+)?)"
    r"(?P<label>[A-Za-z][^:\r\n]{0,80}):[ \t]*"
    r"(?P<url>https://(?:[^/\s]+\.)?aspose\.(?:com|org)/[^\s<>)]+)[ \t]*$"
)
_PRODUCT_URL = re.compile(r"https://products\.aspose\.com/[^\s<>)]+", re.IGNORECASE)
_PROHIBITED_ENTERPRISE_TERMS = re.compile(
    r"(?i)\b(?:commercial|on[- ]premise)\s+"
    r"(?:enterprise\s+edition|package|library|product|edition)\b"
)
_LEGACY_ENTERPRISE_TERMS = re.compile(
    r"(?i)\b(?:commercial\s+on[- ]premise\s+(?:product|edition)"
    r"|on[- ]premise\s+(?:product|edition)"
    r"|commercial\s+(?:product|edition))\b"
)
_BRANDED_ON_PREMISE = re.compile(
    r"(?i)\bcommercial\s+(?P<brand>Aspose\.[A-Za-z0-9.]+\s+)"
    r"on[- ]premise(?:\s+(?P<noun>package|library|product|edition))?\b"
)
_COMMERCIAL_ARTIFACT = re.compile(r"(?i)\bcommercial\s+(?P<noun>package|library)\b")
_COMMERCIAL_ENTERPRISE = re.compile(r"(?i)\bcommercial\s+Enterprise Edition\b")


def _visitor_ranges(markdown: str) -> list[tuple[int, int]]:
    fences = list(_FENCE.finditer(markdown))
    if len(fences) % 2:
        return [(0, len(markdown))]
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for opening, closing in zip(fences[::2], fences[1::2], strict=True):
        if cursor < opening.start():
            ranges.append((cursor, opening.start()))
        cursor = closing.end()
    if cursor < len(markdown):
        ranges.append((cursor, len(markdown)))
    return ranges


def _normalize_product_link(match: re.Match[str]) -> str:
    label = match.group("label").strip()
    if "enterprise edition" not in label.casefold():
        platform = re.fullmatch(r"(?P<product>Aspose\.[^]]+?)\s+for\s+(?P<platform>.+)", label)
        if platform is not None:
            label = (
                f"{platform.group('product')} Enterprise Edition for {platform.group('platform')}"
            )
        elif label.casefold().startswith("aspose."):
            label = f"{label} Enterprise Edition"
        else:
            label = "Enterprise Edition"
    return f"[{label}]({match.group('url')}{match.group('title') or ''})"


def _normalize_visitor_text(text: str) -> str:
    def branded_replacement(match: re.Match[str]) -> str:
        noun = match.group("noun")
        suffix = f" {noun}" if noun and noun.casefold() in {"package", "library"} else ""
        return f"{match.group('brand')}Enterprise Edition{suffix}"

    normalized = _BRANDED_ON_PREMISE.sub(branded_replacement, text)
    normalized = _LEGACY_ENTERPRISE_TERMS.sub("Enterprise Edition", normalized)
    normalized = _COMMERCIAL_ENTERPRISE.sub("Enterprise Edition", normalized)
    normalized = _COMMERCIAL_ARTIFACT.sub(
        lambda match: f"Enterprise Edition {match.group('noun')}",
        normalized,
    )
    normalized = _PRODUCT_MARKDOWN_LINK.sub(_normalize_product_link, normalized)

    def labeled_url_replacement(match: re.Match[str]) -> str:
        label = match.group("label").strip()
        if "products.aspose.com" in match.group("url").casefold():
            label = "Enterprise Edition"
        return f"{match.group('prefix')}[{label}]({match.group('url')})"

    return _RAW_ASPOSE_LABEL.sub(labeled_url_replacement, normalized)


def normalize_enterprise_edition_terminology(markdown: str) -> str:
    """Use the governed public name for every visitor-facing aspose.com product."""

    rendered = markdown
    for start, end in reversed(_visitor_ranges(markdown)):
        rendered = rendered[:start] + _normalize_visitor_text(rendered[start:end]) + rendered[end:]
    return rendered


def unlink_duplicate_opening_promotional_links(markdown: str) -> str:
    """Keep the opening product-first when an exact promotional URL recurs below it."""

    first_h2 = re.search(r"(?m)^## ", markdown)
    if first_h2 is None:
        return markdown
    boundary = first_h2.start()
    opening = markdown[:boundary]
    below_fold = markdown[boundary:]
    return (
        _PROMOTIONAL_MARKDOWN_LINK.sub(
            lambda match: (
                match.group("label") if match.group("url") in below_fold else match.group(0)
            ),
            opening,
        )
        + below_fold
    )


def unnamed_enterprise_product_references(markdown: str) -> tuple[str, ...]:
    """Return visitor-facing products.aspose.com references lacking the governed term."""

    invalid: list[str] = []
    for start, end in _visitor_ranges(markdown):
        visitor = markdown[start:end]
        links = list(_PRODUCT_MARKDOWN_LINK.finditer(visitor))
        invalid.extend(
            match.group(0)
            for match in links
            if "enterprise edition" not in match.group("label").casefold()
        )
        markdown_link_spans = [match.span() for match in links]
        for url in _PRODUCT_URL.finditer(visitor):
            if any(
                link_start <= url.start() < link_end for link_start, link_end in markdown_link_spans
            ):
                continue
            line_start = visitor.rfind("\n", 0, url.start()) + 1
            line_end = visitor.find("\n", url.end())
            line = visitor[line_start:] if line_end < 0 else visitor[line_start:line_end]
            if "enterprise edition" not in line.casefold():
                invalid.append(line.strip())
    return tuple(invalid)


def contains_prohibited_enterprise_terminology(markdown: str) -> bool:
    """Return whether visitor-facing prose retains a prohibited legacy descriptor."""

    return any(
        _PROHIBITED_ENTERPRISE_TERMS.search(markdown[start:end])
        for start, end in _visitor_ranges(markdown)
    )
