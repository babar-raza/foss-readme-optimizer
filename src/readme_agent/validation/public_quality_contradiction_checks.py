"""Symbol- and phrase-level contradiction checks for public README prose."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.capability_semantics import (
    identifier_discriminators,
    same_public_capability,
)
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_structure import Heading
from readme_agent.readme.presentation_lint_text import VisibleLine, visible_lines
from readme_agent.validation.public_quality_contracts import (
    PublicQualityFindingV1,
    _location,
    _make_finding,
)
from readme_agent.validation.public_quality_semantic_common import (
    _BACKTICK_SYMBOL,
    _CONDITIONAL_MARKER,
    _NEGATIVE_CUE,
    _POSITIVE_CUE,
    _SCOPE_QUALIFIER,
    _direction,
    _excepted_discriminators,
    _opposite_direction,
)

# ---------------------------------------------------------------------------------------------
# Tier B -- exact code-symbol contradiction in prose
# ---------------------------------------------------------------------------------------------


def _check_contradiction_capability_symbol(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    positive: dict[str, list[VisibleLine]] = {}
    negative: dict[str, list[VisibleLine]] = {}
    for line in visible_lines(text):
        symbols = {match.group(1) for match in _BACKTICK_SYMBOL.finditer(line.text)}
        if not symbols:
            continue
        if _NEGATIVE_CUE.search(line.text):
            for symbol in symbols:
                negative.setdefault(symbol, []).append(line)
        elif _POSITIVE_CUE.search(line.text):
            for symbol in symbols:
                positive.setdefault(symbol, []).append(line)
    findings: list[PublicQualityFindingV1] = []
    for symbol in sorted(set(positive) & set(negative)):
        for positive_line in positive[symbol]:
            for negative_line in negative[symbol]:
                if _SCOPE_QUALIFIER.search(negative_line.text) and not _SCOPE_QUALIFIER.search(
                    positive_line.text
                ):
                    continue
                if _CONDITIONAL_MARKER.search(positive_line.text) or _CONDITIONAL_MARKER.search(
                    negative_line.text
                ):
                    continue  # branching "if X is installed/available" prose, not a firm claim
                locations = (
                    _location(headings, text, positive_line.start, positive_line.end),
                    _location(headings, text, negative_line.start, negative_line.end),
                )
                findings.append(
                    _make_finding(
                        "contradiction_capability_symbol",
                        "cross_section_contradiction",
                        "critical",
                        "exact_symbol",
                        True,
                        locations,
                        subject=symbol,
                        polarity="explicit_constraint",
                        message=(
                            f"`{symbol}` is described as available in one section and explicitly "
                            "unsupported or unimplemented in another."
                        ),
                        repair_target=(
                            f"{locations[1].section_path}: reconcile `{symbol}` status with "
                            f"{locations[0].section_path}"
                        ),
                    )
                )
    return findings


# ---------------------------------------------------------------------------------------------
# Tier C -- phrase-level contradiction, no shared code symbol
# ---------------------------------------------------------------------------------------------


def _check_contradiction_capability_phrase(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    positive_lines: list[VisibleLine] = []
    negative_lines: list[VisibleLine] = []
    for line in visible_lines(text):
        if _BACKTICK_SYMBOL.search(line.text):
            continue  # handled at higher confidence by the symbol-level tier
        if _NEGATIVE_CUE.search(line.text):
            negative_lines.append(line)
        elif _POSITIVE_CUE.search(line.text):
            positive_lines.append(line)
    findings: list[PublicQualityFindingV1] = []
    for positive_line in positive_lines:
        for negative_line in negative_lines:
            if _opposite_direction(positive_line.text, negative_line.text):
                continue  # import vs. export (etc.) are different operations, not a contradiction
            if _SCOPE_QUALIFIER.search(negative_line.text) and not _SCOPE_QUALIFIER.search(
                positive_line.text
            ):
                continue
            if _CONDITIONAL_MARKER.search(positive_line.text) or _CONDITIONAL_MARKER.search(
                negative_line.text
            ):
                continue  # branching "if X is installed/available" prose, not a firm claim
            positive_discriminators = identifier_discriminators(positive_line.text)
            negative_discriminators = identifier_discriminators(negative_line.text)
            excepted = _excepted_discriminators(negative_line.text)
            if positive_discriminators & excepted:
                continue  # e.g. "other than PDF" explicitly exempts PDF from this limitation
            shared = positive_discriminators & (negative_discriminators - excepted)
            shared = frozenset(
                token
                for token in shared
                if re.search(rf"(?i)\bnon[- ]?{re.escape(token)}\b", negative_line.text) is None
            )
            same_capability = same_public_capability(positive_line.text, negative_line.text)
            positive_direction = _direction(positive_line.text)
            negative_direction = _direction(negative_line.text)
            same_direction = (
                positive_direction is not None and positive_direction == negative_direction
            )
            if shared and (same_capability or same_direction):
                blocking = True
            elif same_capability:
                blocking = False
            else:
                continue
            locations = (
                _location(headings, text, positive_line.start, positive_line.end),
                _location(headings, text, negative_line.start, negative_line.end),
            )
            findings.append(
                _make_finding(
                    "contradiction_capability_phrase",
                    "cross_section_contradiction",
                    "critical" if blocking else "warning",
                    "phrase_discriminator" if blocking else "phrase_generic",
                    blocking,
                    locations,
                    subject=", ".join(sorted(shared)) or None,
                    polarity="explicit_constraint",
                    message=(
                        "A public capability claim and a limitations statement appear to "
                        "describe the same capability with opposite polarity."
                    ),
                    repair_target=(
                        f"{locations[1].section_path}: reconcile with {locations[0].section_path}"
                    ),
                )
            )
    return findings
