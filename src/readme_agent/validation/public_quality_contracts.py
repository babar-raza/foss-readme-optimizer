"""Stable contracts and finding-location helpers for public README quality."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.document_structure import Heading

PUBLIC_QUALITY_CHECKS_VERSION = 5


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
