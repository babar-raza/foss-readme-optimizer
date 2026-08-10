"""Detect competing examples, broken navigation, and promotional imbalance."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.template_compiler import select_density_profile
from readme_agent.presentation.template_schema import load_repository_presentation_template
from readme_agent.readme.document_structure import (
    code_blocks_in_span,
    github_anchor,
    heading_identity,
    parse_headings,
)
from readme_agent.readme.opening_summary_fallback import verified_identity_opening_summary
from readme_agent.readme.presentation_contract import (
    PRESENTATION_SECTION_VISIBLE_LIMITS_BY_HEADING,
)
from readme_agent.readme.presentation_lint_models import (
    PresentationLintFindingV1,
    PresentationLintSpanV1,
)
from readme_agent.readme.presentation_lint_text import (
    exact_span,
    line_span,
    make_finding,
    visible_lines,
)
from readme_agent.readme.presentation_report import product_explanation_offset

RULE_IDS = (
    "competing_primary_examples",
    "invalid_third_party_notices",
    "malformed_navigation",
    "promotional_imbalance",
    "promotional_opening",
    "redundant_quick_links",
    "section_brief_overflow",
    "section_details_multiplicity",
    "uncollapsed_secondary_detail",
    "unnormalized_blank_lines",
)

_PRIMARY_EXAMPLE = re.compile(r"(?i)^(?:quick start|usage|getting started|example)$")
_LOCAL_LINK = re.compile(r"\[[^\]]+\]\(#([^)]+)\)")
_COMMERCIAL_LINK = re.compile(r"https?://[^)\s]*aspose\.com(?:/[^)\s]*)?", re.IGNORECASE)
_PROMO_HEADING = re.compile(r"(?i)(?:enterprise edition|aspose\.com)")
_PROMO_CTA = re.compile(r"(?i)\b(?:buy|upgrade now|free trial|download)\b")
_PROMOTIONAL_OPENING = re.compile(
    r"(?i)\b(?:official\s+Aspose\s+project|100\s*%\s+free(?:\s*&\s*open[- ]source)?)\b"
)
_QUICK_LINKS = re.compile(r"(?i)^\s*Quick links\s*:")
_THIRD_PARTY_LINK = re.compile(
    r"\[[^\]]*(?:third[- ]party|THIRD_PARTY_NOTICES)[^\]]*\]\((?P<target>[^)]+)\)",
    re.IGNORECASE,
)


def _heading_span(text: str, start: int, heading_end: int):
    newline = text.find("\n", start, heading_end)
    return exact_span(text, start, newline if newline >= 0 else heading_end)


def _accepted_purpose_exists(facts: ProductFactsV2) -> bool:
    for field in ("product.problems_solved", "product.capabilities", "product.formats"):
        fact_id = facts.selected_fact_ids.get(field)
        if fact_id is None:
            continue
        fact = facts.fact_by_id(fact_id)
        if (
            fact.verification_state in {"verified", "policy_approved"}
            and not fact.has_unresolved_conflict
        ):
            return True
    return False


def _identity_only_explanation_offset(text: str, facts: ProductFactsV2 | None) -> int | None:
    """Recognize the exact fact-derived opening when richer purpose evidence is absent."""

    if facts is None or _accepted_purpose_exists(facts):
        return None
    fallback = verified_identity_opening_summary(facts)
    if fallback is None:
        return None
    offset = text.find(fallback.text)
    if offset < 0:
        return None
    first_h2 = next((heading for heading in parse_headings(text) if heading.level == 2), None)
    if first_h2 is not None and offset >= first_h2.start:
        return None
    return offset


def lint_structure(
    text: str,
    facts: ProductFactsV2 | None = None,
) -> list[PresentationLintFindingV1]:
    findings: list[PresentationLintFindingV1] = []
    headings = parse_headings(text)
    h1 = next((heading for heading in headings if heading.level == 1), None)
    first_h2 = next((heading for heading in headings if heading.level == 2), None)
    opening_start = h1.heading_end if h1 is not None else 0
    opening_end = first_h2.start if first_h2 is not None else len(text)
    opening_lines = [
        line for line in visible_lines(text) if opening_start <= line.start < opening_end
    ]
    promotional_opening = [
        line_span(text, line) for line in opening_lines if _PROMOTIONAL_OPENING.search(line.text)
    ]
    if promotional_opening:
        findings.append(
            make_finding(
                "promotional_opening",
                "The opening must be one factual product summary without promotional claims.",
                promotional_opening,
            )
        )
    quick_links = [
        line_span(text, line) for line in opening_lines if _QUICK_LINKS.search(line.text)
    ]
    if quick_links:
        findings.append(
            make_finding(
                "redundant_quick_links",
                "Opening quick-link shells duplicate the complete Navigation section.",
                quick_links,
            )
        )

    for heading in headings:
        if _PRIMARY_EXAMPLE.fullmatch(heading.title.strip()):
            blocks = code_blocks_in_span(text, heading.start, heading.section_end)
            if len(blocks) > 1:
                labels = [
                    line_span(text[heading.start : heading.section_end], line)
                    for line in visible_lines(text[heading.start : heading.section_end])
                    if line.text.rstrip().endswith(":") and not line.text.lstrip().startswith("#")
                ]
                labels = [
                    span.model_copy(
                        update={
                            "start": span.start + heading.start,
                            "end": span.end + heading.start,
                        }
                    )
                    for span in labels
                ]
                findings.append(
                    make_finding(
                        "competing_primary_examples",
                        "Multiple full workflows compete inside the primary example section.",
                        [_heading_span(text, heading.start, heading.heading_end), *labels],
                    )
                )

    contract = load_repository_presentation_template()
    profile = select_density_profile(len(text.splitlines()), template=contract)
    collapsed_slots = set(contract.profiles[profile].collapse_slots)
    for heading in headings:
        if heading.level != 2:
            continue
        normalized = heading.title.strip().casefold()
        slot = (
            "additional_examples"
            if "example" in normalized and "quick" not in normalized
            else "api_reference"
            if "api" in normalized
            else "development_and_testing"
            if any(token in normalized for token in ("development", "testing", "workflow"))
            else None
        )
        body = text[heading.heading_end : heading.section_end]
        if (
            slot in collapsed_slots
            and sum(bool(line.strip()) for line in body.splitlines()) >= 12
            and "<details>" not in body.casefold()
        ):
            findings.append(
                make_finding(
                    "uncollapsed_secondary_detail",
                    "Long secondary examples, API detail, and development workflows must collapse.",
                    [_heading_span(text, heading.start, heading.heading_end)],
                )
            )

    notice_links = list(_THIRD_PARTY_LINK.finditer(text))
    notices_heading = next(
        (
            heading
            for heading in headings
            if heading.level == 2 and heading.title.strip().casefold() == "third-party notices"
        ),
        None,
    )
    invalid_notice_spans: list[PresentationLintSpanV1] = []
    if notice_links and notices_heading is None:
        invalid_notice_spans.extend(
            exact_span(text, match.start(), match.end()) for match in notice_links
        )
    elif notices_heading is not None:
        for match in notice_links:
            if (
                notices_heading.heading_end <= match.start() < notices_heading.section_end
                and match.group("target").casefold().startswith(("http://", "https://"))
            ):
                invalid_notice_spans.append(exact_span(text, match.start(), match.end()))
    if invalid_notice_spans:
        findings.append(
            make_finding(
                "invalid_third_party_notices",
                "Third-party notices require a dedicated H2 and repository-relative link.",
                invalid_notice_spans,
            )
        )

    anchors = {github_anchor(heading.title) for heading in headings}
    broken = []
    for line in visible_lines(text):
        if any(
            match.group(1).casefold() not in anchors for match in _LOCAL_LINK.finditer(line.text)
        ):
            broken.append(line_span(text, line))
    if broken:
        findings.append(
            make_finding(
                "malformed_navigation",
                "One or more README navigation links do not resolve to a heading.",
                broken,
            )
        )

    limits_by_identity = {
        heading_identity(title): limit
        for title, limit in PRESENTATION_SECTION_VISIBLE_LIMITS_BY_HEADING.items()
    }
    for heading in headings:
        if heading.level != 2:
            continue
        limit = limits_by_identity.get(heading_identity(heading.title))
        if limit is None:
            continue
        body = text[heading.heading_end : heading.section_end]
        details_count = len(re.findall(r"(?i)<details(?:\s|>)", body))
        if details_count > 1:
            findings.append(
                make_finding(
                    "section_details_multiplicity",
                    f"{heading.title} must fold detail into at most one details block.",
                    [_heading_span(text, heading.start, heading.heading_end)],
                )
            )
        brief_end = heading.heading_end + len(body.partition("<details>")[0])
        overflow = [
            line_span(text, line)
            for line in visible_lines(text)
            if heading.heading_end <= line.start < brief_end and line.text.strip()
        ][limit:]
        if overflow:
            findings.append(
                make_finding(
                    "section_brief_overflow",
                    (
                        f"{heading.title} must show at most {limit} always-visible "
                        "lines before one details block."
                    ),
                    overflow,
                )
            )

    blank_run_anchors: list[PresentationLintSpanV1] = []
    fenced = False
    consecutive_blank = 0
    last_content: tuple[int, int] | None = None
    offset = 0
    for raw in text.splitlines(keepends=True):
        content = raw.rstrip("\r\n")
        if content.lstrip().startswith("```"):
            fenced = not fenced
            consecutive_blank = 0
            last_content = (offset, offset + len(content))
        elif fenced or content.strip():
            consecutive_blank = 0
            last_content = (offset, offset + len(content))
        else:
            consecutive_blank += 1
            if consecutive_blank == 2 and last_content is not None:
                blank_run_anchors.append(exact_span(text, *last_content))
        offset += len(raw)
    if blank_run_anchors:
        unique_anchors = {(span.start, span.end): span for span in blank_run_anchors}
        findings.append(
            make_finding(
                "unnormalized_blank_lines",
                "Consecutive blank lines must be collapsed to a single separator.",
                list(unique_anchors.values()),
            )
        )

    explanation = product_explanation_offset(text)
    if explanation is None:
        explanation = _identity_only_explanation_offset(text, facts)
    promotional = []
    for line in visible_lines(text):
        commercial = _COMMERCIAL_LINK.search(line.text)
        if commercial and (explanation is None or line.start < explanation):
            promotional.append(line_span(text, line))
        elif _PROMO_CTA.search(line.text) and (commercial or "Enterprise Edition" in line.text):
            promotional.append(line_span(text, line))
    for heading in headings:
        if not _PROMO_HEADING.search(heading.title):
            continue
        section = text[heading.start : heading.section_end]
        if len(_COMMERCIAL_LINK.findall(section)) >= 2 or _PROMO_CTA.search(section):
            promotional.append(_heading_span(text, heading.start, heading.heading_end))
            promotional.extend(
                span.model_copy(
                    update={
                        "start": span.start + heading.start,
                        "end": span.end + heading.start,
                    }
                )
                for line in visible_lines(section)
                if (_COMMERCIAL_LINK.search(line.text) or _PROMO_CTA.search(line.text))
                for span in [line_span(section, line)]
            )
    if promotional:
        unique = {(span.start, span.end): span for span in promotional}
        findings.append(
            make_finding(
                "promotional_imbalance",
                "Commercial calls to action precede or outweigh contextual product guidance.",
                list(unique.values()),
            )
        )
    return findings
