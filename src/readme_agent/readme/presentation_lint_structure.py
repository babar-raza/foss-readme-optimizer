"""Detect competing examples, broken navigation, and promotional imbalance."""

from __future__ import annotations

import re

from readme_agent.readme.document_structure import (
    code_blocks_in_span,
    github_anchor,
    parse_headings,
)
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import (
    exact_span,
    line_span,
    make_finding,
    visible_lines,
)
from readme_agent.readme.presentation_report import product_explanation_offset

RULE_IDS = (
    "competing_primary_examples",
    "malformed_navigation",
    "promotional_imbalance",
)

_PRIMARY_EXAMPLE = re.compile(r"(?i)^(?:quick start|usage|getting started|example)$")
_LOCAL_LINK = re.compile(r"\[[^\]]+\]\(#([^)]+)\)")
_COMMERCIAL_LINK = re.compile(r"https?://[^)\s]*aspose\.com(?:/[^)\s]*)?", re.IGNORECASE)
_PROMO_HEADING = re.compile(r"(?i)(?:enterprise edition|aspose\.com)")
_PROMO_CTA = re.compile(r"(?i)\b(?:buy|upgrade now|free trial|download)\b")


def _heading_span(text: str, start: int, heading_end: int):
    newline = text.find("\n", start, heading_end)
    return exact_span(text, start, newline if newline >= 0 else heading_end)


def lint_structure(text: str) -> list[PresentationLintFindingV1]:
    findings: list[PresentationLintFindingV1] = []
    headings = parse_headings(text)

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

    explanation = product_explanation_offset(text)
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
