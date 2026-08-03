"""Validate compiled repository-presentation documents against the structural contract."""

from __future__ import annotations

import re
import unicodedata

from markdown_it import MarkdownIt

from readme_agent.links.terminology import find_enterprise_terminology_findings
from readme_agent.presentation.template_schema import (
    PresentationTemplateInputV1,
    RepositoryPresentationTemplateV1,
    load_repository_presentation_template,
)
from readme_agent.readme.document_structure import github_anchor, parse_headings

_BADGE = re.compile(r"(?:!\[[^\]]+\]\([^)]+\)|\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\))")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_CODE_COMMENT = re.compile(r"(?m)^\s*(?:#(?!\s*\[)|//|/\*|\*|--)\s+\S")
_COPYRIGHT = re.compile(r"(?im)^\s*copyright(?:\s*©|\s+\(c\)|\s+\d{4})|©")
_MERMAID_NODE = re.compile(r'(?m)^\s*[A-Za-z][A-Za-z0-9_]*\["[^"]+"\]\s*$')
_ASPOSE_FOSS_PRODUCT = re.compile(r"\bAspose\.([A-Za-z0-9]+)\s+FOSS\b")


def _contains_emoji(text: str) -> bool:
    for character in text:
        codepoint = ord(character)
        if (
            0x1F000 <= codepoint <= 0x1FAFF
            or 0x2600 <= codepoint <= 0x27BF
            or unicodedata.category(character) == "So"
            and codepoint > 0x2300
        ):
            return True
    return False


def validate_repository_presentation(
    candidate: str,
    template_input: PresentationTemplateInputV1,
    *,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> list[str]:
    """Return deterministic contract violations; an empty list is acceptance."""

    contract = template or load_repository_presentation_template()
    errors: list[str] = []
    headings = parse_headings(candidate)
    h1s = [heading.title for heading in headings if heading.level == 1]
    h2s = [heading for heading in headings if heading.level == 2]
    title = " ".join(template_input.title.markdown.split())
    if h1s != [title]:
        errors.append("candidate must contain exactly one full-product-name H1")

    opening = candidate[: h2s[0].start] if h2s else candidate
    badge_lines = [line for line in opening.splitlines() if _BADGE.search(line)]
    if len(badge_lines) != contract.invariants.badge_rows:
        errors.append("candidate must contain exactly one opening badge row")
    elif len(_BADGE.findall(badge_lines[0])) < contract.invariants.minimum_badges:
        errors.append("candidate badge row has no applicable badge")
    elif badge_lines[0] != template_input.badges.markdown.strip():
        errors.append("candidate badge row differs from the bound applicable badge set")

    navigation = next(
        (heading for heading in h2s if heading.title.casefold() == "navigation"),
        None,
    )
    if navigation is None:
        errors.append("candidate is missing list navigation")
    else:
        body = candidate[navigation.heading_end : navigation.section_end]
        expected = {
            github_anchor(heading.title)
            for heading in h2s
            if heading.title.casefold() != "navigation"
        }
        linked = set(re.findall(r"(?m)^- \[[^\]]+\]\(#([^)]+)\)$", body))
        if linked != expected:
            errors.append("navigation must be a complete H2 link list")

    tokens = MarkdownIt("commonmark").parse(candidate)
    mermaid = [
        token.content for token in tokens if token.type == "fence" and token.info == "mermaid"
    ]
    if len(mermaid) != 1:
        errors.append("candidate must contain exactly one Mermaid diagram")
    else:
        source = mermaid[0]
        if title not in source:
            errors.append("Mermaid must use the complete product name")
        for label, minimum in (
            ("Inputs", contract.invariants.minimum_mermaid_inputs),
            ("Capabilities", contract.invariants.minimum_mermaid_capabilities),
            ("Outputs", contract.invariants.minimum_mermaid_outputs),
        ):
            match = re.search(
                rf'(?ms)subgraph\s+\w+\["[^"]*{label}[^"]*"\](.*?)^\s*end\s*$',
                source,
                re.IGNORECASE,
            )
            count = len(_MERMAID_NODE.findall(match.group(1))) if match else 0
            if count < minimum:
                errors.append(f"Mermaid requires at least {minimum} {label.casefold()} nodes")
        if "-->" in source:
            errors.append("Mermaid overview must not imply a mandatory directional workflow")

    if _HTML_COMMENT.search(candidate) or any(
        _CODE_COMMENT.search(token.content)
        for token in tokens
        if token.type in {"fence", "code_block"} and token.info != "mermaid"
    ):
        errors.append("candidate contains a visible or code comment")
    if _contains_emoji(candidate):
        errors.append("candidate contains emoji")
    if _COPYRIGHT.search(candidate):
        errors.append("candidate contains a default copyright declaration")
    own_families = {match.group(1).casefold() for match in _ASPOSE_FOSS_PRODUCT.finditer(title)}
    candidate_families = {
        match.group(1).casefold() for match in _ASPOSE_FOSS_PRODUCT.finditer(candidate)
    }
    if own_families and candidate_families - own_families:
        errors.append("candidate contains cross-product Aspose FOSS identity leakage")
    if find_enterprise_terminology_findings(candidate):
        errors.append("candidate contains noncanonical Aspose Enterprise Edition terminology")

    license_heading = next(
        (heading for heading in h2s if heading.title.casefold() == "license"),
        None,
    )
    license_body = (
        candidate[license_heading.heading_end : license_heading.section_end]
        if license_heading
        else ""
    )
    if not license_heading or not re.search(
        r"\[[^\]]*license[^\]]*\]\([^)]+\)",
        license_body,
        re.I,
    ):
        errors.append("License must be prose with a license link")
    if "permit" not in license_body.casefold():
        errors.append("License prose must summarize practical permission benefits")

    notices = next(
        (heading for heading in h2s if heading.title.casefold() == "third-party notices"),
        None,
    )
    if notices is not None:
        body = candidate[notices.heading_end : notices.section_end]
        if not re.search(r"\[[^\]]+\]\((?!https?://)[^)]+\)", body):
            errors.append("Third-party notices must link a repository-relative notice file")
    return errors
