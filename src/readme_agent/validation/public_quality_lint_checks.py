"""Presentation-lint adapters and malformed-prose checks for public README quality."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_structure import Heading
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import visible_lines
from readme_agent.validation.public_quality_contracts import (
    PublicQualityCategory,
    PublicQualityFindingV1,
    PublicQualityLocationV1,
    PublicQualitySpanV1,
    _location,
    _make_finding,
    _section_path,
)
from readme_agent.validation.public_quality_semantic_common import (
    _INFLECTION_SUFFIXES,
    _INLINE_CODE_SPAN,
    _PLACEHOLDER_BODY,
    _SAFE_DOUBLES,
    _URL,
    _WORD,
    _spans_overlap,
)

# ---------------------------------------------------------------------------------------------
# Reused-dependency wrappers (leakage / low-information prose) -- defended by
# test_reused_presentation_lint_rule_ids_still_exist
# ---------------------------------------------------------------------------------------------

_REUSED_LEAKAGE_RULE_IDS = frozenset(
    {
        "internal_assurance_commentary",
        "generic_preservation_heading",
        "api_reference_internal_assurance",
    }
)
_REUSED_MALFORMED_RULE_IDS = frozenset(
    {
        "semantic_duplicate",
        "api_reference_tautological_description",
        "api_reference_low_information_description",
        "api_reference_malformed_terminology",
    }
)


def _remap_presentation_finding(
    check_id: str,
    category: PublicQualityCategory,
    headings: list[Heading],
    finding: PresentationLintFindingV1,
) -> PublicQualityFindingV1:
    locations = tuple(
        PublicQualityLocationV1(
            section_path=_section_path(headings, span.start),
            span=PublicQualitySpanV1(start=span.start, end=span.end, text=span.text),
        )
        for span in finding.spans
    )
    blocking = finding.severity == "critical"
    return _make_finding(
        check_id,
        category,
        finding.severity,
        "exact_symbol",
        blocking,
        locations,
        message=finding.message,
        repair_target=f"{locations[0].section_path}: resolve {finding.rule_id}",
    )


def _check_process_leakage(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    result = lint_readme_presentation(text, facts)
    return [
        _remap_presentation_finding("process_leakage", "process_leakage", headings, finding)
        for finding in result.findings
        if finding.rule_id in _REUSED_LEAKAGE_RULE_IDS
    ]


def _check_malformed_low_information_prose(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    result = lint_readme_presentation(text, facts)
    return [
        _remap_presentation_finding(
            "malformed_low_information_prose", "malformed_prose", headings, finding
        )
        for finding in result.findings
        if finding.rule_id in _REUSED_MALFORMED_RULE_IDS
    ]


# ---------------------------------------------------------------------------------------------
# Net-new malformed-prose checks
# ---------------------------------------------------------------------------------------------


def _check_malformed_duplicate_language(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    findings: list[PublicQualityFindingV1] = []
    for line in visible_lines(text):
        protected = [match.span() for match in _INLINE_CODE_SPAN.finditer(line.text)]
        protected += [match.span() for match in _URL.finditer(line.text)]
        words = list(_WORD.finditer(line.text))
        for first, second in zip(words, words[1:], strict=False):
            gap = line.text[first.end() : second.start()]
            if gap.strip():
                continue  # not adjacent
            if _spans_overlap(first.start(), protected) or _spans_overlap(
                second.start(), protected
            ):
                continue
            first_word, second_word = first.group(0), second.group(0)
            first_lower, second_lower = first_word.lower(), second_word.lower()
            is_exact_duplicate = (
                first_lower == second_lower
                and len(first_lower) >= 4
                and first_lower not in _SAFE_DOUBLES
            )
            is_corrupted_inflection = len(first_lower) >= 4 and any(
                second_lower == first_lower + suffix for suffix in _INFLECTION_SUFFIXES
            )
            if not (is_exact_duplicate or is_corrupted_inflection):
                continue
            start = line.start + first.start()
            end = line.start + second.end()
            location = _location(headings, text, start, end)
            findings.append(
                _make_finding(
                    "malformed_duplicate_language",
                    "malformed_prose",
                    "critical",
                    "exact_symbol",
                    True,
                    (location,),
                    message=(
                        f"Adjacent duplicated or corrupted words: {first_word!r} {second_word!r}."
                    ),
                    repair_target=f"{location.section_path}: correct '{first_word} {second_word}'",
                )
            )
    return findings


def _is_leaf_heading(heading: Heading, headings: list[Heading]) -> bool:
    return not any(
        other is not heading and heading.heading_end <= other.start < heading.section_end
        for other in headings
    )


def _check_empty_or_placeholder_section(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    findings: list[PublicQualityFindingV1] = []
    for heading in headings:
        if not _is_leaf_heading(heading, headings):
            continue
        body = text[heading.heading_end : heading.section_end].strip()
        if body and not _PLACEHOLDER_BODY.match(body):
            continue
        location = _location(headings, text, heading.start, heading.heading_end)
        reason = "empty" if not body else f"placeholder text ({body!r})"
        findings.append(
            _make_finding(
                "empty_or_placeholder_section",
                "malformed_prose",
                "warning",
                "phrase_generic",
                False,
                (location,),
                message=f"Section {heading.title.strip()!r} has {reason} instead of real content.",
                repair_target=f"{location.section_path}: fill in real content or omit the section",
            )
        )
    return findings
