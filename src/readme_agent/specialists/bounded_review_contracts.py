"""Typed contracts for deterministic bounded README review packets."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.readme_review_roles import FactualPlanVerdict

_ALGORITHM_CONTRACT_VERSION = "bounded-review-packets-v2-target-scoped-visitor-evidence"
DEFAULT_BOUNDED_PACKET_BUDGET_CHARS = 120_000
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
DEFAULT_API_INVENTORY_HEADING_KEYWORDS: frozenset[str] = frozenset(
    {"api", "reference", "methods", "classes", "endpoints", "properties", "parameters"}
)
DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD = 0.6
DEFAULT_NEIGHBOR_CONTEXT_CHARS = 400

PacketFacet = Literal["factual", "visitor"]
UnitKind = Literal["heading", "paragraph", "fence", "table", "list"]
UnpacketizableReason = Literal["unresolved_fact_reference", "oversized_unit"]
AggregateOverall = Literal["ACCEPT", "INCOMPLETE", "REJECTED", "CONFLICT", "BLOCKED"]
BoundedPacketVerdict = FactualPlanVerdict


class BoundedReviewInputMismatchError(ValueError):
    """Raised when candidate/facts/plan hashes disagree -- a caller contract violation.

    Distinct from ``UnpacketizableRecordV1`` (redesign point 4): this is raised at plan
    construction time and aborts the whole call. A localized referential gap on one claim or
    provenance entry never raises this -- it becomes a recorded, non-fatal blocking record instead.
    """


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------------------------
# Atomic units and section classification
# --------------------------------------------------------------------------------------------


class AtomicUnitV1(_StrictModel):
    """One structural, never-split Markdown block with its exact document position."""

    unit_id: str = Field(min_length=1)
    kind: UnitKind
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    claim_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    requires_factual_review: bool = False

    @model_validator(mode="after")
    def _valid_span(self) -> AtomicUnitV1:
        if self.char_end <= self.char_start:
            raise ValueError("atomic unit requires a nonempty char span")
        if self.line_end < self.line_start:
            raise ValueError("atomic unit line_end must be >= line_start")
        return self


class SectionClassificationV1(_StrictModel):
    """One section's deterministic mechanical-API-inventory classification."""

    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    classification: Literal["standard", "mechanical_api_inventory"]
    justification: str = Field(min_length=1)


class UnpacketizableRecordV1(_StrictModel):
    """One explicit blocking record -- never a silent omission (redesign point 4).

    ``reason="unresolved_fact_reference"``: one claim's or provenance entry's ``accepted_fact_ids``
    / ``fact_ids`` cites a fact absent from ``product_facts`` -- localized data damage, recorded
    for that record alone. ``reason="oversized_unit"``: one atomic unit's own minimal packaged
    payload exceeds ``budget_chars`` even alone and cannot be packed for the named facet.
    """

    record_id: str = Field(min_length=1)
    reason: UnpacketizableReason
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    claim_id: str | None = None
    provenance_id: str | None = None
    missing_fact_id: str | None = None
    unit_kind: UnitKind | None = None
    required_min_budget: int | None = None
    detail: str = Field(min_length=1)

    @model_validator(mode="after")
    def _shape_matches_reason(self) -> UnpacketizableRecordV1:
        if self.reason == "unresolved_fact_reference":
            no_subject = self.claim_id is None and self.provenance_id is None
            if self.missing_fact_id is None or no_subject:
                raise ValueError(
                    "unresolved_fact_reference record requires missing_fact_id and a claim_id or "
                    "provenance_id"
                )
            if self.unit_kind is not None or self.required_min_budget is not None:
                raise ValueError(
                    "unresolved_fact_reference record cannot carry oversized_unit fields"
                )
        else:
            if self.unit_kind is None or self.required_min_budget is None:
                raise ValueError("oversized_unit record requires unit_kind and required_min_budget")
            if (
                self.claim_id is not None
                or self.provenance_id is not None
                or self.missing_fact_id is not None
            ):
                raise ValueError(
                    "oversized_unit record cannot carry unresolved_fact_reference fields"
                )
        return self


# --------------------------------------------------------------------------------------------
# Packets and plan
# --------------------------------------------------------------------------------------------


class BoundedFactualPacketV1(_StrictModel):
    """One bounded factual-review packet: minimal section-scoped prose plus reachable facts."""

    schema_version: Literal[1] = 1
    packet_id: str = Field(min_length=1)
    stable_slot_id: str = Field(min_length=1)
    facet: Literal["factual"] = "factual"
    order: int = Field(ge=0)
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    unit_text: str = Field(min_length=1)
    covered_unit_ids: tuple[str, ...] = Field(min_length=1)
    claim_ids: tuple[str, ...] = ()
    accepted_fact_ids: tuple[str, ...] = ()
    facts: tuple[dict[str, Any], ...] = ()
    do_not_claim: tuple[dict[str, Any], ...] = ()
    provenance_ids: tuple[str, ...] = ()
    prompt_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    input_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    packet_sha256: str = Field(pattern=_SHA256_PATTERN)


class BoundedVisitorPacketV1(_StrictModel):
    """One bounded visitor-review packet: full section prose plus bounded neighbor context."""

    schema_version: Literal[1] = 1
    packet_id: str = Field(min_length=1)
    stable_slot_id: str = Field(min_length=1)
    facet: Literal["visitor"] = "visitor"
    order: int = Field(ge=0)
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    section_text: str = Field(min_length=1)
    neighbor_context_before: str = ""
    neighbor_context_after: str = ""
    covered_unit_ids: tuple[str, ...] = Field(min_length=1)
    prompt_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    input_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    packet_sha256: str = Field(pattern=_SHA256_PATTERN)


BoundedPacketV1: TypeAlias = BoundedFactualPacketV1 | BoundedVisitorPacketV1


class BoundedReviewPlanV1(_StrictModel):
    """A complete, deterministic bounded-review packet plan for one candidate."""

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    budget_chars: int = Field(gt=0)
    factual_packets: tuple[BoundedFactualPacketV1, ...] = ()
    visitor_packets: tuple[BoundedVisitorPacketV1, ...] = ()
    unpacketizable: tuple[UnpacketizableRecordV1, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))
