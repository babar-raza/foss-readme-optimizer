"""Relative structural-quality checks for public README candidates."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_structure import Heading
from readme_agent.validation.public_quality_contracts import (
    PublicQualityFindingV1,
    _location,
    _make_finding,
)
from readme_agent.validation.public_quality_semantic_common import _IDENTIFIER_TOKEN, _WORD

# ---------------------------------------------------------------------------------------------
# Structural quality (always advisory) -- relative outliers, never a fixed length limit
# ---------------------------------------------------------------------------------------------


def _h2_sections(headings: list[Heading]) -> list[Heading]:
    return [heading for heading in headings if heading.level == 2]


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _check_structural_size_outlier(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    sections = _h2_sections(headings)
    if len(sections) < 3:
        return []
    counts = [
        (heading, len(_WORD.findall(text[heading.heading_end : heading.section_end])))
        for heading in sections
    ]
    nonzero = [count for _, count in counts if count > 0]
    if len(nonzero) < 3:
        return []
    median = _median([float(count) for count in nonzero])
    if median <= 0:
        return []
    findings: list[PublicQualityFindingV1] = []
    for heading, count in counts:
        if count == 0:
            continue  # empty sections are reported by empty_or_placeholder_section
        ratio = count / median
        if 0.25 <= ratio <= 4:
            continue
        location = _location(headings, text, heading.start, heading.heading_end)
        findings.append(
            _make_finding(
                "structural_size_outlier",
                "structural_quality",
                "warning",
                "phrase_generic",
                False,
                (location,),
                message=(
                    f"Section {heading.title.strip()!r} is {count} words "
                    f"({ratio:.1f}x the sibling median of {median:.0f})."
                ),
                repair_target=f"{location.section_path}: rebalance section length vs. siblings",
            )
        )
    return findings


def _check_structural_detail_density(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    sections = _h2_sections(headings)
    if len(sections) < 3:
        return []
    densities = []
    for heading in sections:
        body = text[heading.heading_end : heading.section_end]
        word_count = len(_WORD.findall(body)) or 1
        identifier_count = len(_IDENTIFIER_TOKEN.findall(body))
        densities.append((heading, identifier_count / word_count))
    nonzero = [density for _, density in densities if density > 0]
    if len(nonzero) < 3:
        return []
    median = _median(nonzero)
    if median <= 0:
        return []
    findings: list[PublicQualityFindingV1] = []
    for heading, density in densities:
        if density == 0:
            continue
        ratio = density / median
        if ratio <= 4:
            continue
        location = _location(headings, text, heading.start, heading.heading_end)
        findings.append(
            _make_finding(
                "structural_detail_density",
                "structural_quality",
                "warning",
                "phrase_generic",
                False,
                (location,),
                message=(
                    f"Section {heading.title.strip()!r} has a raw-identifier density "
                    f"{ratio:.1f}x the sibling median."
                ),
                repair_target=(
                    f"{location.section_path}: explain identifiers in visitor-facing prose"
                ),
            )
        )
    return findings
