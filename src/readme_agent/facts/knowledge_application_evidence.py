"""Build the per-run `knowledge-application.json` evidence artifact: the
auditable answer to "exactly which imported knowledge affected this
candidate, where did it affect it, and why was it trusted?"

Deterministic and cheap (pure file I/O plus in-memory filtering, zero
network/LLM work) -- it recomputes `select_knowledge_claims()` rather than
threading the result through the fact-collection call chain, so it can be
called independently from evidence-writing code without changing that
chain's return contract.

Four distinct, never-conflated stages (Gate R5 of the 2026-08-19
knowledge-to-output pipeline course-correction review -- "evidence records
intent instead of actual influence" was a confirmed defect: the prior
version derived a single `sections_influenced` field from every disposition
carrying an `intended_section`, including claims this run went on to
*reject*, and did so before any document was ever rendered):

* **considered** -- every claim this run examined (`considered_count`,
  `dispositions`). Nothing here implies the claim reached output.
* **selected for planning** -- claims that survived corroboration/
  freshness/relevance gating into a `FactRecordV2`
  (`sections_selected_for_planning`, `fact_fields_produced`). Still not
  proof the renderer used them -- a selected fact can go uncited if the
  agentic composition plan chose not to reference it.
* **influenced** -- sections where a real, *surviving*
  `ReadmeDocumentPlanV1` operation actually cites one of this run's
  selected fact IDs in its own `fact_ids` (`sections_influenced`). Requires
  the caller to pass the real `document_plan` from
  `document_renderer.build_readme_document_candidate()`; when no plan is
  available yet (this evidence is written once at fact-collection time,
  before any candidate has been rendered, and again -- superseding the
  first -- once `readme/idea_candidate.py` has a real plan) this is
  correctly empty, never guessed from intent.
* **rendered output spans** -- the exact operation(s) that carried each
  influencing fact into the candidate (`rendered_output_spans`): operation
  id, section, and the operation's own `replacement_sha256` (the same hash
  `ReadmeDocumentOperationV1` already carries and `document_validation.py`
  already verifies against the rendered candidate bytes -- reused as the
  span's own integrity anchor rather than re-deriving a second, possibly
  drifting, byte range).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from readme_agent.facts.aspose_knowledge_claims import KnowledgeLoadFindingV1
from readme_agent.facts.aspose_knowledge_selection import (
    KnowledgeClaimDispositionV1,
    select_knowledge_claims,
)
from readme_agent.facts.aspose_seo_keyword_facts import (
    SeoKeywordDispositionV1,
    seo_keyword_dispositions,
)
from readme_agent.facts.schema_v2 import descriptive_fact_id
from readme_agent.readme.claim_accountability_coordinates import (
    structured_list_item_coordinate,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1

# The five bounded dispositions a final (post-render) report may assign to
# one output-authorizing imported-knowledge item -- every such item gets
# exactly one, enforced by `KnowledgeApplicationV1._final_dispositions_are_
# internally_consistent` below.
FinalKnowledgeDispositionV1 = Literal[
    "rendered_with_exact_spans",
    "intentionally_omitted_with_evidence",
    "superseded_or_corrected_with_evidence",
    "rejected_before_authorship",
    "not_applicable_with_reason",
]


class RenderedOutputSpanV1(BaseModel):
    """One surviving document-plan operation or candidate-content provenance
    binding that actually carried a selected knowledge fact into the
    rendered candidate. `candidate_byte_start`/`candidate_byte_end` are only
    ever populated for a provenance-sourced span (an operation's own
    replacement lands at a candidate offset this report does not replay
    reconstruction to recover, so `replacement_sha256` -- the operation's
    own replacement-text hash, already verified elsewhere against the
    rendered candidate -- remains that case's span-integrity anchor)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    section: str | None
    operation_id: str
    operation: str
    replacement_sha256: str
    candidate_byte_start: int | None = None
    candidate_byte_end: int | None = None
    fact_coordinates: tuple[StructuredFactCoordinateV1, ...] = ()


class FinalKnowledgeItemDispositionV1(BaseModel):
    """One output-authorizing imported-knowledge item's exactly-one final
    disposition, bound to this exact candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    global_claim_id: str
    fact_field: str | None
    disposition: FinalKnowledgeDispositionV1
    reason: str
    output_spans: tuple[RenderedOutputSpanV1, ...] = ()


class KnowledgeApplicationV1(BaseModel):
    """One repository/run's complete imported-knowledge accountability
    record. Every field here is either read directly off the real
    `KnowledgeSelectionResultV1`/`ReadmeDocumentPlanV1` this run computed,
    or derived from them -- never narrated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 4
    status: Literal["provisional", "final"] = "provisional"
    org_repo: str
    family: str
    platform: str
    source_revision: str | None
    facts_hash: str | None = None
    document_plan_hash: str | None = None
    candidate_sha256: str | None = None
    reviewer_disposition: str | None = None
    imported_bundle_repo_sha: str | None
    freshness: str
    considered_count: int
    selected_count: int
    rejected_count: int
    fact_fields_produced: tuple[str, ...]
    sections_considered: tuple[str, ...]
    sections_selected_for_planning: tuple[str, ...]
    sections_influenced: tuple[str, ...]
    rendered_output_spans: tuple[RenderedOutputSpanV1, ...]
    final_dispositions: tuple[FinalKnowledgeItemDispositionV1, ...] = ()
    load_findings: tuple[KnowledgeLoadFindingV1, ...]
    dispositions: tuple[KnowledgeClaimDispositionV1, ...]
    seo_keyword_dispositions: tuple[SeoKeywordDispositionV1, ...]

    @model_validator(mode="after")
    def _final_dispositions_are_internally_consistent(self) -> KnowledgeApplicationV1:
        considered_claim_ids = {d.global_claim_id for d in self.dispositions}
        seen: set[str] = set()
        for entry in self.final_dispositions:
            if entry.global_claim_id in seen:
                raise ValueError(
                    f"duplicate final disposition attribution: {entry.global_claim_id}"
                )
            seen.add(entry.global_claim_id)
            if entry.global_claim_id not in considered_claim_ids:
                raise ValueError(
                    f"final disposition cites an unknown claim: {entry.global_claim_id}"
                )
            if entry.disposition == "rendered_with_exact_spans" and not entry.output_spans:
                raise ValueError(
                    f"claim {entry.global_claim_id} is rendered_with_exact_spans "
                    "but carries no output_spans"
                )
            if entry.disposition == "rendered_with_exact_spans" and any(
                not span.fact_coordinates for span in entry.output_spans
            ):
                raise ValueError(
                    f"claim {entry.global_claim_id} is rendered_with_exact_spans "
                    "but a cited span has no exact fact coordinate"
                )
            if entry.disposition != "rendered_with_exact_spans" and not entry.reason.strip():
                raise ValueError(f"claim {entry.global_claim_id} has no omission/rejection reason")
        if self.status == "final":
            rendered_coordinates = {
                coordinate
                for span in self.rendered_output_spans
                for coordinate in span.fact_coordinates
            }
            dispositioned_rendered_coordinates = {
                coordinate
                for entry in self.final_dispositions
                if entry.disposition == "rendered_with_exact_spans"
                for span in entry.output_spans
                for coordinate in span.fact_coordinates
            }
            unaccounted = rendered_coordinates - dispositioned_rendered_coordinates
            if unaccounted:
                raise ValueError(
                    f"rendered output span(s) unaccounted for by any disposition: {unaccounted}"
                )
        return self


def _selected_claim_coordinates(result) -> dict[str, StructuredFactCoordinateV1]:
    """Bind each selected knowledge claim to its exact structured fact item."""

    coordinates: dict[str, StructuredFactCoordinateV1] = {}
    for fact in result.fact_records:
        if not isinstance(fact.value, list):
            continue
        for item in fact.value:
            if not isinstance(item, dict):
                continue
            claim_id = item.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id:
                continue
            coordinates[claim_id] = structured_list_item_coordinate(
                fact.fact_id,
                fact.field,
                item,
            )
    return coordinates


def _output_authorizing(disposition: KnowledgeClaimDispositionV1) -> bool:
    """An item may authorize output only when it is accepted AND its own
    item-level polarity/qualification (`corroboration`) -- not
    `verification_state` alone -- is genuinely corroborated. Re-checked here,
    defensively, rather than trusting an upstream aggregate: this is the
    exact false-positive shape `d11ac3800` closed (a claim's field-level
    `verification_state` can read "verified" while the item's own evidence
    was never actually re-corroborated at this call site)."""

    return (
        disposition.accepted
        and disposition.verification_state == "verified"
        and disposition.corroboration == "corroborated"
    )


def _final_dispositions(
    dispositions: tuple[KnowledgeClaimDispositionV1, ...],
    claim_coordinates: dict[str, StructuredFactCoordinateV1],
    rendered_output_spans: tuple[RenderedOutputSpanV1, ...],
    *,
    status: Literal["provisional", "final"],
) -> tuple[FinalKnowledgeItemDispositionV1, ...]:
    spans_by_coordinate: dict[StructuredFactCoordinateV1, list[RenderedOutputSpanV1]] = {}
    for span in rendered_output_spans:
        for coordinate in span.fact_coordinates:
            spans_by_coordinate.setdefault(coordinate, []).append(span)

    entries: list[FinalKnowledgeItemDispositionV1] = []
    for disposition in dispositions:
        field = disposition.resulting_fact_field
        if not disposition.accepted:
            entries.append(
                FinalKnowledgeItemDispositionV1(
                    global_claim_id=disposition.global_claim_id,
                    fact_field=field,
                    disposition="rejected_before_authorship",
                    reason=disposition.rejection_reason or "rejected during knowledge selection",
                )
            )
            continue
        # Proof by actual usage always wins first, regardless of this item's
        # own verification_state/corroboration: a real, surviving operation
        # or candidate-content provenance binding citing this field's fact_id
        # is definitive, first-hand evidence the pipeline treated it as
        # output-authorizing -- the item-level re-check below governs
        # categorization only for items that were NOT demonstrably rendered.
        selected_coordinate = claim_coordinates.get(disposition.global_claim_id)
        spans = (
            spans_by_coordinate.get(selected_coordinate, [])
            if selected_coordinate is not None
            else []
        )
        if spans:
            entries.append(
                FinalKnowledgeItemDispositionV1(
                    global_claim_id=disposition.global_claim_id,
                    fact_field=field,
                    disposition="rendered_with_exact_spans",
                    reason="cited by a surviving document operation or candidate-content "
                    "provenance binding",
                    output_spans=tuple(spans),
                )
            )
            continue
        if not _output_authorizing(disposition):
            # Accepted but not output-authorizing (e.g. the split
            # `aspose-knowledge-supporting` unverified sibling `d11ac3800`
            # introduced) -- never reaches composition as an authorizing
            # fact, so it is not applicable to this report's disposition
            # vocabulary rather than falsely claimed rejected or omitted.
            # This is exactly where a false-positive format/feature fact
            # would be caught: `verification_state == "verified"` alone is
            # never trusted -- `corroboration == "corroborated"` (the real,
            # item-level polarity signal `d11ac3800` produced) is required too.
            entries.append(
                FinalKnowledgeItemDispositionV1(
                    global_claim_id=disposition.global_claim_id,
                    fact_field=field,
                    disposition="not_applicable_with_reason",
                    reason=(
                        f"accepted but not output-authorizing: verification_state="
                        f"{disposition.verification_state!r}, corroboration="
                        f"{disposition.corroboration!r}"
                    ),
                )
            )
            continue
        if status != "final":
            entries.append(
                FinalKnowledgeItemDispositionV1(
                    global_claim_id=disposition.global_claim_id,
                    fact_field=field,
                    disposition="not_applicable_with_reason",
                    reason="provisional report has no document plan yet; final disposition "
                    "is decided only by the post-render report",
                )
            )
            continue
        entries.append(
            FinalKnowledgeItemDispositionV1(
                global_claim_id=disposition.global_claim_id,
                fact_field=field,
                disposition="intentionally_omitted_with_evidence",
                reason="available to composition (accepted_composition_fact_ids) but not "
                "cited by any surviving operation or candidate-content provenance binding",
            )
        )
    return tuple(entries)


def build_knowledge_application_report(
    org_repo: str,
    family: str,
    platform: str,
    *,
    data_root: Path,
    seo_data_root: Path | None = None,
    clone_cache: Path,
    source_revision: str | None,
    document_plan: ReadmeDocumentPlanV1 | None = None,
    candidate_text: str | None = None,
    status: Literal["provisional", "final"] = "provisional",
    reviewer_disposition: str | None = None,
) -> KnowledgeApplicationV1:
    result = select_knowledge_claims(
        family,
        platform,
        data_root=data_root,
        clone_cache=clone_cache,
        source_revision=source_revision,
    )
    fact_fields = tuple(sorted({fact.field for fact in result.fact_records}))
    field_fact_ids = {
        field: descriptive_fact_id(field, "aspose-knowledge") for field in fact_fields
    }
    claim_coordinates = _selected_claim_coordinates(result)
    sections_considered = tuple(
        sorted({d.intended_section for d in result.dispositions if d.intended_section})
    )
    sections_selected_for_planning = tuple(
        sorted(
            {d.intended_section for d in result.dispositions if d.accepted and d.intended_section}
        )
    )

    rendered_output_spans: tuple[RenderedOutputSpanV1, ...] = ()
    sections_influenced: tuple[str, ...] = ()
    candidate_bytes = candidate_text.encode("utf-8") if candidate_text is not None else None
    if document_plan is not None:
        spans: list[RenderedOutputSpanV1] = []
        influenced: set[str] = set()
        field_by_fact_id = {fact_id: field for field, fact_id in field_fact_ids.items()}
        section_by_field = {
            d.resulting_fact_field: d.intended_section
            for d in result.dispositions
            if d.accepted and d.resulting_fact_field is not None and d.intended_section
        }
        for operation in document_plan.operations:
            for fact_id in operation.fact_ids:
                field = field_by_fact_id.get(fact_id)
                if field is None:
                    continue
                section = section_by_field.get(field)
                spans.append(
                    RenderedOutputSpanV1(
                        fact_id=fact_id,
                        section=section,
                        operation_id=operation.operation_id,
                        operation=operation.operation,
                        replacement_sha256=operation.replacement_sha256,
                    )
                )
                if section is not None:
                    influenced.add(section)
        # Verified-template production commonly carries its real per-fact
        # lineage only in `candidate_content_provenance` -- its own compile
        # operation cites no `fact_ids` at all. Scanning operations alone
        # would silently report zero influence for that whole route.
        if candidate_bytes is not None:
            for provenance in document_plan.candidate_content_provenance:
                for fact_id in provenance.fact_ids:
                    field = field_by_fact_id.get(fact_id)
                    if field is None:
                        continue
                    section = section_by_field.get(field)
                    span_bytes = candidate_bytes[
                        provenance.candidate_byte_start : provenance.candidate_byte_end
                    ]
                    spans.append(
                        RenderedOutputSpanV1(
                            fact_id=fact_id,
                            section=section,
                            operation_id=provenance.provenance_id,
                            operation="verified_template_provenance",
                            replacement_sha256=sha256_hex(span_bytes),
                            candidate_byte_start=provenance.candidate_byte_start,
                            candidate_byte_end=provenance.candidate_byte_end,
                            fact_coordinates=tuple(
                                coordinate
                                for coordinate in provenance.fact_coordinates
                                if coordinate.fact_id == fact_id
                            ),
                        )
                    )
                    if section is not None:
                        influenced.add(section)
        rendered_output_spans = tuple(spans)
        sections_influenced = tuple(sorted(influenced))

    final_status: Literal["provisional", "final"] = (
        status if document_plan is not None else ("provisional")
    )
    final_dispositions = _final_dispositions(
        result.dispositions,
        claim_coordinates,
        rendered_output_spans,
        status=final_status,
    )

    seo_dispositions = seo_keyword_dispositions(
        family,
        platform,
        data_root=seo_data_root or data_root,
    )
    return KnowledgeApplicationV1(
        status=final_status,
        org_repo=org_repo,
        family=family,
        platform=platform,
        source_revision=source_revision,
        facts_hash=document_plan.facts_hash if document_plan is not None else None,
        document_plan_hash=(
            sha256_hex(
                json.dumps(
                    document_plan.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            if document_plan is not None
            else None
        ),
        candidate_sha256=document_plan.candidate_sha256 if document_plan is not None else None,
        reviewer_disposition=reviewer_disposition,
        imported_bundle_repo_sha=result.bundle_repo_sha,
        freshness=result.freshness,
        considered_count=len(result.dispositions),
        selected_count=result.selected_count,
        rejected_count=result.rejected_count,
        fact_fields_produced=fact_fields,
        sections_considered=sections_considered,
        sections_selected_for_planning=sections_selected_for_planning,
        sections_influenced=sections_influenced,
        rendered_output_spans=rendered_output_spans,
        final_dispositions=final_dispositions,
        load_findings=result.load_findings,
        dispositions=result.dispositions,
        seo_keyword_dispositions=seo_dispositions,
    )


__all__ = [
    "FinalKnowledgeItemDispositionV1",
    "FinalKnowledgeDispositionV1",
    "KnowledgeApplicationV1",
    "RenderedOutputSpanV1",
    "build_knowledge_application_report",
]
