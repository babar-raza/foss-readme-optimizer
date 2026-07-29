"""Validate an assembled trusted README against presentation contracts."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.registry.loader import load_products

_HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
_URL = re.compile(r"https?://[^\s<>)\"']+")
_PROHIBITED_ENTERPRISE_TERMS = re.compile(
    r"(?i)\b(?:commercial|on[- ]premise)\s+(?:product|edition)\b"
)
_FENCE = re.compile(r"(?m)^(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)$")
_CODE_COMMENT_BY_LANGUAGE: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"(?m)^\s*#(?![!]).*$"),
    "py": re.compile(r"(?m)^\s*#(?![!]).*$"),
    "java": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "c": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "cpp": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "csharp": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "cs": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "javascript": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "js": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "typescript": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "ts": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "go": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "rust": re.compile(r"(?m)^\s*(?://|/\*|\*).*$"),
    "bash": re.compile(r"(?m)^\s*#(?![!]).*$"),
    "sh": re.compile(r"(?m)^\s*#(?![!]).*$"),
    "shell": re.compile(r"(?m)^\s*#(?![!]).*$"),
    "powershell": re.compile(r"(?m)^\s*#(?![!]).*$"),
}


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
        labels = [
            str(item).casefold()
            for item in standards["readme.navigation"].parameters.get("required_labels", [])
        ]
        if not labels or any(label not in candidate.casefold() for label in labels):
            raise LLMError("configured README navigation is incomplete")
        _validate_navigation_targets(candidate)
    if "readme.at_a_glance_mermaid" in standards and candidate.count("```mermaid") != 1:
        raise LLMError("configured at-a-glance Mermaid diagram is absent or duplicated")
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


def _validate_contextual_links(
    source_text: str,
    candidate: str,
    standard,
    configured_standards: tuple,
) -> None:
    source_urls = {_clean_url(url) for url in _URL.findall(source_text)}
    candidate_urls = [_clean_url(url) for url in _URL.findall(candidate)]
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


def _validate_markdown(candidate: str) -> None:
    fences = list(_FENCE.finditer(candidate))
    if len(fences) % 2:
        raise LLMError("trusted composition candidate has an unclosed Markdown fence")
    for opening, closing in zip(fences[::2], fences[1::2], strict=True):
        if opening.group("marker")[0] != closing.group("marker")[0]:
            raise LLMError("trusted composition candidate has mismatched Markdown fences")
        language = opening.group("info").strip().split(maxsplit=1)[0].casefold()
        comment_pattern = _CODE_COMMENT_BY_LANGUAGE.get(language)
        body = candidate[opening.end() : closing.start()]
        if comment_pattern is not None and comment_pattern.search(body):
            raise LLMError("trusted composition candidate contains a code comment")
    MarkdownIt("commonmark", {"html": True}).parse(candidate)


def _github_slug(heading: str) -> str:
    normalized = re.sub(r"[^\w\- ]", "", heading.casefold(), flags=re.UNICODE)
    return re.sub(r"\s+", "-", normalized.strip())


def _validate_navigation_targets(candidate: str) -> None:
    targets = {
        _github_slug(match.group(2))
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
