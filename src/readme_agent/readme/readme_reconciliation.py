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

One real gap this module found on first use against a real candidate
(2026-08-19): `replay_operation_origins` (`composition_operation_origins.py`)
tracks per-byte origin by exact `replacement_text == current_text`
equality, which cannot recognize a *reorder* -- `document_section_order.py`'s
`move_exact` pass relocates whole H2 blocks by replacing a large
`candidate_utf8`-space span with a rearranged concatenation of those same
blocks, so every byte the move touches loses origin tracking even though
the content is 100% unchanged, just repositioned. `ExactSourcePlacementV1`
records (and therefore this module's "relocated" bucket from placements
alone) never cover that content. Rather than fix per-byte origin tracking
through a reorder -- real surgery on already-relied-upon lineage machinery,
out of this gate's safe scope -- this module closes the gap the same way a
human auditor would: any remaining unaccounted span whose exact bytes
appear verbatim inside a real `move_exact` operation's own
`replacement_text` is relocated by that operation, attributed to it by
`operation_id`. Anything left over after *that* check is a genuine,
previously-silent loss and still raises.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.readme.document_plan import ReadmeDocumentOperationV1, ReadmeDocumentPlanV1

ReconciliationDisposition = Literal["preserved", "corrected", "relocated", "superseded", "omitted"]

_RELOCATED_BASIS = "relocated_exact_equivalence"


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

    ranges: list[tuple[int, int, ReconciliationDisposition, str | None, str | None]] = []
    for placement in ledger.source_placements:
        disposition: ReconciliationDisposition = (
            "relocated" if placement.placement_basis == _RELOCATED_BASIS else "preserved"
        )
        ranges.append(
            (placement.source_byte_start, placement.source_byte_end, disposition, None, None)
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

    move_operations = [op for op in plan.operations if op.operation == "move_exact"]

    def _explain_gap(
        start: int, end: int
    ) -> tuple[ReconciliationDisposition, str | None, str | None]:
        gap_operation = _covering_operation(start, end)
        if gap_operation is not None:
            return "omitted", gap_operation.operation_id, gap_operation.rationale
        gap_bytes = source_bytes_actual[start:end]
        moved_by = next(
            (op for op in move_operations if gap_bytes in op.replacement_text.encode("utf-8")),
            None,
        )
        if moved_by is not None:
            return "relocated", moved_by.operation_id, moved_by.rationale
        raise ValueError(
            f"unaccounted source loss: bytes [{start}, {end}) are not covered by any source "
            "placement or explaining operation"
        )

    entries: list[SourceReconciliationEntryV1] = []
    cursor = 0
    for start, end, disposition, operation_id, rationale in ranges:
        if start > cursor:
            gap_disposition, gap_operation_id, gap_rationale = _explain_gap(cursor, start)
            entries.append(
                SourceReconciliationEntryV1(
                    source_byte_start=cursor,
                    source_byte_end=start,
                    disposition=gap_disposition,
                    operation_id=gap_operation_id,
                    rationale=gap_rationale,
                )
            )
        entries.append(
            SourceReconciliationEntryV1(
                source_byte_start=start,
                source_byte_end=end,
                disposition=disposition,
                operation_id=operation_id,
                rationale=rationale,
            )
        )
        cursor = end
    if cursor < ledger.source_bytes:
        gap_disposition, gap_operation_id, gap_rationale = _explain_gap(cursor, ledger.source_bytes)
        entries.append(
            SourceReconciliationEntryV1(
                source_byte_start=cursor,
                source_byte_end=ledger.source_bytes,
                disposition=gap_disposition,
                operation_id=gap_operation_id,
                rationale=gap_rationale,
            )
        )

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
