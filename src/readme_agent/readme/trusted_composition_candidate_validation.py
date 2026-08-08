"""Validate an assembled trusted README against presentation contracts."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

from readme_agent.errors import LLMError
from readme_agent.facts.example_quality import source_contains_comments, strip_source_comments
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.document_structure import (
    github_anchor,
    introduced_duplicate_headings,
    normalize_navigation_targets,
    normalized_heading_counts,
    remove_excess_headings,
    remove_redundant_nested_headings,
)
from readme_agent.readme.trusted_candidate_terminology import (
    contains_prohibited_enterprise_terminology,
    normalize_enterprise_edition_terminology,
    unlink_duplicate_opening_promotional_links,
    unnamed_enterprise_product_references,
)
from readme_agent.readme.trusted_code_provenance import (
    validate_trusted_code_block_provenance,
)
from readme_agent.readme.trusted_portfolio_brand import (
    normalize_trusted_enterprise_product_links,
    normalize_trusted_key_capabilities,
    normalize_trusted_portfolio_emojis,
    normalize_trusted_portfolio_header_assets,
    normalize_trusted_portfolio_headings,
    normalize_trusted_portfolio_mermaid,
    validate_trusted_portfolio_brand,
)
from readme_agent.registry.loader import load_products

TRUSTED_CANDIDATE_NORMALIZATION_VERSION = "trusted-candidate-normalization-v32-code-provenance"

_HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
_URL = re.compile(r"https?://[^\s<>)\"']+")
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
        for match in _URL.finditer(markdown)
        if _belongs_to(match.group(0), "aspose.org") or _belongs_to(match.group(0), "aspose.com")
    ]
    occurrences: dict[str, int] = {}
    ranked: list[tuple[tuple[int, int, int, int], int, re.Match[str]]] = []
    surface_order = {"products": 0, "docs": 1, "kb": 2, "reference": 3, "blog": 4}
    for index, match in enumerate(matches):
        url = _clean_url(match.group(0))
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
        url = match.group(0)
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
    links = list(_MARKDOWN_LINK.finditer(markdown))
    edits: dict[tuple[int, int], str] = {}
    for index, match in enumerate(matches):
        if index in retained:
            continue
        enclosing = next(
            (link for link in links if link.start() <= match.start() and match.end() <= link.end()),
            None,
        )
        if enclosing is not None:
            edits[(enclosing.start(), enclosing.end())] = enclosing.group("label")
            continue
        line_start = markdown.rfind("\n", 0, match.start()) + 1
        line_end = markdown.find("\n", match.end())
        line_end = len(markdown) if line_end < 0 else line_end + 1
        line = markdown[line_start:line_end]
        without_url = line[: match.start() - line_start] + line[match.end() - line_start :]
        if re.fullmatch(
            r"[ \t]*(?:[-*+][ \t]+)?"
            r"(?:documentation|docs|product|enterprise edition)"
            r"[ \t]*:?[ \t]*[.,;:]?[ \t]*(?:\r?\n)?",
            without_url,
            flags=re.IGNORECASE,
        ):
            edits[(line_start, line_end)] = ""
        else:
            edits[(match.start(), match.end())] = ""
    normalized = markdown
    for (start, end), replacement in sorted(edits.items(), reverse=True):
        normalized = normalized[:start] + replacement + normalized[end:]
    return normalized


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
        normalize_trusted_portfolio_mermaid(
            normalize_trusted_portfolio_headings(
                normalize_enterprise_edition_terminology(
                    strip_readme_comments(normalize_inherited_code_blocks(markdown, graph))
                ),
                graph,
            ),
            graph,
        ),
        graph,
        navigation_boundary_prefix=navigation_boundary_prefix,
    )
    structured = normalize_trusted_key_capabilities(
        normalize_trusted_portfolio_header_assets(structured, graph),
        graph,
    )
    # Section-owned normalizers may materialize historical sentence-case
    # labels. Re-apply the configured public heading contract at the final
    # structural boundary so validation observes the actual visitor standard.
    structured = normalize_trusted_portfolio_headings(structured, graph)
    structured = normalize_trusted_portfolio_emojis(structured, graph)
    structured = unlink_duplicate_opening_promotional_links(structured)
    source_headings = _heading_counts("\n\n".join(fact.value for fact in graph.inherited_facts))
    allowed_counts = {
        (int(tag.removeprefix("h")), title): count
        for (tag, title), count in source_headings.items()
    }
    return normalize_trusted_enterprise_product_links(
        normalize_contextual_link_budget(
            normalize_promotional_blockquotes(
                normalize_navigation_targets(
                    remove_redundant_nested_headings(
                        remove_excess_headings(structured, allowed_counts)
                    ),
                    boundary_line_prefix=navigation_boundary_prefix,
                ),
                graph,
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
    """Restore curated code by unique content similarity while removing its comments."""

    source_blocks: list[str] = []
    for fact in graph.inherited_facts:
        if fact.material_kind != "code":
            continue
        spans = _non_mermaid_fenced_spans(fact.value)
        source_blocks.extend(strip_readme_comments(fact.value[start:end]) for start, end in spans)
    candidate_spans = _non_mermaid_fenced_spans(markdown)
    if not source_blocks or not candidate_spans:
        return markdown
    candidate_sections = [
        _code_section_key(_h2_section_at(markdown, start) or "") for start, _ in candidate_spans
    ]
    source_sections = [
        _code_section_key(" ".join(fact.heading_path))
        for fact in graph.inherited_facts
        if fact.material_kind == "code"
        for _ in _non_mermaid_fenced_spans(fact.value)
    ]
    replacements: dict[tuple[int, int], str] = {}
    used_source: set[int] = set()
    used_candidate: set[int] = set()
    candidate_blocks = [markdown[start:end] for start, end in candidate_spans]
    for source_index, source_block in enumerate(source_blocks):
        available = [
            candidate_index
            for candidate_index in range(len(candidate_blocks))
            if candidate_index not in used_candidate
        ]
        same_section = [
            candidate_index
            for candidate_index in available
            if candidate_sections[candidate_index] == source_sections[source_index]
        ]
        candidate_pool = same_section or available
        ranked = sorted(
            (
                (
                    SequenceMatcher(
                        None,
                        _canonical_code_block(source_block),
                        _canonical_code_block(candidate_block),
                        autojunk=False,
                    ).ratio(),
                    candidate_index,
                )
                for candidate_index in candidate_pool
                for candidate_block in (candidate_blocks[candidate_index],)
            ),
            reverse=True,
        )
        if not ranked:
            break
        best_score, candidate_index = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score < 0.72 or (best_score < 0.98 and best_score - runner_up < 0.08):
            continue
        replacements[candidate_spans[candidate_index]] = source_block
        used_source.add(source_index)
        used_candidate.add(candidate_index)
    for section_key in ("installation", "quick start"):
        source_indexes = [
            index
            for index, source_section in enumerate(source_sections)
            if source_section == section_key and index not in used_source
        ]
        candidate_indexes = [
            index
            for index, candidate_section in enumerate(candidate_sections)
            if candidate_section == section_key and index not in used_candidate
        ]
        if len(source_indexes) != 1 or len(candidate_indexes) != 1:
            continue
        source_index = source_indexes[0]
        candidate_index = candidate_indexes[0]
        replacements[candidate_spans[candidate_index]] = source_blocks[source_index]
        used_source.add(source_index)
        used_candidate.add(candidate_index)
    remaining_source = [index for index in range(len(source_blocks)) if index not in used_source]
    remaining_candidate = [
        index for index in range(len(candidate_blocks)) if index not in used_candidate
    ]
    if (
        remaining_source
        and len(remaining_source) == len(remaining_candidate)
        and all(source_sections[index] is None for index in remaining_source)
        and all(candidate_sections[index] is None for index in remaining_candidate)
    ):
        for source_index, candidate_index in zip(
            remaining_source,
            remaining_candidate,
            strict=True,
        ):
            replacements[candidate_spans[candidate_index]] = source_blocks[source_index]
    normalized = markdown
    for (start, end), source_block in sorted(replacements.items(), reverse=True):
        normalized = normalized[:start] + source_block + normalized[end:]
    return normalized


def _canonical_code_block(block: str) -> str:
    return re.sub(r"\s+", "", block).casefold()


def _code_section_key(heading: str) -> str | None:
    normalized = heading.casefold()
    if "installation" in normalized or normalized.strip() == "install":
        return "installation"
    if "quick start" in normalized or "getting started" in normalized:
        return "quick start"
    return None


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
    validate_trusted_code_block_provenance(source_text, candidate)
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
        if contains_prohibited_enterprise_terminology(candidate):
            raise LLMError("trusted candidate uses prohibited Enterprise Edition terminology")
        if unnamed_enterprise_product_references(candidate):
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
    validate_trusted_portfolio_brand(candidate, graph)


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
    prefix = markdown[:offset]
    fence_offsets = [match.start() for match in _FENCE.finditer(prefix)]
    headings = [
        heading
        for heading in re.finditer(r"(?m)^##[ \t]+(.+?)\s*$", prefix)
        if sum(fence < heading.start() for fence in fence_offsets) % 2 == 0
    ]
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


def _heading_counts(markdown: str) -> dict[tuple[str, str], int]:
    return {
        (f"h{level}", title): count
        for (level, title), count in normalized_heading_counts(markdown).items()
    }


def _validate_no_introduced_duplicate_headings(source_text: str, candidate: str) -> None:
    introduced = introduced_duplicate_headings(source_text, candidate)
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
