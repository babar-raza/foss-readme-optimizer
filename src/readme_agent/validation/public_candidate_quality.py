"""Deterministic, non-LLM quality gate for public README candidate prose."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import sys
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.capability_semantics import (
    identifier_discriminators,
    same_public_capability,
)
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
    StructuredFactCoordinateV1,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_structure import Heading, parse_headings
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import VisibleLine, visible_lines

# Bumped whenever the detection heuristics below (cue patterns, tiering thresholds, structural
# outlier ratios) change in a way that could alter findings for unchanged candidate text. See
# test_checks_source_hash_matches_recorded_version for the enforcement mechanism.
PUBLIC_QUALITY_CHECKS_VERSION = 3

# ---------------------------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------------------------


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicQualitySpanV1(_StrictModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered(self) -> PublicQualitySpanV1:
        if self.end <= self.start:
            raise ValueError("public quality span must be non-empty and ordered")
        return self


class PublicQualityLocationV1(_StrictModel):
    section_path: str = Field(min_length=1)
    span: PublicQualitySpanV1


PublicQualityCategory = Literal[
    "cross_section_contradiction",
    "process_leakage",
    "malformed_prose",
    "claim_grounding",
    "structural_quality",
]
PublicQualitySeverity = Literal["critical", "warning"]
# Evidence-strength tier, not a category label: structured_evidence (backed by a supplied
# fact/claim record) and exact_symbol (exact deterministic token/pattern match) are high
# confidence; phrase_discriminator (fuzzy phrase match anchored by a shared discriminator token)
# is medium; phrase_generic (fuzzy phrase match with no shared anchor) is low.
PublicQualityConfidence = Literal[
    "structured_evidence", "exact_symbol", "phrase_discriminator", "phrase_generic"
]
PublicQualityPolarity = Literal["positive_implementation", "explicit_constraint"]
PublicQualityDirection = Literal["read", "write"]


class PublicQualityFindingV1(_StrictModel):
    finding_id: str = Field(pattern=r"^public_quality\.[a-z0-9_]+\.[0-9a-f]{12}$")
    check_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    category: PublicQualityCategory
    severity: PublicQualitySeverity
    confidence: PublicQualityConfidence
    blocking: bool
    locations: tuple[PublicQualityLocationV1, ...] = Field(min_length=1)
    subject: str | None = None
    operation: str | None = None
    direction: PublicQualityDirection | None = None
    polarity: PublicQualityPolarity | None = None
    conflicting_ids: tuple[str, ...] = ()
    evidence_refs: tuple[StructuredFactCoordinateV1, ...] = ()
    message: str = Field(min_length=1)
    repair_target: str = Field(min_length=1)


class PublicQualityCountsV1(_StrictModel):
    cross_section_contradiction: int = 0
    process_leakage: int = 0
    malformed_prose: int = 0
    claim_grounding: int = 0
    structural_quality: int = 0
    critical: int = 0
    warning: int = 0
    blocking: int = 0
    advisory: int = 0


class PublicQualityReportV1(_StrictModel):
    schema_version: Literal[1] = 1
    checks_version: int = PUBLIC_QUALITY_CHECKS_VERSION
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checks_run: tuple[str, ...]
    findings: tuple[PublicQualityFindingV1, ...] = ()
    counts: PublicQualityCountsV1
    report_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _internally_consistent(self) -> PublicQualityReportV1:
        if list(self.checks_run) != sorted(set(self.checks_run)):
            raise ValueError("checks_run must be sorted and unique")
        expected = _content_hash(self.model_dump(mode="json", exclude={"report_hash"}))
        if self.report_hash != expected:
            raise ValueError("report_hash does not match canonical content hash")
        return self


# ---------------------------------------------------------------------------------------------
# Hashing / fingerprint helpers
# ---------------------------------------------------------------------------------------------


def _content_hash(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fingerprint(check_id: str, locations: tuple[PublicQualityLocationV1, ...]) -> str:
    ordered = sorted(
        locations,
        key=lambda location: (
            location.section_path,
            location.span.start,
            location.span.end,
            location.span.text,
        ),
    )
    payload = (
        check_id
        + "\0"
        + "\0".join(
            f"{location.section_path}\0{location.span.start}\0{location.span.end}\0"
            f"{location.span.text}\0{index}"
            for index, location in enumerate(ordered)
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _make_finding(
    check_id: str,
    category: PublicQualityCategory,
    severity: PublicQualitySeverity,
    confidence: PublicQualityConfidence,
    blocking: bool,
    locations: tuple[PublicQualityLocationV1, ...],
    *,
    message: str,
    repair_target: str,
    subject: str | None = None,
    operation: str | None = None,
    direction: PublicQualityDirection | None = None,
    polarity: PublicQualityPolarity | None = None,
    conflicting_ids: tuple[str, ...] = (),
    evidence_refs: tuple[StructuredFactCoordinateV1, ...] = (),
) -> PublicQualityFindingV1:
    ordered = tuple(
        sorted(
            locations,
            key=lambda location: (
                location.section_path,
                location.span.start,
                location.span.end,
                location.span.text,
            ),
        )
    )
    fingerprint = _fingerprint(check_id, ordered)
    return PublicQualityFindingV1(
        finding_id=f"public_quality.{check_id}.{fingerprint}",
        check_id=check_id,
        category=category,
        severity=severity,
        confidence=confidence,
        blocking=blocking,
        locations=ordered,
        subject=subject,
        operation=operation,
        direction=direction,
        polarity=polarity,
        conflicting_ids=conflicting_ids,
        evidence_refs=evidence_refs,
        message=message,
        repair_target=repair_target,
    )


def _section_path(headings: list[Heading], offset: int) -> str:
    """Return a breadcrumb of enclosing heading titles for one character offset.

    Distinguishes two identically-titled headings that sit under different parents, since each
    accumulates a different chain of enclosing ancestors.
    """

    enclosing = sorted(
        (heading for heading in headings if heading.start <= offset < heading.section_end),
        key=lambda heading: heading.start,
    )
    if not enclosing:
        return "(preamble)"
    return " > ".join(heading.title.strip() for heading in enclosing)


def _location(headings: list[Heading], text: str, start: int, end: int) -> PublicQualityLocationV1:
    return PublicQualityLocationV1(
        section_path=_section_path(headings, start),
        span=PublicQualitySpanV1(start=start, end=end, text=text[start:end]),
    )


# ---------------------------------------------------------------------------------------------
# Shared cue patterns (generic English polarity/scope cues -- no product/family branching)
# ---------------------------------------------------------------------------------------------

_POSITIVE_CUE = re.compile(
    r"(?i)\b(?:support(?:s|ed|ing)?|provide[sd]?|providing|implement(?:s|ed|ing)?|enable[sd]?|"
    r"enabling|allow(?:s|ed|ing)?|return(?:s|ed|ing)?|creat(?:e[sd]?|ing)|export(?:s|ed|ing)?|"
    r"import(?:s|ed|ing)?|convert(?:s|ed|ing)?|render(?:s|ed|ing)?|generat(?:e[sd]?|ing)|"
    r"sav(?:e[sd]?|ing)|load(?:s|ed|ing)?|pars(?:e[sd]?|ing)|reads?|reading|writ(?:e[sd]?|ing)|"
    r"calls?\b.*\boperation\b)\b"
)
_NEGATIVE_CUE = re.compile(
    r"(?i)\b(?:not\s+(?:currently\s+)?(?:support(?:ed)?|implement(?:ed)?|available|reachable)|"
    r"unsupported|no\s+support\s+for|NotImplementedError|not\s+yet\s+(?:supported|implemented)|"
    r"unavailable|limit(?:ed)?\s+to|restrict(?:ed)?\s+to|remain(?:s)?\s+incomplete|"
    r"out\s+of\s+scope|only\b.{0,80}\bsupported)\b"
)
_SCOPE_QUALIFIER = re.compile(
    r"(?i)\b(?:through\s+the\s+public\s+api|in\s+this\s+build|in\s+this\s+edition|"
    r"on\s+this\s+platform)\b"
)
# Independently defined, publicly-scoped equivalent of capability_semantics.py's private
# _READ_DIRECTION/_WRITE_DIRECTION (same vocabulary; that pair is module-private there, and
# AGENTS.md disallows depending on another module's `_`-private helpers).
_READ_CUE = re.compile(
    r"(?i)\b(?:read(?:s|ing)?|load(?:s|ing)?|import(?:s|ing)?|open(?:s|ing)?|pars(?:e|es|ing))\b"
)
_WRITE_CUE = re.compile(
    r"(?i)\b(?:writ(?:e|es|ing)|sav(?:e|es|ing)|export(?:s|ing)?|generat(?:e|es|ing))\b"
)
_BACKTICK_SYMBOL = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)(?:\(\))?`")
_INLINE_CODE_SPAN = re.compile(r"`[^`\r\n]+`")
_URL = re.compile(r"https?://\S+")
_WORD = re.compile(r"[A-Za-z]+")
_IDENTIFIER_TOKEN = re.compile(r"`[^`\r\n]+`|\b[a-z]+(?:_[a-z0-9]+)+\b")
_SAFE_DOUBLES = frozenset({"that", "had", "has", "was"})
_INFLECTION_SUFFIXES = ("ing", "ed", "es")
_PLACEHOLDER_BODY = re.compile(r"(?i)^(?:tbd|coming soon\.?|lorem ipsum.*|n/a)$")
# "Saving formats other than PDF ... are not implemented" narrows the negative claim AWAY FROM
# PDF, not onto it -- an explicit exception clause removes its named discriminator(s) from the
# negative statement's subject before matching, so a broad "everything except X" limitation does
# not fire against every unrelated positive claim that happens to mention X (found via the
# manual precision dry-run against real committed candidates; see WORKLOG.md).
_EXCEPTION_CLAUSE = re.compile(
    r"(?i)\b(?:other\s+than|except(?:ing)?|excluding|besides)\s+"
    r"([A-Za-z0-9][A-Za-z0-9/+.\-, ()]{0,60}?)(?=[.;]|\)?\s+(?:are|is|were|was)\b|$)"
)
# Conditional runtime-dependency prose ("if `X` is installed ... / if `X` is unavailable ...")
# describes branching behavior, not an unconditional capability claim -- also found via the
# manual precision dry-run.
_CONDITIONAL_MARKER = re.compile(
    r"(?i)\bif\s+(?:the\s+)?[`\"']?[\w.]+[`\"']?\s+is\s+"
    r"(?:installed|not\s+installed|available|unavailable|not\s+available|present|absent)\b"
)


def _excepted_discriminators(value: str) -> frozenset[str]:
    excepted: set[str] = set()
    for match in _EXCEPTION_CLAUSE.finditer(value):
        excepted |= identifier_discriminators(match.group(1))
    return frozenset(excepted)


def _spans_overlap(index: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in spans)


def _direction(value: str) -> PublicQualityDirection | None:
    reads = _READ_CUE.search(value) is not None
    writes = _WRITE_CUE.search(value) is not None
    if reads and not writes:
        return "read"
    if writes and not reads:
        return "write"
    return None


def _opposite_direction(left: str, right: str) -> bool:
    left_direction = _direction(left)
    right_direction = _direction(right)
    return (
        left_direction is not None
        and right_direction is not None
        and left_direction != right_direction
    )


# ---------------------------------------------------------------------------------------------
# Tier A -- claim grounding against explicit structured negative/unresolved facts
# ---------------------------------------------------------------------------------------------


def _fact_phrase(fact: FactRecordV2) -> str | None:
    value = fact.value
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        parts = [str(item) for item in value if str(item).strip()]
        return ", ".join(parts) if parts else None
    if isinstance(value, dict):
        parts = [str(item) for item in value.values() if isinstance(item, str) and item.strip()]
        return ", ".join(parts) if parts else None
    return None


def _check_claim_grounding_negative_fact(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    if facts is None:
        return []
    negative_facts = [
        fact
        for fact in facts.facts
        if fact.field == "product.limitations"
        or fact.verification_state in {"conflicting", "blocked", "missing"}
    ]
    if not negative_facts:
        return []
    findings: list[PublicQualityFindingV1] = []
    for line in visible_lines(text):
        if _NEGATIVE_CUE.search(line.text) or not _POSITIVE_CUE.search(line.text):
            continue
        accountable_fact_ids = None
        if claim_accountability is not None:
            accountable_fact_ids = {
                fact_id
                for claim in claim_accountability.claims
                if claim.stage == "candidate"
                and claim.currently_accountable
                and claim.source_byte_start < line.end
                and claim.source_byte_end > line.start
                for fact_id in claim.accepted_fact_ids
            }
        for fact in negative_facts:
            if accountable_fact_ids is not None and fact.fact_id not in accountable_fact_ids:
                continue
            fact_phrase = _fact_phrase(fact)
            if not fact_phrase or not same_public_capability(line.text, fact_phrase):
                continue
            location = _location(headings, text, line.start, line.end)
            findings.append(
                _make_finding(
                    "claim_grounding_negative_fact",
                    "claim_grounding",
                    "critical",
                    "structured_evidence",
                    True,
                    (location,),
                    subject=fact.field,
                    polarity="explicit_constraint",
                    conflicting_ids=(fact.fact_id,),
                    message=(
                        f"Public prose asserts a capability that fact {fact.fact_id!r} "
                        f"({fact.field}, verification_state={fact.verification_state!r}) records "
                        "as a limitation or unresolved."
                    ),
                    repair_target=f"{location.section_path}: reconcile with fact {fact.fact_id}",
                )
            )
    return findings


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


# ---------------------------------------------------------------------------------------------
# Check registry and entry point
# ---------------------------------------------------------------------------------------------

_CheckFn = Callable[
    [str, list[Heading], ProductFactsV2 | None, ReadmeClaimAccountabilityMapV1 | None],
    list[PublicQualityFindingV1],
]

# (check_id, category, requires_structured_evidence, function). A check with
# requires_structured_evidence=True is omitted from checks_run entirely (never run-with-zero-
# findings) when neither facts nor claim_accountability is supplied -- an honest "not evaluated",
# not a fabricated pass.
_CHECKS: tuple[tuple[str, PublicQualityCategory, bool, _CheckFn], ...] = (
    (
        "claim_grounding_negative_fact",
        "claim_grounding",
        True,
        _check_claim_grounding_negative_fact,
    ),
    (
        "contradiction_capability_symbol",
        "cross_section_contradiction",
        False,
        _check_contradiction_capability_symbol,
    ),
    (
        "contradiction_capability_phrase",
        "cross_section_contradiction",
        False,
        _check_contradiction_capability_phrase,
    ),
    ("process_leakage", "process_leakage", False, _check_process_leakage),
    (
        "malformed_low_information_prose",
        "malformed_prose",
        False,
        _check_malformed_low_information_prose,
    ),
    ("malformed_duplicate_language", "malformed_prose", False, _check_malformed_duplicate_language),
    ("empty_or_placeholder_section", "malformed_prose", False, _check_empty_or_placeholder_section),
    ("structural_size_outlier", "structural_quality", False, _check_structural_size_outlier),
    ("structural_detail_density", "structural_quality", False, _check_structural_detail_density),
)

# Forget-proofing tripwire (mirrors validation/registry.py's VALIDATION_RULESET_VERSION /
# _RULES_SOURCE_HASH_AT_VERSION convention): test_checks_source_hash_matches_recorded_version
# recomputes the live hash of every check function's source and fails loudly if it no longer
# matches this recorded value, forcing a conscious "does PUBLIC_QUALITY_CHECKS_VERSION need to
# move" decision on every detection-logic edit instead of a silent, unreviewed drift.
_CHECKS_SOURCE_HASH_AT_VERSION = "5e189b4bd45fa9bbb2fc61927b0035f75f775afe1a4a438dc91a5503dd766f27"


def compute_checks_source_hash() -> str:
    """Deliberately over-sensitive, like validation/registry.py's compute_rules_source_hash():
    hashes this entire module's source (minus the line(s) that record the expected hash itself,
    to avoid a self-referential loop) rather than only the check functions' own bodies -- a
    cue-pattern constant (e.g. _POSITIVE_CUE, _EXCEPTION_CLAUSE) can change detection behavior
    without touching any function body's text, and this tripwire must not miss that."""

    source = inspect.getsource(sys.modules[__name__])
    kept = [line for line in source.splitlines() if "_CHECKS_SOURCE_HASH_AT_VERSION" not in line]
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


_COUNT_FIELDS = (
    "cross_section_contradiction",
    "process_leakage",
    "malformed_prose",
    "claim_grounding",
    "structural_quality",
    "critical",
    "warning",
    "blocking",
    "advisory",
)


def _build_counts(findings: list[PublicQualityFindingV1]) -> PublicQualityCountsV1:
    tally: dict[str, int] = dict.fromkeys(_COUNT_FIELDS, 0)
    for finding in findings:
        tally[finding.category] += 1
        tally[finding.severity] += 1
        tally["blocking" if finding.blocking else "advisory"] += 1
    return PublicQualityCountsV1(**tally)


def evaluate_public_candidate_quality(
    candidate_text: str,
    *,
    facts: ProductFactsV2 | None = None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None = None,
) -> PublicQualityReportV1:
    """Deterministically evaluate public README candidate prose for known defect classes.

    Pure function: identical ``candidate_text``/``facts``/``claim_accountability`` inputs always
    produce a byte-identical serialized report, including ``report_hash``.
    """

    candidate_sha256 = sha256_hex(candidate_text)
    headings = parse_headings(candidate_text)
    checks_run: list[str] = []
    findings: list[PublicQualityFindingV1] = []
    has_structured_evidence = facts is not None or claim_accountability is not None
    for check_id, _category, requires_structured_evidence, check_fn in _CHECKS:
        if requires_structured_evidence and not has_structured_evidence:
            continue
        checks_run.append(check_id)
        findings.extend(check_fn(candidate_text, headings, facts, claim_accountability))
    findings.sort(
        key=lambda finding: (
            finding.locations[0].section_path,
            finding.locations[0].span.start,
            finding.locations[0].span.end,
            finding.check_id,
        )
    )
    counts = _build_counts(findings)
    checks_run_sorted = tuple(sorted(checks_run))
    findings_tuple = tuple(findings)

    draft = PublicQualityReportV1.model_construct(
        schema_version=1,
        checks_version=PUBLIC_QUALITY_CHECKS_VERSION,
        candidate_sha256=candidate_sha256,
        checks_run=checks_run_sorted,
        findings=findings_tuple,
        counts=counts,
        report_hash="0" * 64,
    )
    report_hash = _content_hash(draft.model_dump(mode="json", exclude={"report_hash"}))
    return PublicQualityReportV1(
        schema_version=1,
        checks_version=PUBLIC_QUALITY_CHECKS_VERSION,
        candidate_sha256=candidate_sha256,
        checks_run=checks_run_sorted,
        findings=findings_tuple,
        counts=counts,
        report_hash=report_hash,
    )


__all__ = [
    "PUBLIC_QUALITY_CHECKS_VERSION",
    "PublicQualityCategory",
    "PublicQualityConfidence",
    "PublicQualityCountsV1",
    "PublicQualityDirection",
    "PublicQualityFindingV1",
    "PublicQualityLocationV1",
    "PublicQualityPolarity",
    "PublicQualityReportV1",
    "PublicQualitySeverity",
    "PublicQualitySpanV1",
    "evaluate_public_candidate_quality",
]
