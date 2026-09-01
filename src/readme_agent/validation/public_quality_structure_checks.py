"""Relative structural-quality checks for public README candidates."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_structure import Heading
from readme_agent.validation.public_quality_contracts import (
    PublicQualityFindingV1,
    _location,
    _make_finding,
)
from readme_agent.validation.public_quality_semantic_common import _IDENTIFIER_TOKEN, _WORD

_COUNTED_LIST_CLAIM = re.compile(
    r"\b(?:the\s+following\s+)?(?P<count>\d+)\s+"
    r"(?P<kind>capabilities|features|formats|examples|operations|outputs|inputs|packages)\b",
    re.IGNORECASE,
)
_LIST_ITEM = re.compile(r"^[ \t]{0,3}(?:[-+*]|\d+[.)])[ \t]+\S", re.MULTILINE)
_API_TABLE_SUMMARY = re.compile(
    r"The package (?P<verb>reference presents|documents) (?P<count>\d+) "
    r"(?P<kind>API table entries|public types) across (?P<namespaces>\d+) namespaces\.",
    re.IGNORECASE,
)
_API_TABLE_ROW = re.compile(r"(?m)^\| `[^`]+` \| [^|]+ \|$")
_API_NAMESPACE_HEADING = re.compile(r"(?m)^### [^\r\n]+ Namespace \(`[^`]+`\)\s*$")
# Scopes row-counting to the generated `| Type | Description |` table immediately under each
# namespace heading -- source-preserved content elsewhere in the same section (e.g. a repository's
# own pre-existing `| Class | Description |` method index) can share the same `| \`X\` | text |`
# row shape and must not be counted as part of the declared namespace summary.
_NAMESPACE_TABLE_BLOCK = re.compile(
    r"(?m)^### [^\r\n]+ Namespace \(`[^`]+`\)\s*\n\n\| Type \| Description \|\n\| --- \| --- \|\n"
    r"(?P<rows>(?:\| `[^`]+` \| [^|]+ \|\n?)*)"
)

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


def _check_numeric_list_consistency(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    """Reject an explicit item count when its immediately following list disagrees.

    The check is intentionally narrow: it does not infer counts from arbitrary prose. It only
    evaluates an explicit ``N capabilities/features/...`` claim followed, before any intervening
    paragraph or heading, by one Markdown list. This makes the signal deterministic and avoids
    treating version numbers, format names, or unrelated lists as count promises.
    """

    findings: list[PublicQualityFindingV1] = []
    for match in _COUNTED_LIST_CLAIM.finditer(text):
        claim_line_end = text.find("\n", match.end())
        if claim_line_end < 0:
            continue
        tail_start = claim_line_end + 1
        tail = text[tail_start:]
        lines = tail.splitlines(keepends=True)
        list_lines: list[tuple[int, str]] = []
        offset = tail_start
        list_started = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if list_started:
                    break
                offset += len(line)
                continue
            if stripped.startswith("#") or stripped.startswith("```"):
                break
            if _LIST_ITEM.match(line):
                list_started = True
                list_lines.append((offset, line))
                offset += len(line)
                continue
            break
        if not list_lines:
            continue
        expected = int(match.group("count"))
        actual = len(list_lines)
        if expected == actual:
            continue
        claim_location = _location(headings, text, match.start(), match.end())
        first_offset, first_line = list_lines[0]
        list_location = _location(
            headings,
            text,
            first_offset,
            first_offset + len(first_line.rstrip("\r\n")),
        )
        findings.append(
            _make_finding(
                "numeric_list_consistency",
                "structural_quality",
                "critical",
                "exact_symbol",
                True,
                (claim_location, list_location),
                message=(
                    f"The public count promises {expected} {match.group('kind').lower()}, "
                    f"but the immediately following Markdown list contains {actual}."
                ),
                repair_target=(
                    f"{claim_location.section_path}: align the explicit count with the list"
                ),
            )
        )
    api_reference = next(
        (heading for heading in headings if heading.title.casefold() == "api reference"),
        None,
    )
    if api_reference is None:
        return findings
    api_body = text[api_reference.heading_end : api_reference.section_end]
    metric = _API_TABLE_SUMMARY.search(api_body)
    if metric is None:
        return findings
    actual_entries = sum(
        len(_API_TABLE_ROW.findall(block.group("rows")))
        for block in _NAMESPACE_TABLE_BLOCK.finditer(api_body)
    )
    actual_namespaces = len(_API_NAMESPACE_HEADING.findall(api_body))
    declared_entries = int(metric.group("count"))
    declared_namespaces = int(metric.group("namespaces"))
    mislabeled = metric.group("kind").casefold() != "api table entries"
    mismatched = declared_entries != actual_entries or declared_namespaces != actual_namespaces
    if not mislabeled and not mismatched:
        return findings
    metric_start = api_reference.heading_end + metric.start()
    metric_location = _location(
        headings,
        text,
        metric_start,
        api_reference.heading_end + metric.end(),
    )
    reasons: list[str] = []
    if mislabeled:
        reasons.append("table rows are labelled as distinct public types")
    if mismatched:
        reasons.append(
            f"declared {declared_entries}/{declared_namespaces} but rendered "
            f"{actual_entries}/{actual_namespaces} entries/namespaces"
        )
    findings.append(
        _make_finding(
            "numeric_list_consistency",
            "structural_quality",
            "critical",
            "exact_symbol",
            True,
            (metric_location,),
            message="API reference summary is inconsistent: " + "; ".join(reasons) + ".",
            repair_target=(
                f"{metric_location.section_path}: label and count the rendered API table exactly"
            ),
        )
    )
    return findings
