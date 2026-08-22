"""Deterministic bounded-review packetizer, validator, aggregator, and repair router.

Standalone module. Codex is the sole integration authority; nothing here is registered anywhere
and nothing here calls a provider/LLM client. It only prepares bounded review packets from an
already-composed README candidate, validates packet-scoped reviewer results, reduces them to one
fail-closed aggregate verdict, and routes narrow repair targets. The system state machine outside
this module retains all retry authority.

Why this exists (see the design plan for the full root-cause analysis): the existing factual and
visitor reviewers send the whole candidate plus the whole fact corpus in one call, against a
measured payload ceiling (owner-audit ``qwen_context_budget/REPORT.md``), and the provider's
tool-call output is independently nondeterministic at temperature 0 even for identical input.
Splitting into packets fixes the size failure mode by construction but, if the *planning* layer
itself is not provably deterministic, it adds a third, self-inflicted failure mode on top of the
two inherent ones. This module is built around six redesign points that exist specifically to
avoid that:

1. Canonical-hash discipline: every collection is sorted on an explicit stable key before any hash
   is derived; nothing content-identifying depends on ``set``/``dict`` iteration order or Python's
   hash randomization.
2. Input-sequence normalization at the planning boundary: caller-supplied ``claims``,
   ``candidate_content_provenance``, and ``do_not_claim`` sequences are sorted by a stable key
   before anything is derived from them, regardless of caller-supplied array order.
3. ``_ALGORITHM_CONTRACT_VERSION`` is folded into every ``packet_sha256`` itself, not only into the
   cache-key wrapper, so a change to *how* packets are built cannot silently reuse a
   content-identical-looking cached result produced under different packetization semantics.
4. Two distinct kinds of bad input: a candidate/facts/plan hash mismatch is a caller contract
   violation and raises ``BoundedReviewInputMismatchError`` at construction time; an unresolvable
   fact reference on one claim or provenance entry is localized data damage and becomes an
   ``UnpacketizableRecordV1`` for that one record, never a crash and never a silent drop of the
   whole plan.
5. ``BLOCKED`` is a distinct aggregate state from ``INCOMPLETE``. ``INCOMPLETE`` means waiting on
   more reviewer calls and is safe to retry; ``BLOCKED`` means the plan is structurally
   unreviewable (unpacketizable records present) and more LLM calls will not resolve it.
6. The packet-level result envelope (``BoundedPacketResultV1``) mirrors the existing cross-field
   verdict/finding validators already enforced on ``FactualPlanReviewResultV1`` instead of using a
   looser, ad hoc shape.

No provider/LLM client is imported anywhere in this file (enforced by a dedicated test).
"""

from __future__ import annotations

import bisect
import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_inputs import composition_fact_payloads
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_structure import heading_identity
from readme_agent.specialists.readme_review_roles import FactualPlanVerdict
from readme_agent.specialists.review_finding_grounding import (
    BLIND_QUALITY_CRITERIA,
    GroundedReviewFindingV1,
)

# Redesign point 3: folded into every packet_sha256 below, not only into cache keys. Bump this
# whenever packetization semantics change (unit boundaries, packing order, payload shape, ...).
_ALGORITHM_CONTRACT_VERSION = "bounded-review-packets-v1"

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


# --------------------------------------------------------------------------------------------
# Coverage ledger
# --------------------------------------------------------------------------------------------


class CoverageSpanV1(_StrictModel):
    """One atomic unit's assignment to zero or more covering packets for one facet."""

    unit_id: str = Field(min_length=1)
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    unit_kind: UnitKind
    covering_packet_ids: tuple[str, ...] = ()


class ExcludedSpanV1(_StrictModel):
    """One atomic unit explicitly excluded from visitor coverage, with its justification."""

    unit_id: str = Field(min_length=1)
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    classification: str = Field(min_length=1)
    justification: str = Field(min_length=1)


class CoverageOverlapV1(_StrictModel):
    """One intentional multi-packet coverage of the same subject (e.g. neighbor-context text)."""

    subject: str = Field(min_length=1)
    packet_ids: tuple[str, ...]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _at_least_two_packets(self) -> CoverageOverlapV1:
        if len(self.packet_ids) < 2:
            raise ValueError("a coverage overlap requires at least two covering packets")
        return self


class CoverageLedgerV1(_StrictModel):
    """Proof that every required span is covered, bound to exact candidate/plan hashes."""

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    visitor_spans: tuple[CoverageSpanV1, ...] = ()
    factual_spans: tuple[CoverageSpanV1, ...] = ()
    excluded_spans: tuple[ExcludedSpanV1, ...] = ()
    overlaps: tuple[CoverageOverlapV1, ...] = ()
    blocking_record_ids: tuple[str, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class CoverageValidationV1(_StrictModel):
    """Structural completeness of one coverage ledger.

    ``is_complete`` and ``has_blocking_gaps`` are deliberately independent (redesign point 5):
    a ledger can be complete (every span assigned) yet still ``has_blocking_gaps`` when the bound
    plan carries unpacketizable records, and that is exactly what drives the ``BLOCKED`` aggregate
    state below, distinct from ``INCOMPLETE``.
    """

    is_complete: bool
    has_blocking_gaps: bool
    unassigned_visitor_span_ids: tuple[str, ...] = ()
    unassigned_factual_span_ids: tuple[str, ...] = ()


def validate_coverage_ledger(ledger: CoverageLedgerV1) -> CoverageValidationV1:
    """Never raises; reports completeness and blocking-gap status independently."""

    unassigned_visitor = tuple(
        sorted(span.unit_id for span in ledger.visitor_spans if not span.covering_packet_ids)
    )
    unassigned_factual = tuple(
        sorted(span.unit_id for span in ledger.factual_spans if not span.covering_packet_ids)
    )
    return CoverageValidationV1(
        is_complete=not unassigned_visitor and not unassigned_factual,
        has_blocking_gaps=bool(ledger.blocking_record_ids),
        unassigned_visitor_span_ids=unassigned_visitor,
        unassigned_factual_span_ids=unassigned_factual,
    )


# --------------------------------------------------------------------------------------------
# Result envelope, validation, aggregation
# --------------------------------------------------------------------------------------------


class BoundedPacketResultV1(_StrictModel):
    """One packet's reviewer result.

    Mirrors ``FactualPlanReviewResultV1``'s cross-field validator discipline (redesign point 6)
    instead of a looser shape: ACCEPT requires grounded ``supports_acceptance`` findings, a
    ``BLOCKED_*`` verdict requires a corresponding blocking finding, and finding ``kind`` must
    match the packet's own facet (``factual`` for factual packets, ``quality`` for visitor
    packets, restricted to ``BLIND_QUALITY_CRITERIA`` for visitor packets exactly as
    ``BlindQualityReviewResultV1`` restricts its own findings).
    """

    schema_version: Literal[1] = 1
    packet_id: str = Field(min_length=1)
    facet: PacketFacet
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    packet_sha256: str = Field(pattern=_SHA256_PATTERN)
    prompt_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    input_contract_hash: str = Field(pattern=_SHA256_PATTERN)
    verdict: BoundedPacketVerdict
    reasoning: str = Field(min_length=1)
    failed_criteria: tuple[str, ...] = ()
    required_repair: str = ""
    findings: tuple[GroundedReviewFindingV1, ...] = ()

    @model_validator(mode="after")
    def _verdict_payload(self) -> BoundedPacketResultV1:
        if self.verdict == "ACCEPT":
            if self.failed_criteria or self.required_repair:
                raise ValueError("bounded packet ACCEPT cannot carry failure details")
            if not self.findings or any(
                finding.disposition != "supports_acceptance" for finding in self.findings
            ):
                raise ValueError("bounded packet ACCEPT requires grounded supporting findings")
        if (
            self.verdict != "ACCEPT"
            and self.verdict != "SYSTEM_FAILURE"
            and (not self.failed_criteria or not self.findings)
        ):
            raise ValueError("bounded packet failure requires criteria and findings")
        if self.verdict == "REJECT_REPAIRABLE" and any(
            finding.disposition != "requires_repair" for finding in self.findings
        ):
            raise ValueError("bounded packet repair verdict requires repair findings")
        if self.verdict in {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"} and any(
            finding.disposition != "blocks" for finding in self.findings
        ):
            raise ValueError("bounded packet blocked verdict requires blocking findings")
        if self.verdict == "SYSTEM_FAILURE" and self.findings:
            raise ValueError("bounded packet SYSTEM_FAILURE cannot carry findings")
        expected_kind = "quality" if self.facet == "visitor" else "factual"
        if any(finding.kind != expected_kind for finding in self.findings):
            raise ValueError("bounded packet result finding kind does not match packet facet")
        if self.facet == "visitor" and any(
            finding.criterion not in BLIND_QUALITY_CRITERIA for finding in self.findings
        ):
            raise ValueError(
                "bounded visitor packet criterion is outside visible-quality authority"
            )
        if self.verdict == "BLOCKED_FACT_CONFLICT" and not any(
            finding.polarity_result == "contradicts" for finding in self.findings
        ):
            raise ValueError("fact-conflict verdict requires a contradicted factual finding")
        if self.verdict == "BLOCKED_MISSING_EVIDENCE" and not any(
            finding.polarity_result == "missing" for finding in self.findings
        ):
            raise ValueError("missing-evidence verdict requires a missing factual finding")
        return self


class PacketResultValidationV1(_StrictModel):
    """Never-raising structural validation result for one packet result against its plan."""

    valid: bool
    errors: tuple[str, ...] = ()


def _find_packet(plan: BoundedReviewPlanV1, packet_id: str) -> BoundedPacketV1 | None:
    all_packets: tuple[BoundedPacketV1, ...] = (*plan.factual_packets, *plan.visitor_packets)
    for packet in all_packets:
        if packet.packet_id == packet_id:
            return packet
    return None


def _packet_text(packet: BoundedPacketV1) -> str:
    if isinstance(packet, BoundedFactualPacketV1):
        return packet.unit_text
    return packet.neighbor_context_before + packet.section_text + packet.neighbor_context_after


def validate_packet_result(
    plan: BoundedReviewPlanV1,
    result: BoundedPacketResultV1,
) -> PacketResultValidationV1:
    """Never raises. Checks packet existence, hash echoes, and finding containment.

    A finding's ``quoted_candidate_span`` must occur within the packet's own declared text, its
    ``section`` must match the packet's ``section_path``, and (for factual packets) its
    ``fact_id`` must be one of the packet's own ``accepted_fact_ids`` -- this is what rejects a
    finding that "refers outside its span."
    """

    errors: list[str] = []
    packet = _find_packet(plan, result.packet_id)
    if packet is None:
        return PacketResultValidationV1(
            valid=False, errors=(f"{result.packet_id}: packet does not exist in plan",)
        )
    if result.facet != packet.facet:
        errors.append(f"{result.packet_id}: facet does not match plan packet")
    if result.candidate_sha256 != packet.candidate_sha256:
        errors.append(f"{result.packet_id}: candidate_sha256 does not match plan packet")
    if result.packet_sha256 != packet.packet_sha256:
        errors.append(f"{result.packet_id}: packet_sha256 does not match plan packet (stale)")
    if result.prompt_contract_hash != packet.prompt_contract_hash:
        errors.append(f"{result.packet_id}: prompt_contract_hash does not match plan packet")
    if result.input_contract_hash != packet.input_contract_hash:
        errors.append(f"{result.packet_id}: input_contract_hash does not match plan packet")

    packet_text = _packet_text(packet)
    allowed_fact_ids = (
        set(packet.accepted_fact_ids) if isinstance(packet, BoundedFactualPacketV1) else set()
    )
    for finding in result.findings:
        if finding.quoted_candidate_span not in packet_text:
            errors.append(
                f"{finding.finding_id}: quoted span is outside this packet's declared text"
            )
        if finding.section != packet.section_path:
            errors.append(
                f"{finding.finding_id}: finding section does not match packet section_path"
            )
        if finding.fact_id is not None and finding.fact_id not in allowed_fact_ids:
            errors.append(
                f"{finding.finding_id}: fact_id is outside this packet's accepted fact set"
            )
    return PacketResultValidationV1(valid=not errors, errors=tuple(errors))


class AggregateVerdictV1(_StrictModel):
    """One deterministic, fail-closed reduction of every packet result for a plan.

    ``BLOCKED`` is checked first and independently of every packet result (redesign point 5):
    no amount of complete, valid, ACCEPT packet results can rescue a structurally unreviewable
    plan. ``ACCEPT`` requires every required packet present, valid, and ACCEPT, with no conflicts
    -- the default is never ACCEPT.
    """

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    overall: AggregateOverall
    accepted_packet_ids: tuple[str, ...] = ()
    missing_packet_ids: tuple[str, ...] = ()
    invalid_packet_ids: tuple[str, ...] = ()
    rejected_packet_ids: tuple[str, ...] = ()
    conflicting_packet_ids: tuple[str, ...] = ()
    blocking_record_ids: tuple[str, ...] = ()
    details: tuple[str, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def aggregate_packet_results(
    plan: BoundedReviewPlanV1,
    coverage_ledger: CoverageLedgerV1,
    results: Mapping[str, BoundedPacketResultV1],
) -> AggregateVerdictV1:
    """Reduce every packet result to one fail-closed aggregate verdict. Never raises."""

    required_ids = {p.packet_id for p in plan.factual_packets} | {
        p.packet_id for p in plan.visitor_packets
    }
    blocking_record_ids = tuple(sorted(record.record_id for record in plan.unpacketizable))
    ledger_blocked = validate_coverage_ledger(coverage_ledger).has_blocking_gaps
    if ledger_blocked or blocking_record_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="BLOCKED",
            blocking_record_ids=blocking_record_ids,
            missing_packet_ids=tuple(sorted(required_ids - set(results))),
            details=("plan has unpacketizable records; more reviewer calls cannot resolve this",),
        )

    missing_ids = sorted(required_ids - set(results))
    invalid_ids = sorted(
        packet_id
        for packet_id in required_ids
        if packet_id not in missing_ids
        and not validate_packet_result(plan, results[packet_id]).valid
    )
    if missing_ids or invalid_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="INCOMPLETE",
            missing_packet_ids=tuple(missing_ids),
            invalid_packet_ids=tuple(invalid_ids),
        )

    conflicting_ids: set[str] = set()
    for overlap in coverage_ledger.overlaps:
        involved = [packet_id for packet_id in overlap.packet_ids if packet_id in results]
        if len(involved) < 2:
            continue
        verdicts = {results[packet_id].verdict for packet_id in involved}
        if len(verdicts) > 1:
            conflicting_ids.update(involved)
    if conflicting_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="CONFLICT",
            conflicting_packet_ids=tuple(sorted(conflicting_ids)),
        )

    rejected_ids = sorted(
        packet_id for packet_id in required_ids if results[packet_id].verdict != "ACCEPT"
    )
    if rejected_ids:
        return AggregateVerdictV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            overall="REJECTED",
            rejected_packet_ids=tuple(rejected_ids),
        )

    return AggregateVerdictV1(
        candidate_sha256=plan.candidate_sha256,
        plan_hash=plan.plan_hash,
        overall="ACCEPT",
        accepted_packet_ids=tuple(sorted(required_ids)),
    )


# --------------------------------------------------------------------------------------------
# Selective repair routing
# --------------------------------------------------------------------------------------------


class RepairTargetV1(_StrictModel):
    """One narrow, deterministic repair target -- never the whole candidate."""

    packet_id: str | None = None
    facet: PacketFacet | None = None
    section_path: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    claim_ids: tuple[str, ...] = ()
    fact_ids: tuple[str, ...] = ()
    issue_summary: str = Field(min_length=1)
    required_section_authoring_clusters: tuple[str, ...] = ()


class RepairPlanV1(_StrictModel):
    """Pure data production: no retry loop, no candidate mutation, no autonomous call issuance.

    ``requires_deterministic_remediation=True`` (only set when ``aggregate.overall == "BLOCKED"``)
    is the operational payoff of redesign point 5: it tells the caller that issuing more LLM calls
    will not help, and that targets come from ``plan.unpacketizable``, not from reviewer failures.
    """

    schema_version: Literal[1] = 1
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_hash: str = Field(pattern=_SHA256_PATTERN)
    round_number: int = Field(ge=0)
    max_repair_rounds: int = Field(ge=0)
    repair_permitted: bool
    requires_deterministic_remediation: bool = False
    targets: tuple[RepairTargetV1, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def _cluster_for(
    section_path: str, section_cluster_map: Mapping[str, str] | None
) -> tuple[str, ...]:
    if section_cluster_map is None or section_path not in section_cluster_map:
        return ()
    return (section_cluster_map[section_path],)


def route_selective_repairs(
    plan: BoundedReviewPlanV1,
    aggregate: AggregateVerdictV1,
    results: Mapping[str, BoundedPacketResultV1],
    *,
    current_round: int,
    max_repair_rounds: int,
    section_cluster_map: Mapping[str, str] | None = None,
) -> RepairPlanV1:
    """Route a narrow set of deterministic repair targets. Never mutates or retries."""

    repair_permitted = current_round < max_repair_rounds

    if aggregate.overall == "BLOCKED":
        targets = tuple(
            RepairTargetV1(
                packet_id=None,
                facet=None,
                section_path=record.section_path,
                char_start=record.char_start,
                char_end=record.char_end,
                claim_ids=(record.claim_id,) if record.claim_id else (),
                fact_ids=(record.missing_fact_id,) if record.missing_fact_id else (),
                issue_summary=record.detail,
                required_section_authoring_clusters=_cluster_for(
                    record.section_path, section_cluster_map
                ),
            )
            for record in sorted(plan.unpacketizable, key=lambda r: r.record_id)
        )
        return RepairPlanV1(
            candidate_sha256=plan.candidate_sha256,
            plan_hash=plan.plan_hash,
            round_number=current_round,
            max_repair_rounds=max_repair_rounds,
            repair_permitted=repair_permitted,
            requires_deterministic_remediation=True,
            targets=targets,
        )

    problem_ids = sorted(
        set(aggregate.invalid_packet_ids)
        | set(aggregate.rejected_packet_ids)
        | set(aggregate.conflicting_packet_ids)
    )
    target_list: list[RepairTargetV1] = []
    for packet_id in problem_ids:
        packet = _find_packet(plan, packet_id)
        if packet is None:
            continue
        result = results.get(packet_id)
        if result is not None and result.failed_criteria:
            issue = "; ".join(result.failed_criteria)
        elif result is not None:
            issue = result.reasoning
        else:
            issue = "packet result is missing or failed structural validation"
        target_list.append(
            RepairTargetV1(
                packet_id=packet.packet_id,
                facet=packet.facet,
                section_path=packet.section_path,
                char_start=packet.char_start,
                char_end=packet.char_end,
                claim_ids=packet.claim_ids if isinstance(packet, BoundedFactualPacketV1) else (),
                fact_ids=(
                    packet.accepted_fact_ids if isinstance(packet, BoundedFactualPacketV1) else ()
                ),
                issue_summary=issue,
                required_section_authoring_clusters=_cluster_for(
                    packet.section_path, section_cluster_map
                ),
            )
        )
    return RepairPlanV1(
        candidate_sha256=plan.candidate_sha256,
        plan_hash=plan.plan_hash,
        round_number=current_round,
        max_repair_rounds=max_repair_rounds,
        repair_permitted=repair_permitted,
        requires_deterministic_remediation=False,
        targets=tuple(target_list),
    )


# --------------------------------------------------------------------------------------------
# Cache identity
# --------------------------------------------------------------------------------------------


def packet_cache_key(
    packet: BoundedPacketV1,
    *,
    model: str,
    schema_sha256: str,
    facts_hash: str,
    provenance_hash: str,
    sampling_parameters: Mapping[str, Any] | None = None,
) -> str:
    """Deterministic cache identity for one packet's reviewer call.

    ``packet.packet_sha256`` already embeds ``_ALGORITHM_CONTRACT_VERSION``, so an algorithm
    change invalidates through the key without needing a separate version field here.
    """

    return _canonical_hash(
        {
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
            "facet": packet.facet,
            "model": model,
            "schema_sha256": schema_sha256,
            "facts_hash": facts_hash,
            "provenance_hash": provenance_hash,
            "sampling_parameters": dict(sampling_parameters or {}),
        }
    )


def is_reusable_cache_entry(result: BoundedPacketResultV1) -> bool:
    """False for SYSTEM_FAILURE (never let a failure masquerade as a cached ACCEPT)."""

    return result.verdict != "SYSTEM_FAILURE"


def invalidated_packet_ids(
    old_plan: BoundedReviewPlanV1,
    new_plan: BoundedReviewPlanV1,
) -> frozenset[str]:
    """Packets whose cached result must not be reused between ``old_plan`` and ``new_plan``.

    Matches by ``stable_slot_id`` (content-hash-independent). A slot whose ``packet_sha256``
    changed, or that is new/removed, is invalidated. A visitor slot additionally invalidates its
    immediate section-order neighbors, since their neighbor-context text is now stale even though
    their own primary content did not change.
    """

    old_all: tuple[BoundedPacketV1, ...] = (*old_plan.factual_packets, *old_plan.visitor_packets)
    new_all: tuple[BoundedPacketV1, ...] = (*new_plan.factual_packets, *new_plan.visitor_packets)
    old_slots = {p.stable_slot_id: p for p in old_all}
    new_slots = {p.stable_slot_id: p for p in new_all}
    invalidated: set[str] = set()
    for slot in set(old_slots) | set(new_slots):
        old_packet = old_slots.get(slot)
        new_packet = new_slots.get(slot)
        changed = (
            old_packet is None
            or new_packet is None
            or old_packet.packet_sha256 != new_packet.packet_sha256
        )
        if changed:
            if old_packet is not None:
                invalidated.add(old_packet.packet_id)
            if new_packet is not None:
                invalidated.add(new_packet.packet_id)

    new_visitor_by_order = sorted(new_plan.visitor_packets, key=lambda p: p.order)
    section_sequence = [p.section_path for p in new_visitor_by_order]
    changed_sections = {p.section_path for p in new_visitor_by_order if p.packet_id in invalidated}
    for section in changed_sections:
        idx = section_sequence.index(section)
        for neighbor_idx in (idx - 1, idx + 1):
            if 0 <= neighbor_idx < len(section_sequence):
                invalidated.add(new_visitor_by_order[neighbor_idx].packet_id)
    return frozenset(invalidated)


def canonical_json(value: BaseModel) -> str:
    """Deterministic sorted-key JSON serialization shared by every model in this module."""

    return json.dumps(
        value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _packet_sha256(substantive_payload: Mapping[str, Any]) -> str:
    versioned = {**substantive_payload, "_algorithm_contract_version": _ALGORITHM_CONTRACT_VERSION}
    return _canonical_hash(versioned)


def _packet_id_slug(section_path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", section_path.casefold()).strip("-")
    return slug or "section"


# --------------------------------------------------------------------------------------------
# Structural parsing (candidate -> atomic units): pure, line-based, stdlib-only
# --------------------------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
_FENCE_OPEN_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[ \t]*\S*[ \t]*$")
_TABLE_ROW_RE = re.compile(r"^[ \t]*\|.*\|[ \t]*$")
_TABLE_DELIM_CELL_RE = re.compile(r"^:?-+:?$")
_LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]+|\d+[.)][ \t]+)")


@dataclass
class _MutableUnit:
    kind: UnitKind
    char_start: int
    char_end: int
    line_start: int
    line_end: int
    section_path: str
    claim_ids: list[str] = field(default_factory=list)
    provenance_ids: list[str] = field(default_factory=list)
    unit_id: str = ""


def _line_records(text: str) -> list[tuple[int, int, str]]:
    records: list[tuple[int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        records.append((offset, offset + len(line), line.rstrip("\r\n")))
        offset += len(line)
    return records


def _fence_open(line: str) -> tuple[str, int] | None:
    match = _FENCE_OPEN_RE.match(line)
    if match is None:
        return None
    run = match.group(1)
    return run[0], len(run)


def _fence_close(line: str, char: str, min_len: int) -> bool:
    stripped = line.strip()
    return len(stripped) >= min_len and bool(stripped) and set(stripped) == {char}


def _is_table_delimiter_row(line: str) -> bool:
    if not _TABLE_ROW_RE.match(line):
        return False
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(_TABLE_DELIM_CELL_RE.match(cell) for cell in cells)


def _build_raw_units(text: str) -> list[_MutableUnit]:
    """Walk lines once, tracking cumulative char offsets and a heading-chain stack."""

    records = _line_records(text)
    n = len(records)
    units: list[_MutableUnit] = []
    stack: list[tuple[int, str]] = []

    def section_path_now() -> str:
        return "/".join(slug for _, slug in stack) if stack else "front-matter"

    i = 0
    while i < n:
        start, end, stripped = records[i]
        if not stripped.strip():
            i += 1
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match is not None:
            level = len(heading_match.group(1))
            title = re.sub(r"[ \t]+#+[ \t]*$", "", heading_match.group(2).strip()).strip()
            if level == 1:
                unit_section_path = "front-matter"
            else:
                slug = heading_identity(title)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, slug))
                unit_section_path = section_path_now()
            units.append(
                _MutableUnit(
                    kind="heading",
                    char_start=start,
                    char_end=end,
                    line_start=i + 1,
                    line_end=i + 1,
                    section_path=unit_section_path,
                )
            )
            i += 1
            continue

        fence_info = _fence_open(stripped)
        if fence_info is not None:
            char, min_len = fence_info
            j = i + 1
            close_index = None
            while j < n:
                if _fence_close(records[j][2], char, min_len):
                    close_index = j
                    break
                j += 1
            end_index = close_index if close_index is not None else n - 1
            units.append(
                _MutableUnit(
                    kind="fence",
                    char_start=start,
                    char_end=records[end_index][1],
                    line_start=i + 1,
                    line_end=end_index + 1,
                    section_path=section_path_now(),
                )
            )
            i = end_index + 1
            continue

        table_starts_here = (
            _TABLE_ROW_RE.match(stripped)
            and i + 1 < n
            and _is_table_delimiter_row(records[i + 1][2])
        )
        if table_starts_here:
            j = i + 1
            while j < n and records[j][2].strip() and _TABLE_ROW_RE.match(records[j][2]):
                j += 1
            end_index = j - 1
            units.append(
                _MutableUnit(
                    kind="table",
                    char_start=start,
                    char_end=records[end_index][1],
                    line_start=i + 1,
                    line_end=end_index + 1,
                    section_path=section_path_now(),
                )
            )
            i = end_index + 1
            continue

        # Paragraph or list: the remaining contiguous non-blank line run.
        j = i
        is_list = False
        while j < n and records[j][2].strip():
            candidate = records[j][2]
            if _HEADING_RE.match(candidate) or _fence_open(candidate) is not None:
                break
            if _LIST_MARKER_RE.match(candidate):
                is_list = True
            j += 1
        end_index = j - 1
        units.append(
            _MutableUnit(
                kind="list" if is_list else "paragraph",
                char_start=start,
                char_end=records[end_index][1],
                line_start=i + 1,
                line_end=end_index + 1,
                section_path=section_path_now(),
            )
        )
        i = end_index + 1

    return units


def _byte_offset_table(text: str) -> list[int]:
    """Cumulative UTF-8 byte offset for character index ``i`` (len(text)+1 entries)."""

    offsets = [0]
    total = 0
    for ch in text:
        total += len(ch.encode("utf-8"))
        offsets.append(total)
    return offsets


def _char_span_from_byte_span(
    byte_offsets: list[int], byte_start: int, byte_end: int
) -> tuple[int, int]:
    return bisect.bisect_left(byte_offsets, byte_start), bisect.bisect_left(byte_offsets, byte_end)


def _section_path_at(raw_units: list[_MutableUnit], char_offset: int) -> str:
    starts = [u.char_start for u in raw_units]
    idx = bisect.bisect_right(starts, char_offset) - 1
    return raw_units[idx].section_path if idx >= 0 else "front-matter"


def _merge_units_for_claim_spans(
    units: list[_MutableUnit],
    claim_char_spans: list[tuple[int, int, str]],
) -> list[_MutableUnit]:
    """Merge overlapping units until no claim span straddles a unit boundary."""

    changed = True
    while changed:
        changed = False
        for char_start, char_end, _claim_id in claim_char_spans:
            if char_end <= char_start:
                continue
            overlap_indices = [
                idx
                for idx, unit in enumerate(units)
                if unit.char_start < char_end and char_start < unit.char_end
            ]
            if len(overlap_indices) > 1:
                first, last = overlap_indices[0], overlap_indices[-1]
                group = units[first : last + 1]
                kinds = {unit.kind for unit in group}
                merged = _MutableUnit(
                    kind=next(iter(kinds)) if len(kinds) == 1 else "paragraph",
                    char_start=group[0].char_start,
                    char_end=group[-1].char_end,
                    line_start=group[0].line_start,
                    line_end=group[-1].line_end,
                    section_path=group[0].section_path,
                )
                units = units[:first] + [merged] + units[last + 1 :]
                changed = True
                break
    return units


def _attach_claim_ids(
    units: list[_MutableUnit], claim_char_spans: list[tuple[int, int, str]]
) -> None:
    for char_start, char_end, claim_id in claim_char_spans:
        if char_end <= char_start:
            continue
        for unit in units:
            if unit.char_start <= char_start and char_end <= unit.char_end:
                unit.claim_ids.append(claim_id)
                break


def _attach_provenance_ids(units: list[_MutableUnit], spans: list[tuple[int, int, str]]) -> None:
    for char_start, char_end, provenance_id in spans:
        if char_end <= char_start:
            continue
        for unit in units:
            if unit.char_start < char_end and char_start < unit.char_end:
                unit.provenance_ids.append(provenance_id)


def _group_into_sections(units: Sequence[Any]) -> list[list[Any]]:
    groups: list[list[Any]] = []
    for unit in units:
        if groups and groups[-1][-1].section_path == unit.section_path:
            groups[-1].append(unit)
        else:
            groups.append([unit])
    return groups


def _dedupe_section_paths(sections: list[list[_MutableUnit]]) -> None:
    """Disambiguate non-adjacent recurrences of the same heading text/slug."""

    seen: dict[str, int] = {}
    for group in sections:
        base = group[0].section_path
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            new_path = f"{base}~{seen[base]}"
            for unit in group:
                unit.section_path = new_path


def _classify_sections(
    sections: Sequence[Sequence[Any]],
    *,
    api_inventory_heading_keywords: frozenset[str],
    api_inventory_table_fence_threshold: float,
) -> dict[str, SectionClassificationV1]:
    result: dict[str, SectionClassificationV1] = {}
    for group in sections:
        section_path = group[0].section_path
        heading_words = set(re.split(r"[/-]", section_path))
        keyword_match = bool(heading_words & api_inventory_heading_keywords)
        total_chars = sum(unit.char_end - unit.char_start for unit in group) or 1
        table_fence_chars = sum(
            unit.char_end - unit.char_start for unit in group if unit.kind in {"table", "fence"}
        )
        dominated = (table_fence_chars / total_chars) >= api_inventory_table_fence_threshold
        if keyword_match and dominated:
            classification: Literal["standard", "mechanical_api_inventory"] = (
                "mechanical_api_inventory"
            )
            justification = (
                f"section path {section_path!r} matches an API-inventory keyword and "
                f"{table_fence_chars}/{total_chars} characters "
                f"({table_fence_chars / total_chars:.0%}) are table/fence content"
            )
        else:
            classification = "standard"
            justification = (
                "does not meet the configured API-inventory heading-keyword + "
                "table/fence-dominance heuristic"
            )
        result[section_path] = SectionClassificationV1(
            section_path=section_path,
            char_start=group[0].char_start,
            char_end=group[-1].char_end,
            classification=classification,
            justification=justification,
        )
    return result


def _claim_char_spans(
    byte_offsets: list[int], claims: Sequence[ReadmeClaimAccountabilityV1]
) -> list[tuple[int, int, str]]:
    spans = []
    for claim in claims:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, claim.source_byte_start, claim.source_byte_end
        )
        spans.append((char_start, char_end, claim.claim_id))
    return spans


def _provenance_char_spans(
    byte_offsets: list[int], entries: Sequence[CandidateContentProvenanceV1]
) -> list[tuple[int, int, str]]:
    spans = []
    for entry in entries:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, entry.candidate_byte_start, entry.candidate_byte_end
        )
        spans.append((char_start, char_end, entry.provenance_id))
    return spans


def _order_invariant_claim_accountability_hash(
    claim_accountability: ReadmeClaimAccountabilityMapV1,
) -> str:
    """Hash a claim map's substance without depending on its ``claims`` array order.

    ``ReadmeClaimAccountabilityMapV1.canonical_hash()`` uses sorted-key JSON, but ``sort_keys``
    only sorts dict keys -- it does not reorder the ``claims`` list itself. Folding that method's
    result directly into ``plan_hash`` would make the plan's own top-level hash depend on
    caller-supplied claim order, exactly the self-inflicted nondeterminism redesign point 1/2
    exist to rule out. Sorting each claim's dumped payload by its own stable key first closes
    that gap.
    """

    payload = {
        "org_repo": claim_accountability.org_repo,
        "facts_hash": claim_accountability.facts_hash,
        "source_sha256": claim_accountability.source_sha256,
        "candidate_sha256": claim_accountability.candidate_sha256,
        "claims": sorted(
            (claim.model_dump(mode="json") for claim in claim_accountability.claims),
            key=lambda claim: (claim["source_byte_start"], claim["claim_id"]),
        ),
    }
    return _canonical_hash(payload)


def _valid_claims_and_gaps(
    claim_accountability: ReadmeClaimAccountabilityMapV1,
    product_facts: ProductFactsV2,
) -> tuple[list[ReadmeClaimAccountabilityV1], list[tuple[ReadmeClaimAccountabilityV1, str]]]:
    known_fact_ids = {fact.fact_id for fact in product_facts.facts}
    candidate_claims = [
        claim
        for claim in claim_accountability.claims
        if claim.stage == "candidate" and claim.survives_in_candidate
    ]
    sorted_claims = sorted(
        candidate_claims, key=lambda claim: (claim.source_byte_start, claim.claim_id)
    )
    valid: list[ReadmeClaimAccountabilityV1] = []
    gaps: list[tuple[ReadmeClaimAccountabilityV1, str]] = []
    for claim in sorted_claims:
        missing = sorted(
            fact_id for fact_id in claim.accepted_fact_ids if fact_id not in known_fact_ids
        )
        if missing:
            gaps.append((claim, missing[0]))
        else:
            valid.append(claim)
    return valid, gaps


def _valid_provenance_and_gaps(
    candidate_content_provenance: Sequence[CandidateContentProvenanceV1],
    product_facts: ProductFactsV2,
) -> tuple[list[CandidateContentProvenanceV1], list[tuple[CandidateContentProvenanceV1, str]]]:
    known_fact_ids = {fact.fact_id for fact in product_facts.facts}
    sorted_provenance = sorted(
        candidate_content_provenance,
        key=lambda entry: (entry.candidate_byte_start, entry.provenance_id),
    )
    valid: list[CandidateContentProvenanceV1] = []
    gaps: list[tuple[CandidateContentProvenanceV1, str]] = []
    for entry in sorted_provenance:
        missing = sorted(fact_id for fact_id in entry.fact_ids if fact_id not in known_fact_ids)
        if missing:
            gaps.append((entry, missing[0]))
        else:
            valid.append(entry)
    return valid, gaps


def build_atomic_units(
    candidate_text: str,
    claim_accountability: ReadmeClaimAccountabilityMapV1,
    product_facts: ProductFactsV2,
    candidate_content_provenance: Sequence[CandidateContentProvenanceV1] = (),
) -> tuple[AtomicUnitV1, ...]:
    """Parse ``candidate_text`` into stable, claim-respecting atomic units.

    Deterministic and pure: identical input always produces identical output (redesign point 1),
    and input sequences are normalized by a stable sort key before use regardless of caller-
    supplied order (redesign point 2). Referentially broken claims (an ``accepted_fact_ids`` entry
    absent from ``product_facts``) never affect unit boundaries -- they are excluded from claim-id
    attachment here exactly as they are excluded from packet claim-cluster boundaries in
    ``plan_bounded_review_packets``, since a broken claim's span cannot be trusted for merging.
    """

    raw_units = _build_raw_units(candidate_text)
    byte_offsets = _byte_offset_table(candidate_text)
    valid_claims, _claim_gaps = _valid_claims_and_gaps(claim_accountability, product_facts)
    claim_char_spans = _claim_char_spans(byte_offsets, valid_claims)
    merged = _merge_units_for_claim_spans(raw_units, claim_char_spans)
    _attach_claim_ids(merged, claim_char_spans)
    provenance_char_spans = _provenance_char_spans(byte_offsets, candidate_content_provenance)
    _attach_provenance_ids(merged, provenance_char_spans)
    sections = _group_into_sections(merged)
    _dedupe_section_paths(sections)
    for index, unit in enumerate(merged):
        unit.unit_id = f"unit-{index:04d}-{unit.kind}"
    return tuple(
        AtomicUnitV1(
            unit_id=unit.unit_id,
            kind=unit.kind,
            section_path=unit.section_path,
            char_start=unit.char_start,
            char_end=unit.char_end,
            line_start=unit.line_start,
            line_end=unit.line_end,
            claim_ids=tuple(sorted(set(unit.claim_ids))),
            provenance_ids=tuple(sorted(set(unit.provenance_ids))),
        )
        for unit in merged
    )


def _greedy_group_units(
    units: Sequence[_MutableUnit],
    *,
    budget_chars: int,
    size_fn: Callable[[list[_MutableUnit]], int],
) -> tuple[list[list[_MutableUnit]], list[_MutableUnit]]:
    """Greedily accumulate units, in order, never splitting a unit across groups."""

    groups: list[list[_MutableUnit]] = []
    oversized: list[_MutableUnit] = []
    current: list[_MutableUnit] = []
    for unit in units:
        if size_fn([unit]) > budget_chars:
            if current:
                groups.append(current)
                current = []
            oversized.append(unit)
            continue
        trial = [*current, unit]
        if current and size_fn(trial) > budget_chars:
            groups.append(current)
            current = [unit]
        else:
            current = trial
    if current:
        groups.append(current)
    return groups, oversized


def _build_factual_packets(
    *,
    sections: list[list[_MutableUnit]],
    candidate_text: str,
    candidate_sha256: str,
    product_facts: ProductFactsV2,
    accepted_fact_ids_by_claim: dict[str, tuple[str, ...]],
    do_not_claim_sorted: tuple[dict[str, Any], ...],
    valid_provenance: list[CandidateContentProvenanceV1],
    provenance_char_spans: dict[str, tuple[int, int]],
    budget_chars: int,
    factual_prompt_sha256: str,
    input_contract_hash: str,
) -> tuple[list[BoundedFactualPacketV1], list[UnpacketizableRecordV1]]:
    packets: list[BoundedFactualPacketV1] = []
    unpacketizable: list[UnpacketizableRecordV1] = []
    order = 0

    for group in sections:
        section_path = group[0].section_path
        section_start = group[0].char_start
        section_end = group[-1].char_end
        section_provenance = [
            entry
            for entry in valid_provenance
            if section_start <= provenance_char_spans[entry.provenance_id][0] < section_end
        ]

        def overlapping_provenance(
            unit: _MutableUnit,
            *,
            _section_provenance: list[CandidateContentProvenanceV1] = section_provenance,
        ) -> list[CandidateContentProvenanceV1]:
            return [
                entry
                for entry in _section_provenance
                if unit.char_start < provenance_char_spans[entry.provenance_id][1]
                and provenance_char_spans[entry.provenance_id][0] < unit.char_end
            ]

        factual_units = [unit for unit in group if unit.claim_ids or overlapping_provenance(unit)]
        if not factual_units:
            continue

        def unit_fact_ids(unit: _MutableUnit) -> set[str]:
            ids: set[str] = set()
            for claim_id in unit.claim_ids:
                ids.update(accepted_fact_ids_by_claim.get(claim_id, ()))
            for entry in overlapping_provenance(unit):
                ids.update(entry.fact_ids)
            return ids

        def group_size(units: list[_MutableUnit]) -> int:
            text_len = units[-1].char_end - units[0].char_start
            fact_ids: set[str] = set()
            for unit in units:
                fact_ids.update(unit_fact_ids(unit))
            facts_payload = composition_fact_payloads(product_facts, fact_ids)
            return text_len + len(
                json.dumps(facts_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )

        groups_of_units, oversized = _greedy_group_units(
            factual_units, budget_chars=budget_chars, size_fn=group_size
        )
        for unit in oversized:
            unpacketizable.append(
                UnpacketizableRecordV1(
                    record_id=f"unpacketizable-oversized-factual-{unit.unit_id}",
                    reason="oversized_unit",
                    section_path=section_path,
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                    unit_kind=unit.kind,
                    required_min_budget=group_size([unit]),
                    detail=(
                        f"unit {unit.unit_id!r} in section {section_path!r} exceeds budget_chars "
                        "for factual packing even alone"
                    ),
                )
            )

        for local_index, group_units in enumerate(groups_of_units):
            claim_id_set = {cid for unit in group_units for cid in unit.claim_ids}
            claim_ids_sorted = tuple(sorted(claim_id_set))
            fact_ids: set[str] = set()
            for unit in group_units:
                fact_ids.update(unit_fact_ids(unit))
            facts_payload = tuple(
                sorted(
                    composition_fact_payloads(product_facts, fact_ids),
                    key=lambda item: str(item.get("fact_id", "")),
                )
            )
            provenance_ids_sorted = tuple(
                sorted(
                    {
                        entry.provenance_id
                        for unit in group_units
                        for entry in overlapping_provenance(unit)
                    }
                )
            )
            unit_text = candidate_text[group_units[0].char_start : group_units[-1].char_end]
            covered_unit_ids = tuple(unit.unit_id for unit in group_units)
            # Deliberately excludes candidate_sha256 AND absolute position (char/line
            # start/end): packet_sha256 must depend only on this packet's own local content so
            # that an edit elsewhere in the document cannot invalidate every packet -- either
            # through a whole-document hash embedded in each one, or (subtler) through every
            # downstream packet's absolute offsets shifting when upstream text changes length,
            # even though their own text is byte-identical. Both would defeat selective
            # invalidation by construction. Both are still stored as ordinary fields on the
            # packet itself (below) for echo/staleness validation and human inspection.
            substantive: dict[str, Any] = {
                "facet": "factual",
                "section_path": section_path,
                "unit_text": unit_text,
                "covered_unit_ids": covered_unit_ids,
                "claim_ids": claim_ids_sorted,
                "accepted_fact_ids": tuple(sorted(fact_ids)),
                "facts": facts_payload,
                "do_not_claim": do_not_claim_sorted,
                "provenance_ids": provenance_ids_sorted,
                "prompt_contract_hash": factual_prompt_sha256,
                "input_contract_hash": input_contract_hash,
            }
            packet_sha256 = _packet_sha256(substantive)
            slug = _packet_id_slug(section_path)
            packet_id = f"pkt-factual-{order:04d}-{slug}-{packet_sha256[:12]}"
            stable_slot_id = f"factual:{section_path}:{local_index:02d}"
            packets.append(
                BoundedFactualPacketV1(
                    packet_id=packet_id,
                    stable_slot_id=stable_slot_id,
                    order=order,
                    candidate_sha256=candidate_sha256,
                    char_start=group_units[0].char_start,
                    char_end=group_units[-1].char_end,
                    line_start=group_units[0].line_start,
                    line_end=group_units[-1].line_end,
                    packet_sha256=packet_sha256,
                    **substantive,
                )
            )
            order += 1

    return packets, unpacketizable


def _build_visitor_packets(
    *,
    sections: list[list[_MutableUnit]],
    section_classifications: dict[str, SectionClassificationV1],
    candidate_text: str,
    candidate_sha256: str,
    budget_chars: int,
    neighbor_context_chars: int,
    visitor_prompt_sha256: str,
    input_contract_hash: str,
) -> tuple[list[BoundedVisitorPacketV1], list[UnpacketizableRecordV1]]:
    unpacketizable: list[UnpacketizableRecordV1] = []
    eligible: list[dict[str, Any]] = []

    for group in sections:
        section_path = group[0].section_path
        if section_classifications[section_path].classification == "mechanical_api_inventory":
            continue

        def size_fn(units: list[_MutableUnit]) -> int:
            return units[-1].char_end - units[0].char_start

        groups_of_units, oversized = _greedy_group_units(
            group, budget_chars=budget_chars, size_fn=size_fn
        )
        for unit in oversized:
            unpacketizable.append(
                UnpacketizableRecordV1(
                    record_id=f"unpacketizable-oversized-visitor-{unit.unit_id}",
                    reason="oversized_unit",
                    section_path=section_path,
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                    unit_kind=unit.kind,
                    required_min_budget=unit.char_end - unit.char_start,
                    detail=(
                        f"unit {unit.unit_id!r} in section {section_path!r} exceeds budget_chars "
                        "for visitor packing even alone"
                    ),
                )
            )
        if groups_of_units:
            eligible.append({"section_path": section_path, "subgroups": groups_of_units})

    packets: list[BoundedVisitorPacketV1] = []
    order = 0
    for section_index, spec in enumerate(eligible):
        subgroups = spec["subgroups"]
        for local_index, group_units in enumerate(subgroups):
            section_text = candidate_text[group_units[0].char_start : group_units[-1].char_end]
            before = ""
            after = ""
            if local_index == 0 and section_index > 0:
                prev_group = eligible[section_index - 1]["subgroups"][-1]
                prev_text = candidate_text[prev_group[0].char_start : prev_group[-1].char_end]
                before = prev_text[-neighbor_context_chars:] if neighbor_context_chars > 0 else ""
            if local_index == len(subgroups) - 1 and section_index < len(eligible) - 1:
                next_group = eligible[section_index + 1]["subgroups"][0]
                next_text = candidate_text[next_group[0].char_start : next_group[-1].char_end]
                after = next_text[:neighbor_context_chars] if neighbor_context_chars > 0 else ""
            covered_unit_ids = tuple(unit.unit_id for unit in group_units)
            # See the matching note in _build_factual_packets: candidate_sha256 and absolute
            # position are deliberately excluded from the hashed payload so an unrelated edit
            # elsewhere cannot invalidate this packet; both are still stored as ordinary fields
            # on the packet itself below.
            substantive: dict[str, Any] = {
                "facet": "visitor",
                "section_path": spec["section_path"],
                "section_text": section_text,
                "neighbor_context_before": before,
                "neighbor_context_after": after,
                "covered_unit_ids": covered_unit_ids,
                "prompt_contract_hash": visitor_prompt_sha256,
                "input_contract_hash": input_contract_hash,
            }
            packet_sha256 = _packet_sha256(substantive)
            slug = _packet_id_slug(spec["section_path"])
            packet_id = f"pkt-visitor-{order:04d}-{slug}-{packet_sha256[:12]}"
            stable_slot_id = f"visitor:{spec['section_path']}:{local_index:02d}"
            packets.append(
                BoundedVisitorPacketV1(
                    packet_id=packet_id,
                    stable_slot_id=stable_slot_id,
                    order=order,
                    candidate_sha256=candidate_sha256,
                    char_start=group_units[0].char_start,
                    char_end=group_units[-1].char_end,
                    line_start=group_units[0].line_start,
                    line_end=group_units[-1].line_end,
                    packet_sha256=packet_sha256,
                    **substantive,
                )
            )
            order += 1

    return packets, unpacketizable


def plan_bounded_review_packets(
    *,
    candidate_text: str,
    document_plan: ReadmeDocumentPlanV1,
    claim_accountability: ReadmeClaimAccountabilityMapV1,
    product_facts: ProductFactsV2,
    budget_chars: int,
    factual_prompt_sha256: str,
    visitor_prompt_sha256: str,
    do_not_claim: Sequence[Mapping[str, Any]] = (),
    candidate_content_provenance: Sequence[CandidateContentProvenanceV1] = (),
    neighbor_context_chars: int = DEFAULT_NEIGHBOR_CONTEXT_CHARS,
    api_inventory_heading_keywords: frozenset[str] = DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
    api_inventory_table_fence_threshold: float = DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD,
) -> BoundedReviewPlanV1:
    """Deterministically plan bounded review packets for one candidate.

    Raises ``BoundedReviewInputMismatchError`` on a candidate/facts/plan hash mismatch (a caller
    contract violation). A localized unresolved fact reference on one claim or provenance entry
    never raises -- it becomes an ``UnpacketizableRecordV1`` in the returned plan's
    ``unpacketizable`` list (redesign point 4).
    """

    if budget_chars <= 0:
        raise BoundedReviewInputMismatchError("budget_chars must be positive")

    candidate_sha256 = sha256_hex(candidate_text)
    if candidate_sha256 != document_plan.candidate_sha256:
        raise BoundedReviewInputMismatchError(
            "candidate_text sha256 does not match document_plan.candidate_sha256"
        )
    if candidate_sha256 != claim_accountability.candidate_sha256:
        raise BoundedReviewInputMismatchError(
            "candidate_text sha256 does not match claim_accountability.candidate_sha256"
        )
    facts_hash = product_facts.canonical_hash()
    if document_plan.facts_hash != facts_hash:
        raise BoundedReviewInputMismatchError(
            "document_plan.facts_hash does not match product_facts.canonical_hash()"
        )
    if claim_accountability.facts_hash != facts_hash:
        raise BoundedReviewInputMismatchError(
            "claim_accountability.facts_hash does not match product_facts.canonical_hash()"
        )

    input_contract_hash = sha256_hex(_ALGORITHM_CONTRACT_VERSION)

    valid_claims, claim_gaps = _valid_claims_and_gaps(claim_accountability, product_facts)
    valid_provenance, provenance_gaps = _valid_provenance_and_gaps(
        candidate_content_provenance, product_facts
    )

    raw_units = _build_raw_units(candidate_text)
    byte_offsets = _byte_offset_table(candidate_text)

    unpacketizable: list[UnpacketizableRecordV1] = []
    for claim, missing_fact_id in claim_gaps:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, claim.source_byte_start, claim.source_byte_end
        )
        unpacketizable.append(
            UnpacketizableRecordV1(
                record_id=f"unpacketizable-claim-{claim.claim_id}",
                reason="unresolved_fact_reference",
                section_path=_section_path_at(raw_units, char_start),
                char_start=char_start,
                char_end=char_end if char_end > char_start else char_start + 1,
                claim_id=claim.claim_id,
                missing_fact_id=missing_fact_id,
                detail=(
                    f"claim {claim.claim_id!r} cites unresolved fact id {missing_fact_id!r} not "
                    "present in product_facts"
                ),
            )
        )
    for entry, missing_fact_id in provenance_gaps:
        char_start, char_end = _char_span_from_byte_span(
            byte_offsets, entry.candidate_byte_start, entry.candidate_byte_end
        )
        unpacketizable.append(
            UnpacketizableRecordV1(
                record_id=f"unpacketizable-provenance-{entry.provenance_id}",
                reason="unresolved_fact_reference",
                section_path=_section_path_at(raw_units, char_start),
                char_start=char_start,
                char_end=char_end if char_end > char_start else char_start + 1,
                provenance_id=entry.provenance_id,
                missing_fact_id=missing_fact_id,
                detail=(
                    f"provenance {entry.provenance_id!r} cites unresolved fact id "
                    f"{missing_fact_id!r} not present in product_facts"
                ),
            )
        )

    claim_char_spans = _claim_char_spans(byte_offsets, valid_claims)
    merged_units = _merge_units_for_claim_spans(raw_units, claim_char_spans)
    _attach_claim_ids(merged_units, claim_char_spans)
    all_provenance_spans = _provenance_char_spans(byte_offsets, candidate_content_provenance)
    _attach_provenance_ids(merged_units, all_provenance_spans)
    sections = _group_into_sections(merged_units)
    _dedupe_section_paths(sections)
    for index, unit in enumerate(merged_units):
        unit.unit_id = f"unit-{index:04d}-{unit.kind}"

    section_classifications = _classify_sections(
        sections,
        api_inventory_heading_keywords=api_inventory_heading_keywords,
        api_inventory_table_fence_threshold=api_inventory_table_fence_threshold,
    )

    accepted_fact_ids_by_claim = {
        claim.claim_id: tuple(claim.accepted_fact_ids) for claim in valid_claims
    }
    valid_provenance_char_spans = {
        entry.provenance_id: _char_span_from_byte_span(
            byte_offsets, entry.candidate_byte_start, entry.candidate_byte_end
        )
        for entry in valid_provenance
    }
    do_not_claim_sorted = tuple(
        sorted(
            (dict(item) for item in do_not_claim),
            key=lambda item: str(item.get("fact_id", "")),
        )
    )

    factual_packets, factual_oversized = _build_factual_packets(
        sections=sections,
        candidate_text=candidate_text,
        candidate_sha256=candidate_sha256,
        product_facts=product_facts,
        accepted_fact_ids_by_claim=accepted_fact_ids_by_claim,
        do_not_claim_sorted=do_not_claim_sorted,
        valid_provenance=valid_provenance,
        provenance_char_spans=valid_provenance_char_spans,
        budget_chars=budget_chars,
        factual_prompt_sha256=factual_prompt_sha256,
        input_contract_hash=input_contract_hash,
    )
    visitor_packets, visitor_oversized = _build_visitor_packets(
        sections=sections,
        section_classifications=section_classifications,
        candidate_text=candidate_text,
        candidate_sha256=candidate_sha256,
        budget_chars=budget_chars,
        neighbor_context_chars=neighbor_context_chars,
        visitor_prompt_sha256=visitor_prompt_sha256,
        input_contract_hash=input_contract_hash,
    )
    unpacketizable.extend(factual_oversized)
    unpacketizable.extend(visitor_oversized)
    unpacketizable.sort(key=lambda record: record.record_id)

    plan_hash = _canonical_hash(
        {
            "algorithm_contract_version": _ALGORITHM_CONTRACT_VERSION,
            "candidate_sha256": candidate_sha256,
            "document_plan_candidate_sha256": document_plan.candidate_sha256,
            "facts_hash": facts_hash,
            "claim_accountability_hash": _order_invariant_claim_accountability_hash(
                claim_accountability
            ),
            "budget_chars": budget_chars,
            "neighbor_context_chars": neighbor_context_chars,
        }
    )

    return BoundedReviewPlanV1(
        candidate_sha256=candidate_sha256,
        plan_hash=plan_hash,
        budget_chars=budget_chars,
        factual_packets=tuple(factual_packets),
        visitor_packets=tuple(visitor_packets),
        unpacketizable=tuple(unpacketizable),
    )


def build_coverage_ledger(
    plan: BoundedReviewPlanV1,
    *,
    atomic_units: Sequence[AtomicUnitV1],
    api_inventory_heading_keywords: frozenset[str] = DEFAULT_API_INVENTORY_HEADING_KEYWORDS,
    api_inventory_table_fence_threshold: float = DEFAULT_API_INVENTORY_TABLE_FENCE_THRESHOLD,
) -> CoverageLedgerV1:
    """Prove exhaustive coverage for one plan against its own ``atomic_units``.

    Pass the same ``api_inventory_heading_keywords``/``api_inventory_table_fence_threshold`` used
    to build ``plan`` -- this function recomputes section classification from ``atomic_units``
    rather than reading it back off the plan, since ``BoundedReviewPlanV1`` does not carry
    classification directly (only ``visitor_packets`` absence for excluded sections).
    """

    sections = _group_into_sections(list(atomic_units))
    classifications = _classify_sections(
        sections,
        api_inventory_heading_keywords=api_inventory_heading_keywords,
        api_inventory_table_fence_threshold=api_inventory_table_fence_threshold,
    )

    factual_covering: dict[str, list[str]] = {
        unit.unit_id: [] for unit in atomic_units if unit.claim_ids
    }
    for factual_packet in plan.factual_packets:
        for unit_id in factual_packet.covered_unit_ids:
            if unit_id in factual_covering:
                factual_covering[unit_id].append(factual_packet.packet_id)

    visitor_covering: dict[str, list[str]] = {}
    excluded_spans: list[ExcludedSpanV1] = []
    for unit in atomic_units:
        classification = classifications[unit.section_path]
        if classification.classification == "mechanical_api_inventory":
            excluded_spans.append(
                ExcludedSpanV1(
                    unit_id=unit.unit_id,
                    section_path=unit.section_path,
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                    classification="mechanical_api_inventory",
                    justification=classification.justification,
                )
            )
        else:
            visitor_covering[unit.unit_id] = []
    for visitor_packet_item in plan.visitor_packets:
        for unit_id in visitor_packet_item.covered_unit_ids:
            if unit_id in visitor_covering:
                visitor_covering[unit_id].append(visitor_packet_item.packet_id)

    unit_by_id = {unit.unit_id: unit for unit in atomic_units}
    visitor_spans = tuple(
        CoverageSpanV1(
            unit_id=unit_id,
            section_path=unit_by_id[unit_id].section_path,
            char_start=unit_by_id[unit_id].char_start,
            char_end=unit_by_id[unit_id].char_end,
            unit_kind=unit_by_id[unit_id].kind,
            covering_packet_ids=tuple(sorted(packet_ids)),
        )
        for unit_id, packet_ids in sorted(visitor_covering.items())
    )
    factual_spans = tuple(
        CoverageSpanV1(
            unit_id=unit_id,
            section_path=unit_by_id[unit_id].section_path,
            char_start=unit_by_id[unit_id].char_start,
            char_end=unit_by_id[unit_id].char_end,
            unit_kind=unit_by_id[unit_id].kind,
            covering_packet_ids=tuple(sorted(packet_ids)),
        )
        for unit_id, packet_ids in sorted(factual_covering.items())
    )

    overlaps: list[CoverageOverlapV1] = []
    visitor_by_order = sorted(plan.visitor_packets, key=lambda packet: packet.order)
    for index in range(1, len(visitor_by_order)):
        prev_packet = visitor_by_order[index - 1]
        current_packet = visitor_by_order[index]
        if current_packet.neighbor_context_before:
            overlaps.append(
                CoverageOverlapV1(
                    subject=(
                        f"visitor-neighbor-context:{prev_packet.section_path}"
                        f"->{current_packet.section_path}"
                    ),
                    packet_ids=(prev_packet.packet_id, current_packet.packet_id),
                    reason=(
                        "neighbor context intentionally duplicates the adjacent packet's own "
                        "prose for flow continuity"
                    ),
                )
            )

    return CoverageLedgerV1(
        candidate_sha256=plan.candidate_sha256,
        plan_hash=plan.plan_hash,
        visitor_spans=visitor_spans,
        factual_spans=factual_spans,
        excluded_spans=tuple(excluded_spans),
        overlaps=tuple(overlaps),
        blocking_record_ids=tuple(sorted(record.record_id for record in plan.unpacketizable)),
    )
