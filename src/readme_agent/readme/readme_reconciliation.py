"""Derive a five-bucket README reconciliation report (preserved / corrected
/ relocated / superseded / omitted) from a real candidate's own
`ReadmeCompositionLedgerV1` and operations -- Gate R6 of the 2026-08-19
knowledge-to-output pipeline course-correction review.

This is pure derivation, not new extraction or parsing machinery: the
composition ledger (`composition_lineage.py::build_composition_ledger`,
wired into every real candidate by `document_plan_finalizer.py` and
`verified_template_document.py`) already proves, byte-exactly and
hash-verified, that every candidate byte traces to one typed origin and
that no source byte is placed in the candidate more than once. What it does
not do on its own is give every ORIGINAL source byte an accounted
disposition in the vocabulary reviewers actually need -- a source span this
module cannot explain through a real placement or a real fact-correction/
policy-correction operation is a genuine, previously-silent loss, and this
module fails closed on it (raises) rather than reporting an incomplete
reconciliation.

Mapping (grounded in what the ledger's own typed vocabulary already means,
confirmed against real candidates, not invented):

* **relocated** -- an `ExactSourcePlacementV1` whose `placement_basis` is
  `relocated_exact_equivalence` (the model's own literal name for exactly
  this).
* **preserved** -- every other placement basis (`structural_exact_
  equivalence`, `operation_unchanged_exact`, `no_op_whole_source`,
  `composer_inserted_exact`): unchanged content, same or composer-placed
  position.
* **corrected** -- a source-space operation whose `protected_content_
  treatment` is `authoritative_fact_correction` (content changed to match a
  verified fact).
* **superseded** -- a source-space operation whose `protected_content_
  treatment` is `presentation_policy_correction` (content replaced or
  removed because a governed presentation policy -- canonical heading
  casing, enterprise terminology, an unresolved claim withheld by policy --
  supersedes it, not because it was factually wrong).
* **omitted** -- a source span covered by neither a placement nor one of
  the two treatments above. Real gaps are still explained by whichever
  operation(s) touch them, if any; a span with no explaining operation at
  all is an unaccounted loss and raises.

A real gap this module found on first use against a real candidate
(2026-08-19, Gate R6a): `replay_operation_origins` (`composition_operation_
origins.py`) tracks per-byte origin by exact `replacement_text ==
current_text` equality, which cannot recognize a *reorder* --
`document_section_order.py`'s `move_exact` pass relocates whole H2 blocks by
replacing a large `candidate_utf8`-space span with a rearranged
concatenation of those same blocks, so every byte the move touches loses
origin tracking even though the content is 100% unchanged, just
repositioned. `ExactSourcePlacementV1` records (and therefore this module's
"relocated" bucket from placements alone) never cover that content.

The 2026-08-19 Stage 3A repair replaced the original stopgap (a raw
`gap_bytes in move_operation.replacement_text` substring-containment check
across the *entire* move replacement -- unsound: no uniqueness/position
check, so a gap could be misattributed to any coincidentally-matching byte
run anywhere in the move, and two distinct gaps whose bytes happened to
match could both silently "explain" the same destination bytes) with two
evidence-backed mechanisms, in priority order, without touching the shared
`replay_operation_origins`/`ExactSourcePlacementV1` replay machinery (real
surgery on that already-relied-upon lineage machinery remains out of this
gate's safe scope):

1. **`plan.source_claim_resolutions`** (`verified_source_claim_resolution_
   engine.py`, already evidence-backed: every resolution requires
   `evidence: list[str]`). A `verified_omission` resolution covering the gap
   yields `omitted` with the resolution's own evidence attached (not a bare
   operation lookup); `verified_equivalence` yields `relocated` with the
   resolution's own `candidate_byte_start`/`candidate_byte_end` as the real,
   evidence-backed destination (no matching needed -- it is already exact);
   `verified_obligation_replacement` yields `corrected` (a governed,
   fact-bound replacement); `authoritative_correction`/`presentation_policy_
   correction` yield `corrected`/`superseded` respectively, matching this
   module's own operation-treatment vocabulary. `deferred_verification`
   resolves nothing definitive and is skipped.
2. **Heading-identity relocation matching** (`_relocated_gap_match`, for
   gaps no claim resolution explains): find the H2 section of `source_text`
   that owns the gap, require the *same-titled* H2 section to exist exactly
   once in the reconstructed final candidate text (rebuilt from the
   ledger's own `segments`, which fully partition `[0, candidate_bytes)` by
   construction -- never a second, parallel text source), and require the
   gap's own bytes to occur exactly once inside that one destination
   block. Scoping the search to the single correctly-identified destination
   section (never the whole move's `replacement_text`, never the whole
   document) and requiring exact-count uniqueness closes both unsoundness
   holes above; an ambiguous or absent match returns `None` and falls
   through to the existing operation-covering check, then the fail-closed
   `raise` -- never a guess.

Anything neither placements, claim resolutions, covering operations, nor
sound heading-identity relocation matching can explain is a genuine,
previously-silent loss and still raises `ValueError`.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.composition_lineage_models import ReadmeCompositionLedgerV1
from readme_agent.readme.document_plan import (
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.document_structure import parse_headings

ReconciliationDisposition = Literal["preserved", "corrected", "relocated", "superseded", "omitted"]

_RELOCATED_BASIS = "relocated_exact_equivalence"

_CLAIM_RESOLUTION_DISPOSITIONS: dict[str, ReconciliationDisposition] = {
    "verified_omission": "omitted",
    "verified_equivalence": "relocated",
    "verified_obligation_replacement": "corrected",
    "authoritative_correction": "corrected",
    "presentation_policy_correction": "superseded",
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceReconciliationEntryV1(_StrictModel):
    """One contiguous, non-overlapping original-source byte span and its
    exact accounted disposition."""

    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(gt=0)
    disposition: ReconciliationDisposition
    operation_id: str | None = None
    rationale: str | None = None
    final_byte_start: int | None = Field(default=None, ge=0)
    final_byte_end: int | None = Field(default=None, ge=0)
    evidence: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def _valid_destination(self) -> SourceReconciliationEntryV1:
        if (self.final_byte_start is None) != (self.final_byte_end is None):
            raise ValueError("a reconciliation destination span requires both byte bounds")
        if (
            self.final_byte_start is not None
            and self.final_byte_end is not None
            and self.final_byte_end <= self.final_byte_start
        ):
            raise ValueError("a reconciliation destination span must be nonempty")
        return self


class ReadmeReconciliationReportV1(_StrictModel):
    """Every original source byte, accounted for exactly once across the
    five dispositions -- `entries` partitions `[0, source_bytes)` with no
    gap and no overlap by construction (proved at build time, not merely
    asserted)."""

    schema_version: int = 1
    source_bytes: int = Field(ge=0)
    entries: tuple[SourceReconciliationEntryV1, ...]
    preserved_count: int = Field(ge=0)
    corrected_count: int = Field(ge=0)
    relocated_count: int = Field(ge=0)
    superseded_count: int = Field(ge=0)
    omitted_count: int = Field(ge=0)


def _source_operations(plan: ReadmeDocumentPlanV1) -> list[ReadmeDocumentOperationV1]:
    return [
        operation
        for operation in plan.operations
        if operation.coordinate_space == "presentation_inner_utf8"
        and operation.source_byte_start != operation.source_byte_end
    ]


def _reconstructed_final_candidate_text(ledger: ReadmeCompositionLedgerV1) -> str:
    """Rebuild the exact final candidate text from the ledger's own segments,
    which fully partition `[0, candidate_bytes)` by construction -- never a
    second, parallel text source. Verified against the ledger's own hash so a
    reconstruction bug fails loudly instead of silently mismatching."""

    ordered_segments = sorted(ledger.segments, key=lambda segment: segment.final_byte_start)
    text = "".join(segment.content_text for segment in ordered_segments)
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != ledger.candidate_sha256:
        raise ValueError("reconstructed final candidate text does not match the ledger's own hash")
    return text


def _relocated_gap_match(
    start: int,
    end: int,
    source_text: str,
    final_candidate_text: str,
    move_operations: list[ReadmeDocumentOperationV1],
) -> tuple[str, str, int, int] | None:
    """Attribute a source gap to a real relocated H2 block, matched by
    heading identity -- never a bare cross-document substring scan. Find
    which H2 section of `source_text` owns `[start, end)`; require the
    *same-titled* H2 section to exist exactly once in `final_candidate_text`
    (ambiguity -- more than one same-titled destination -- is refused, not
    guessed); require the gap's own bytes to occur exactly once inside that
    one destination block (a repeated phrase inside the single correct
    destination is refused too, never silently attributed to the first
    match). Returns `(operation_id, rationale, final_byte_start,
    final_byte_end)` or `None` if no sound, unambiguous match exists."""

    if not move_operations:
        return None
    source_headings = [heading for heading in parse_headings(source_text) if heading.level == 2]
    owning = next(
        (
            heading
            for heading in source_headings
            if len(source_text[: heading.start].encode("utf-8")) <= start
            and end <= len(source_text[: heading.section_end].encode("utf-8"))
        ),
        None,
    )
    if owning is None:
        return None
    candidate_headings = [
        heading for heading in parse_headings(final_candidate_text) if heading.level == 2
    ]
    same_title = [
        heading
        for heading in candidate_headings
        if heading.title.strip().casefold() == owning.title.strip().casefold()
    ]
    if len(same_title) != 1:
        return None
    destination = same_title[0]
    candidate_bytes = final_candidate_text.encode("utf-8")
    dest_start = len(final_candidate_text[: destination.start].encode("utf-8"))
    dest_end = len(final_candidate_text[: destination.section_end].encode("utf-8"))
    dest_block_bytes = candidate_bytes[dest_start:dest_end]
    # A trailing inter-section blank-line separator is boundary formatting, not
    # content the section "carries" -- it does not survive verbatim when a
    # section becomes the last one after a reorder (`_normalize_public_
    # spacing` collapses it). Match on the trimmed core content; the returned
    # destination span covers only that matched core, which may legitimately
    # be shorter than the full source gap `[start, end)` by exactly that
    # trailing whitespace -- not a loss, a real, accounted normalization.
    gap_bytes = source_text.encode("utf-8")[start:end].rstrip(b"\r\n \t")
    if not gap_bytes or dest_block_bytes.count(gap_bytes) != 1:
        return None
    offset = dest_block_bytes.index(gap_bytes)
    final_start = dest_start + offset
    final_end = final_start + len(gap_bytes)
    operation = move_operations[0]
    return operation.operation_id, operation.rationale, final_start, final_end


def _validate_no_destination_overlap(entries: list[SourceReconciliationEntryV1]) -> None:
    """A relocated/verified-equivalence entry's destination bytes must never
    overlap another entry's destination bytes -- the check that makes
    double-counted relocation attribution structurally impossible rather
    than merely unlikely."""

    located = sorted(
        (entry for entry in entries if entry.final_byte_start is not None),
        key=lambda entry: entry.final_byte_start,  # type: ignore[arg-type,return-value]
    )
    for previous, current in zip(located, located[1:], strict=False):
        assert previous.final_byte_end is not None and current.final_byte_start is not None
        if current.final_byte_start < previous.final_byte_end:
            raise ValueError(
                "reconciliation destination ranges overlap: "
                f"[{previous.final_byte_start}, {previous.final_byte_end}) and "
                f"[{current.final_byte_start}, {current.final_byte_end})"
            )


def build_readme_reconciliation_report(
    plan: ReadmeDocumentPlanV1, *, source_text: str
) -> ReadmeReconciliationReportV1:
    """Partition every original source byte into exactly one of five
    buckets. Fails closed: raises `ValueError` if any source span is
    covered by more than one accounted range, or by none at all.

    `source_text` is the same inner (pre-adoption) source text every other
    lineage builder in this module family takes explicitly (see
    `composition_lineage.py::build_composition_ledger`) -- the plan itself
    stores only a hash, never the text, so it must be supplied and is
    verified against `composition_ledger.source_sha256` before use."""

    ledger = plan.composition_ledger
    if ledger is None:
        raise ValueError(
            "cannot reconcile a document plan with no composition_ledger -- every real "
            "candidate must carry one (see composition_lineage.py::build_composition_ledger)"
        )
    source_bytes_actual = source_text.encode("utf-8")
    if hashlib.sha256(source_bytes_actual).hexdigest() != ledger.source_sha256:
        raise ValueError("supplied source_text does not match the composition ledger's own hash")

    # (start, end, disposition, operation_id, rationale, final_byte_start, final_byte_end, evidence)
    _Range = tuple[
        int,
        int,
        ReconciliationDisposition,
        str | None,
        str | None,
        int | None,
        int | None,
        tuple[str, ...] | None,
    ]
    ranges: list[_Range] = []
    for placement in ledger.source_placements:
        disposition: ReconciliationDisposition = (
            "relocated" if placement.placement_basis == _RELOCATED_BASIS else "preserved"
        )
        ranges.append(
            (
                placement.source_byte_start,
                placement.source_byte_end,
                disposition,
                None,
                None,
                placement.final_byte_start,
                placement.final_byte_end,
                None,
            )
        )

    source_operations = _source_operations(plan)
    for operation in source_operations:
        if operation.protected_content_treatment == "authoritative_fact_correction":
            change_disposition: ReconciliationDisposition = "corrected"
        elif operation.protected_content_treatment == "presentation_policy_correction":
            change_disposition = "superseded"
        else:
            continue
        ranges.append(
            (
                operation.source_byte_start,
                operation.source_byte_end,
                change_disposition,
                operation.operation_id,
                operation.rationale,
                None,
                None,
                None,
            )
        )

    ranges.sort(key=lambda item: item[0])
    for previous, current in zip(ranges, ranges[1:], strict=False):
        if current[0] < previous[1]:
            raise ValueError(
                f"reconciliation source ranges overlap: [{previous[0]}, {previous[1]}) and "
                f"[{current[0]}, {current[1]})"
            )

    # Any source-space operation not already placed above (a treatment
    # other than the two source-changing ones, e.g. a withheld-by-policy
    # removal that still needs its own attribution) still explains real
    # loss inside a gap -- checked by overlap, not by requiring an exact
    # span match, since one gap may be explained by more than one
    # operation touching it.
    def _covering_operation(start: int, end: int) -> ReadmeDocumentOperationV1 | None:
        return next(
            (
                op
                for op in source_operations
                if op.source_byte_start <= start and end <= op.source_byte_end
            ),
            None,
        )

    def _covering_claim_resolution(start: int, end: int) -> SourceClaimResolutionV1 | None:
        return next(
            (
                resolution
                for resolution in plan.source_claim_resolutions
                if resolution.resolution in _CLAIM_RESOLUTION_DISPOSITIONS
                and resolution.source_byte_start <= start
                and end <= resolution.source_byte_end
            ),
            None,
        )

    move_operations = [op for op in plan.operations if op.operation == "move_exact"]
    final_candidate_text = _reconstructed_final_candidate_text(ledger)
    # A gap may span more than one H2 section (e.g. an entire multi-section
    # reorder with no placement between the sections yet). Split at heading
    # boundaries before explaining, so heading-identity relocation matching
    # (`_relocated_gap_match`) always sees exactly one owning section per
    # sub-range instead of failing on a span that straddles several.
    heading_boundaries = [
        len(source_text[: heading.start].encode("utf-8"))
        for heading in parse_headings(source_text)
        if heading.level == 2
    ]

    def _explain_gap(start: int, end: int) -> SourceReconciliationEntryV1:
        claim_resolution = _covering_claim_resolution(start, end)
        if claim_resolution is not None:
            return SourceReconciliationEntryV1(
                source_byte_start=start,
                source_byte_end=end,
                disposition=_CLAIM_RESOLUTION_DISPOSITIONS[claim_resolution.resolution],
                operation_id=claim_resolution.claim_id,
                rationale=claim_resolution.rationale,
                final_byte_start=claim_resolution.candidate_byte_start,
                final_byte_end=claim_resolution.candidate_byte_end,
                evidence=tuple(claim_resolution.evidence),
            )
        gap_operation = _covering_operation(start, end)
        if gap_operation is not None:
            return SourceReconciliationEntryV1(
                source_byte_start=start,
                source_byte_end=end,
                disposition="omitted",
                operation_id=gap_operation.operation_id,
                rationale=gap_operation.rationale,
            )
        relocated = _relocated_gap_match(
            start, end, source_text, final_candidate_text, move_operations
        )
        if relocated is not None:
            operation_id, rationale, final_start, final_end = relocated
            return SourceReconciliationEntryV1(
                source_byte_start=start,
                source_byte_end=end,
                disposition="relocated",
                operation_id=operation_id,
                rationale=rationale,
                final_byte_start=final_start,
                final_byte_end=final_end,
            )
        raise ValueError(
            f"unaccounted source loss: bytes [{start}, {end}) are not covered by any source "
            "placement, claim resolution, or explaining operation"
        )

    def _append_gap_entries(
        entries: list[SourceReconciliationEntryV1], start: int, end: int
    ) -> None:
        cuts = sorted({start, end, *(b for b in heading_boundaries if start < b < end)})
        for sub_start, sub_end in zip(cuts, cuts[1:], strict=False):
            entries.append(_explain_gap(sub_start, sub_end))

    entries: list[SourceReconciliationEntryV1] = []
    cursor = 0
    for (
        start,
        end,
        disposition,
        operation_id,
        rationale,
        final_start,
        final_end,
        evidence,
    ) in ranges:
        if start > cursor:
            _append_gap_entries(entries, cursor, start)
        entries.append(
            SourceReconciliationEntryV1(
                source_byte_start=start,
                source_byte_end=end,
                disposition=disposition,
                operation_id=operation_id,
                rationale=rationale,
                final_byte_start=final_start,
                final_byte_end=final_end,
                evidence=evidence,
            )
        )
        cursor = end
    if cursor < ledger.source_bytes:
        _append_gap_entries(entries, cursor, ledger.source_bytes)

    _validate_no_destination_overlap(entries)

    counts: dict[ReconciliationDisposition, int] = {
        "preserved": 0,
        "corrected": 0,
        "relocated": 0,
        "superseded": 0,
        "omitted": 0,
    }
    for entry in entries:
        counts[entry.disposition] += 1

    return ReadmeReconciliationReportV1(
        source_bytes=ledger.source_bytes,
        entries=tuple(entries),
        preserved_count=counts["preserved"],
        corrected_count=counts["corrected"],
        relocated_count=counts["relocated"],
        superseded_count=counts["superseded"],
        omitted_count=counts["omitted"],
    )


__all__ = [
    "ReadmeReconciliationReportV1",
    "ReconciliationDisposition",
    "SourceReconciliationEntryV1",
    "build_readme_reconciliation_report",
]
