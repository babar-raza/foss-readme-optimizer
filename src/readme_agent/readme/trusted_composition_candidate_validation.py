"""Validate an assembled trusted README against presentation contracts."""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

from readme_agent.errors import LLMError
from readme_agent.facts.example_quality import source_contains_comments, strip_source_comments
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.document_structure import (
    github_anchor,
    normalize_navigation_targets,
    remove_excess_headings,
)
from readme_agent.registry.loader import load_products

TRUSTED_CANDIDATE_NORMALIZATION_VERSION = (
    "trusted-candidate-normalization-v9-promotional-blockquote-unwrapping"
)

_HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
_URL = re.compile(r"https?://[^\s<>)\"']+")
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
_FENCE = re.compile(r"(?m)^(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)$")
_MARKDOWN_LINK = re.compile(
    r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
_BLOCKQUOTE_BLOCK = re.compile(r"(?m)(?:^[ \t]*>[^\r\n]*(?:\r?\n|$))+")
_NAVIGATION_LINE = re.compile(r"(?m)^(?!\!)(?:[-*+]\s+)?\[[^\]]+\]\(#[^)]+\).*$")


def strip_readme_comments(markdown: str) -> str:
    """Remove visitor-visible HTML and source comments from fenced examples."""

    cleaned = _HTML_COMMENT.sub("", markdown)
    fences = list(_FENCE.finditer(cleaned))
    if len(fences) % 2:
        return cleaned
    rendered: list[str] = []
    cursor = 0
    for opening, closing in zip(fences[::2], fences[1::2], strict=True):
        language = opening.group("info").strip().split(maxsplit=1)[0].casefold()
        body_start = opening.end()
        body_end = closing.start()
        rendered.append(cleaned[cursor:body_start])
        source = cleaned[body_start:body_end]
        stripped = strip_source_comments(language, source)
        if source.startswith("\r\n") and not stripped.startswith("\r\n"):
            stripped = "\r\n" + stripped.lstrip("\r\n")
        elif source.startswith("\n") and not stripped.startswith("\n"):
            stripped = "\n" + stripped.lstrip("\n")
        rendered.append(stripped)
        cursor = body_end
    rendered.append(cleaned[cursor:])
    return "".join(rendered)


def normalize_enterprise_edition_terminology(markdown: str) -> str:
    """Use the governed public name for every legacy aspose.com edition label."""

    def branded_replacement(match: re.Match[str]) -> str:
        noun = match.group("noun")
        suffix = f" {noun}" if noun and noun.casefold() in {"package", "library"} else ""
        return f"{match.group('brand')}Enterprise Edition{suffix}"

    normalized = _BRANDED_ON_PREMISE.sub(branded_replacement, markdown)
    normalized = _LEGACY_ENTERPRISE_TERMS.sub("Enterprise Edition", normalized)
    normalized = _COMMERCIAL_ENTERPRISE.sub("Enterprise Edition", normalized)
    return _COMMERCIAL_ARTIFACT.sub(
        lambda match: f"Enterprise Edition {match.group('noun')}",
        normalized,
    )


def normalize_required_section_headings(
    markdown: str,
    graph: TrustedReadmeFactGraphV1,
    *,
    navigation_boundary_prefix: str | None = None,
) -> str:
    """Add exact schema-owned section labels around already-authored content."""

    standards = {item.standard_id for item in graph.configured_standards}
    normalized = markdown
    headings = _heading_counts(normalized)
    if "readme.at_a_glance_mermaid" in standards and ("h2", "at a glance") not in headings:
        mermaid = normalized.find("```mermaid")
        if mermaid >= 0:
            normalized = normalized[:mermaid] + "## At a glance\n\n" + normalized[mermaid:]
    headings = _heading_counts(normalized)
    if "readme.navigation" in standards and ("h2", "navigation") not in headings:
        navigation = _NAVIGATION_LINE.search(normalized)
        if navigation is not None:
            normalized = (
                normalized[: navigation.start()]
                + "## Navigation\n\n"
                + normalized[navigation.start() :]
            )
    normalized = re.sub(
        r"(?m)(!\[[^\r\n]+\]\([^)]+\))[ \t]*\r?\n(?=##[ \t])",
        r"\1\n\n",
        normalized,
    )
    normalized = re.sub(
        r"(?m)^```[ \t]*\r?\n(?=##[ \t])",
        "```\n\n",
        normalized,
    )
    normalized = re.sub(
        r"(?m)^([-*+][ \t]+\[[^\r\n]+\]\(#[^)]+\))[ \t]*\r?\n(?=[A-Za-z0-9>])",
        r"\1\n\n",
        normalized,
    )
    return normalize_navigation_targets(
        normalized,
        boundary_line_prefix=navigation_boundary_prefix,
    )


def normalize_contextual_link_budget(
    markdown: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Retain prioritized Aspose links within configured total and domain limits."""

    standard = next(
        (
            item
            for item in graph.configured_standards
            if item.standard_id == "readme.contextual_links"
        ),
        None,
    )
    if standard is None:
        return markdown
    parameters = standard.parameters
    max_total = parameters.get("max_total")
    if not isinstance(max_total, int):
        return markdown
    domain_maxima = {
        str(domain).casefold(): int(limit)
        for domain, limit in parameters.get("domain_maxima", {}).items()
    }
    priority_hosts = [str(host).casefold() for host in parameters.get("priority_hosts", [])]
    surface_by_url = {
        _clean_url(str(url)): str(surface).casefold()
        for url, surface in parameters.get("surface_by_url", {}).items()
    }
    surface_maxima = {
        str(surface).casefold(): int(limit)
        for surface, limit in parameters.get("surface_maxima", {}).items()
    }
    matches = [
        match
        for match in _MARKDOWN_LINK.finditer(markdown)
        if _belongs_to(match.group("url"), "aspose.org")
        or _belongs_to(match.group("url"), "aspose.com")
    ]
    occurrences: dict[str, int] = {}
    ranked: list[tuple[tuple[int, int, int, int], int, re.Match[str]]] = []
    surface_order = {"products": 0, "docs": 1, "kb": 2, "reference": 3, "blog": 4}
    for index, match in enumerate(matches):
        url = _clean_url(match.group("url"))
        host = urlsplit(url).netloc.casefold()
        duplicate_order = occurrences.get(url, 0)
        occurrences[url] = duplicate_order + 1
        try:
            host_rank = priority_hosts.index(host)
        except ValueError:
            host_rank = len(priority_hosts)
        surface = surface_by_url.get(url) or host.split(".", maxsplit=1)[0]
        ranked.append(
            (
                (
                    1 if duplicate_order else 0,
                    host_rank,
                    surface_order.get(surface, len(surface_order)),
                    index,
                ),
                index,
                match,
            )
        )
    retained: set[int] = set()
    domain_counts: dict[str, int] = {}
    surface_counts: dict[str, int] = {}
    for _, index, match in sorted(ranked):
        if len(retained) >= max_total:
            break
        url = match.group("url")
        domain = next(
            (candidate for candidate in domain_maxima if _belongs_to(url, candidate)),
            "",
        )
        if domain and domain_counts.get(domain, 0) >= domain_maxima[domain]:
            continue
        clean_url = _clean_url(url)
        surface = (
            surface_by_url.get(clean_url)
            or urlsplit(clean_url).netloc.casefold().split(".", maxsplit=1)[0]
        )
        if surface in surface_maxima and surface_counts.get(surface, 0) >= surface_maxima[surface]:
            continue
        retained.add(index)
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        surface_counts[surface] = surface_counts.get(surface, 0) + 1
    current = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal current
        url = match.group("url")
        if not (_belongs_to(url, "aspose.org") or _belongs_to(url, "aspose.com")):
            return match.group(0)
        keep = current in retained
        current += 1
        return match.group(0) if keep else match.group("label")

    return _MARKDOWN_LINK.sub(replace, markdown)


def normalize_promotional_blockquotes(
    markdown: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Turn forbidden promotional callouts into ordinary below-fold prose."""

    forbid_blockquotes = any(
        standard.standard_id == "readme.contextual_links"
        and bool(standard.parameters.get("forbid_blockquotes"))
        for standard in graph.configured_standards
    )
    if not forbid_blockquotes:
        return markdown

    def replace(match: re.Match[str]) -> str:
        block = match.group(0)
        if not any(
            _belongs_to(url.group("url"), "aspose.org")
            or _belongs_to(url.group("url"), "aspose.com")
            for url in _MARKDOWN_LINK.finditer(block)
        ):
            return block
        return re.sub(r"(?m)^[ \t]*>[ \t]?", "", block)

    return _BLOCKQUOTE_BLOCK.sub(replace, markdown)


def normalize_trusted_candidate(
    markdown: str,
    graph: TrustedReadmeFactGraphV1,
    *,
    navigation_boundary_prefix: str | None = None,
) -> str:
    """Apply the canonical configured-standard normalization pipeline."""

    structured = normalize_required_section_headings(
        normalize_enterprise_edition_terminology(
            normalize_inherited_code_blocks(strip_readme_comments(markdown), graph)
        ),
        graph,
        navigation_boundary_prefix=navigation_boundary_prefix,
    )
    source_headings = _heading_counts("\n\n".join(fact.value for fact in graph.inherited_facts))
    allowed_counts = {
        (int(tag.removeprefix("h")), title): count
        for (tag, title), count in source_headings.items()
    }
    return normalize_contextual_link_budget(
        normalize_promotional_blockquotes(
            normalize_navigation_targets(
                remove_excess_headings(structured, allowed_counts),
                boundary_line_prefix=navigation_boundary_prefix,
            ),
            graph,
        ),
        graph,
    )


def _non_mermaid_fenced_spans(markdown: str) -> list[tuple[int, int]]:
    fences = list(_FENCE.finditer(markdown))
    if len(fences) % 2:
        return []
    spans: list[tuple[int, int]] = []
    for opening, closing in zip(fences[::2], fences[1::2], strict=True):
        language = opening.group("info").strip().split(maxsplit=1)[0].casefold()
        if language != "mermaid":
            spans.append((opening.start(), closing.end()))
    return spans


def normalize_inherited_code_blocks(
    markdown: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Restore curated source code blocks in order while removing their comments."""

    source_blocks: list[str] = []
    for fact in graph.inherited_facts:
        if fact.material_kind != "code":
            continue
        spans = _non_mermaid_fenced_spans(fact.value)
        source_blocks.extend(strip_readme_comments(fact.value[start:end]) for start, end in spans)
    candidate_spans = _non_mermaid_fenced_spans(markdown)
    if not source_blocks or len(candidate_spans) != len(source_blocks):
        return markdown
    normalized = markdown
    for (start, end), source_block in reversed(
        list(zip(candidate_spans, source_blocks, strict=True))
    ):
        normalized = normalized[:start] + source_block + normalized[end:]
    return normalized


def validate_trusted_candidate_contract(
    source_text: str,
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> None:
    """Enforce configured additions without upgrading inherited factual assurance."""

    if not candidate.strip():
        raise LLMError("trusted composition produced an empty candidate")
    if _HTML_COMMENT.search(candidate):
        raise LLMError("trusted composition candidate contains an HTML comment")
    _validate_markdown(candidate)
    _validate_no_new_cross_product(source_text, candidate, graph.org_repo)
    headings = re.findall(r"(?m)^# (.+?)\s*$", candidate)
    standards = {item.standard_id: item for item in graph.configured_standards}
    forbidden_terms = {
        str(term).casefold()
        for standard in graph.configured_standards
        for term in standard.parameters.get("forbidden_product_terms", [])
    }
    introduced_cross_product = sorted(
        term
        for term in forbidden_terms
        if term in candidate.casefold() and term not in source_text.casefold()
    )
    if introduced_cross_product:
        raise LLMError(
            f"trusted candidate introduced cross-product prose: {introduced_cross_product}"
        )
    if "readme.header" in standards and len(headings) != 1:
        raise LLMError("configured README header requires exactly one H1")
    if "readme.badges" in standards:
        parameters = standards["readme.badges"].parameters
        fragments = [str(item) for item in parameters.get("required_fragments", [])]
        if not fragments or any(fragment not in candidate for fragment in fragments):
            raise LLMError("configured badge fragments are absent")
        first_h2 = re.search(r"(?m)^## ", candidate)
        header_boundary = first_h2.start() if first_h2 else len(candidate)
        if any(candidate.find(fragment) > header_boundary for fragment in fragments):
            raise LLMError("configured badges must appear in the README header")
    if "readme.navigation" in standards:
        if ("h2", "navigation") not in _heading_counts(candidate):
            raise LLMError("configured README navigation requires an H2 Navigation section")
    if "readme.at_a_glance_mermaid" in standards:
        if ("h2", "at a glance") not in _heading_counts(candidate):
            raise LLMError("configured at-a-glance Mermaid requires an H2 At a glance section")
        if candidate.count("```mermaid") != 1:
            raise LLMError("configured at-a-glance Mermaid diagram is absent or duplicated")
    if "readme.navigation" in standards:
        labels = [
            str(item).casefold()
            for item in standards["readme.navigation"].parameters.get("required_labels", [])
        ]
        if not labels or any(label not in candidate.casefold() for label in labels):
            raise LLMError("configured README navigation is incomplete")
        _validate_navigation_targets(candidate)
    if "readme.enterprise_edition_terminology" in standards:
        if _PROHIBITED_ENTERPRISE_TERMS.search(candidate):
            raise LLMError("trusted candidate uses prohibited Enterprise Edition terminology")
        if (
            "aspose.com" in candidate.casefold()
            and "enterprise edition" not in candidate.casefold()
        ):
            raise LLMError("aspose.com product reference is not called Enterprise Edition")
    _validate_opening(candidate)
    if "readme.contextual_links" in standards:
        _validate_contextual_links(
            source_text,
            candidate,
            standards["readme.contextual_links"],
            tuple(standards.values()),
        )
    _validate_no_introduced_duplicate_headings(source_text, candidate)


def _validate_contextual_links(
    source_text: str,
    candidate: str,
    standard,
    configured_standards: tuple,
) -> None:
    source_urls = {_clean_url(url) for url in _URL.findall(source_text)}
    candidate_matches = list(_URL.finditer(candidate))
    candidate_urls = [_clean_url(match.group(0)) for match in candidate_matches]
    parameters = standard.parameters
    configured_urls = {
        _clean_url(url)
        for configured in configured_standards
        for value in configured.parameters.values()
        for text in _flatten_strings(value)
        for url in _URL.findall(text)
    }
    allowed_urls = (
        source_urls
        | configured_urls
        | {_clean_url(str(url)) for url in parameters.get("allowed_urls", [])}
    )
    unknown = set(candidate_urls) - allowed_urls
    if unknown:
        raise LLMError(f"trusted candidate introduced unconfigured links: {sorted(unknown)}")
    aspose_urls = [
        url
        for url in candidate_urls
        if _belongs_to(url, "aspose.org") or _belongs_to(url, "aspose.com")
    ]
    max_total = parameters.get("max_total")
    if isinstance(max_total, int) and len(aspose_urls) > max_total:
        raise LLMError("trusted candidate exceeds the configured total link budget")
    for domain, limit in parameters.get("domain_maxima", {}).items():
        normalized_domain = str(domain).casefold()
        count = sum(_belongs_to(url, normalized_domain) for url in aspose_urls)
        if count > int(limit):
            raise LLMError(f"trusted candidate exceeds configured link budget for {domain}")
    surface_by_url = {
        _clean_url(str(url)): str(surface)
        for url, surface in parameters.get("surface_by_url", {}).items()
    }
    for surface, limit in parameters.get("surface_maxima", {}).items():
        count = sum(surface_by_url.get(url) == surface for url in aspose_urls)
        if count > int(limit):
            raise LLMError(
                f"trusted candidate exceeds configured link budget for surface {surface}"
            )
    forbidden_sections = {
        str(section).strip().casefold() for section in parameters.get("forbidden_sections", [])
    }
    forbid_blockquotes = bool(parameters.get("forbid_blockquotes"))
    for match in candidate_matches:
        url = _clean_url(match.group(0))
        if not (_belongs_to(url, "aspose.org") or _belongs_to(url, "aspose.com")):
            continue
        section = _h2_section_at(candidate, match.start())
        if section is None or section in forbidden_sections:
            raise LLMError("Aspose links must appear naturally in below-fold substantive content")
        if forbid_blockquotes and _line_at(candidate, match.start()).lstrip().startswith(">"):
            raise LLMError("Aspose links cannot appear in promotional blockquotes")


def _flatten_strings(value) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for child in value.values() for text in _flatten_strings(child))
    if isinstance(value, (list, tuple)):
        return tuple(text for child in value for text in _flatten_strings(child))
    return ()


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:")


def _belongs_to(url: str, parent_domain: str) -> bool:
    host = urlsplit(url).netloc.casefold()
    domain = parent_domain.casefold()
    return host == domain or host.endswith(f".{domain}")


def _h2_section_at(markdown: str, offset: int) -> str | None:
    headings = list(re.finditer(r"(?m)^##[ \t]+(.+?)\s*$", markdown[:offset]))
    return headings[-1].group(1).strip().casefold() if headings else None


def _line_at(markdown: str, offset: int) -> str:
    start = markdown.rfind("\n", 0, offset) + 1
    end = markdown.find("\n", offset)
    return markdown[start : len(markdown) if end < 0 else end]


def _validate_markdown(candidate: str) -> None:
    fences = list(_FENCE.finditer(candidate))
    if len(fences) % 2:
        raise LLMError("trusted composition candidate has an unclosed Markdown fence")
    for opening, closing in zip(fences[::2], fences[1::2], strict=True):
        if opening.group("marker")[0] != closing.group("marker")[0]:
            raise LLMError("trusted composition candidate has mismatched Markdown fences")
        language = opening.group("info").strip().split(maxsplit=1)[0].casefold()
        body = candidate[opening.end() : closing.start()]
        if source_contains_comments(language, body):
            raise LLMError("trusted composition candidate contains a code comment")
    MarkdownIt("commonmark", {"html": True}).parse(candidate)


def _heading_counts(markdown: str) -> Counter[tuple[str, str]]:
    tokens = MarkdownIt("commonmark", {"html": True}).parse(markdown)
    headings: Counter[tuple[str, str]] = Counter()
    for index, token in enumerate(tokens[:-1]):
        if token.type != "heading_open":
            continue
        inline = tokens[index + 1]
        if inline.type == "inline":
            headings[(token.tag, inline.content.strip().casefold())] += 1
    return headings


def _validate_no_introduced_duplicate_headings(source_text: str, candidate: str) -> None:
    source = _heading_counts(source_text)
    candidate_counts = _heading_counts(candidate)
    introduced = sorted(
        f"{tag} {heading}"
        for (tag, heading), count in candidate_counts.items()
        if count > max(source.get((tag, heading), 0), 1)
    )
    if introduced:
        raise LLMError(f"trusted candidate introduced duplicate headings: {introduced}")


def _validate_navigation_targets(candidate: str) -> None:
    targets = {
        github_anchor(match.group(2))
        for match in re.finditer(r"(?m)^(#{2,6})\s+(.+?)\s*$", candidate)
    }
    for anchor in re.findall(r"\[[^\]]+\]\(#([^)]+)\)", candidate):
        if anchor.casefold() not in targets:
            raise LLMError(f"README navigation targets missing heading #{anchor}")


def _validate_opening(candidate: str) -> None:
    first_h2 = re.search(r"(?m)^## ", candidate)
    opening = candidate[: first_h2.start() if first_h2 else len(candidate)]
    if any(
        "aspose.com" in url.casefold() or "aspose.org" in url.casefold()
        for url in _URL.findall(opening)
    ):
        raise LLMError("Aspose promotional links cannot appear in the README opening")


def _validate_no_new_cross_product(source_text: str, candidate: str, org_repo: str) -> None:
    entries = load_products()
    own_entry = next((entry for entry in entries if entry.org_repo == org_repo), None)
    if own_entry is None:
        return
    source_folded = source_text.casefold()
    candidate_folded = candidate.casefold()
    for entry in entries:
        if entry.family == own_entry.family:
            continue
        family = entry.family.casefold()
        tokens = (f"aspose.{family}", f"aspose-{family}", f"@aspose/{family}")
        introduced = [
            token for token in tokens if token in candidate_folded and token not in source_folded
        ]
        if introduced:
            raise LLMError(
                f"trusted candidate introduced cross-product prose: {sorted(introduced)}"
            )
