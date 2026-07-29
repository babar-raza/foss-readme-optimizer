"""Typed receipts for reviewer-directed README repair."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RepairFindingRequestV1(_StrictModel):
    """Normalized repair authority extracted from grounded reviewer records."""

    finding_id: str
    section: str
    criterion: str
    quoted_candidate_span: str
    required_repair: str


class RepairTextDeltaV1(_StrictModel):
    """One inspectable changed region between reviewer-visible candidates."""

    before_start: int = Field(ge=0)
    before_end: int = Field(ge=0)
    after_start: int = Field(ge=0)
    after_end: int = Field(ge=0)
    before_sha256: str
    after_sha256: str
    before_excerpt: str
    after_excerpt: str


class RepairFindingResolutionV1(_StrictModel):
    """Pre-rereview proof that one rejected finding received a relevant edit."""

    finding_id: str
    section: str
    prior_span_occurrences: int = Field(ge=0)
    repaired_span_occurrences: int = Field(ge=0)
    section_changed: bool
    bound_operation_ids: list[str]
    changed_bound_operation_ids: list[str]
    status: Literal["addressed_pending_rereview", "unresolved_unchanged"]


class RepairAttemptReceiptV1(_StrictModel):
    """Candidate-delta and finding-resolution receipt controlling rereview."""

    schema_version: Literal[1] = 1
    repair_attempt: int = Field(ge=1)
    before_candidate_sha256: str
    after_candidate_sha256: str
    candidate_changed: bool
    changed_spans: list[RepairTextDeltaV1]
    changed_operation_ids: list[str]
    finding_resolutions: list[RepairFindingResolutionV1]
    addressed_finding_ids: list[str]
    resolved_finding_ids: list[str] = Field(default_factory=list)
    unresolved_finding_ids: list[str]
    reviewer_call_count_before_rereview: int = Field(ge=1)
    reviewer_call_count_after_rereview: int | None = Field(default=None, ge=1)
    rereview_authorized: bool
