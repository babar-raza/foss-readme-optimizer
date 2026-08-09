"""Reject visitor-facing defects in rendered public API reference tables."""

from __future__ import annotations

import re

from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import (
    exact_span,
    line_span,
    make_finding,
    visible_lines,
)

RULE_IDS = (
    "api_reference_malformed_terminology",
    "api_reference_internal_assurance",
    "api_reference_low_information_description",
    "api_reference_namespace_branding",
    "api_reference_tautological_description",
)

_NAMESPACE_HEADING = re.compile(
    r"^### (?P<display>Aspose\.(?P<family>[A-Za-z][A-Za-z0-9]*)(?:\.[^\r\n]+)?) "
    r"Namespace \(`(?P<identifier>[^`]+)`\)\s*$"
)
_TABLE_ROW = re.compile(r"^\|\s*`[^`]+`\s*\|\s*(?P<description>.+?)\s*\|\s*$")
_INTERNAL_ASSURANCE = re.compile(
    r"(?i)(?:verified public type|verified public operation|exported by the .* namespace|"
    r"source revision|verification environment|inventory receipt)"
)
_TAUTOLOGICAL = re.compile(
    r"(?i)(?:public function for .+ operations|"
    r"provides the .+ operation in the public .+ api)\.?$"
)
_LOW_INFORMATION = re.compile(
    r"(?i)(?:(?::|supports)\s+[^.]{0,120}\b(?:add|all|as|ascend|do|from)\b"
    r"(?:\s*[,.;]|\s+and\s+)|\b(?:autoing|childs|checkboxs|encryptioning|ising|parseing|"
    r"toing)\b)"
)
_OPAQUE_MEMBER_COUNT = re.compile(r"(?i)\bincludes?\s+\d+\s+additional\s+members?\b")
_FRAGMENTARY_PROSE = re.compile(
    r"(?i)(?:\b(?:copying|moving|writing)\s+to\.?$|"
    r"\bdescendants cannot be moved\b|\blowercase ms one note\b|\bms one note\b)"
)
_MALFORMED_TERMINOLOGY = re.compile(
    r"(?i)(?:\ban AF RELATIONSHIPS\b|\bPDF\s+(?:a|ua)\b|\bAspose\s+PDF\b|"
    r"\b(?:Matrix|Point)\s*3\s+D\b|\bhasing\b|\ba XMP\b|\ban URI\b)"
)


def _api_bounds(text: str) -> tuple[int, int] | None:
    headings = parse_headings(text)
    api_heading = next(
        (
            heading
            for heading in headings
            if heading.level == 2 and heading.title.strip().casefold() == "api reference"
        ),
        None,
    )
    if api_heading is None:
        return None
    return api_heading.heading_end, api_heading.section_end


def lint_api_reference(text: str) -> list[PresentationLintFindingV1]:
    """Return exact-span defects within the public API reference section."""

    bounds = _api_bounds(text)
    if bounds is None:
        return []
    start, end = bounds
    findings: list[PresentationLintFindingV1] = []
    for line in visible_lines(text):
        if line.start < start or line.start >= end:
            continue
        heading = _NAMESPACE_HEADING.match(line.text)
        if heading and heading.group("family")[:1].islower():
            display_start = line.start + heading.start("display")
            findings.append(
                make_finding(
                    "api_reference_namespace_branding",
                    "Aspose namespace display headings must preserve the branded family casing.",
                    [
                        exact_span(
                            text,
                            display_start,
                            line.start + heading.end("display"),
                        )
                    ],
                )
            )
        row = _TABLE_ROW.match(line.text)
        if row is None:
            continue
        description = row.group("description")
        span = line_span(text, line)
        if _INTERNAL_ASSURANCE.search(description):
            findings.append(
                make_finding(
                    "api_reference_internal_assurance",
                    "API descriptions must explain visitor value, not internal verification state.",
                    [span],
                )
            )
        if _TAUTOLOGICAL.search(description):
            findings.append(
                make_finding(
                    "api_reference_tautological_description",
                    "API descriptions must explain a concrete role or behavior.",
                    [span],
                )
            )
        if _LOW_INFORMATION.search(description):
            findings.append(
                make_finding(
                    "api_reference_low_information_description",
                    "API descriptions must not expose isolated member-name fragments as prose.",
                    [span],
                )
            )
        if _OPAQUE_MEMBER_COUNT.search(description):
            findings.append(
                make_finding(
                    "api_reference_low_information_description",
                    "API tables must list public members instead of hiding them in a count.",
                    [span],
                )
            )
        if _FRAGMENTARY_PROSE.search(description):
            findings.append(
                make_finding(
                    "api_reference_low_information_description",
                    "API descriptions must use complete visitor-facing sentences.",
                    [span],
                )
            )
        if _MALFORMED_TERMINOLOGY.search(description):
            findings.append(
                make_finding(
                    "api_reference_malformed_terminology",
                    "API descriptions must preserve canonical brands, acronyms, and grammar.",
                    [span],
                )
            )
    return findings


__all__ = ["RULE_IDS", "lint_api_reference"]
