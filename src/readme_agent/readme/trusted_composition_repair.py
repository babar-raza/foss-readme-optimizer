"""Repair one rejected trusted README section without reopening accepted batches."""

from __future__ import annotations

import json

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.trusted_composition import finalize_trusted_composition
from readme_agent.readme.trusted_composition_batching import (
    TrustedCompositionBatch,
    build_trusted_composition_batches,
)
from readme_agent.readme.trusted_composition_execution import compose_trusted_batch
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
    TrustedReadmeDraftSegmentV1,
    TrustedReadmeSectionRepairRequestV1,
    TrustedReadmeSectionToolDraftV1,
)


def repair_trusted_composition_section(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    prior: TrustedReadmeCompositionOutputV1,
    request: TrustedReadmeSectionRepairRequestV1,
    *,
    client: ForcedToolClient,
) -> TrustedReadmeCompositionOutputV1:
    """Replace exactly one hash-bound batch and preserve every accepted draft by hash."""

    if request.org_repo != graph.org_repo or prior.org_repo != graph.org_repo:
        raise LLMError("trusted repair inputs belong to different repositories")
    if request.source_revision != graph.source_revision:
        raise LLMError("trusted repair request source revision is stale")
    drafts = {draft.batch_id: draft for draft in prior.plan.section_drafts}
    rejected = drafts.get(request.rejected_batch_id)
    if rejected is None:
        raise LLMError("trusted repair references an unknown batch")
    if rejected.canonical_hash() != request.rejected_draft_sha256:
        raise LLMError("trusted repair rejected-draft checksum does not match")
    accepted_hashes = {
        draft.canonical_hash()
        for batch_id, draft in drafts.items()
        if batch_id != request.rejected_batch_id
    }
    if accepted_hashes != set(request.accepted_section_sha256s):
        raise LLMError("trusted repair accepted-section hashes are incomplete or stale")
    batches = {
        batch.batch_id: batch
        for batch in build_trusted_composition_batches(graph, prior.plan.envelope)
    }
    rejected_batch = batches.get(request.rejected_batch_id)
    if rejected_batch is None:
        raise LLMError("trusted repair batch cannot be reconstructed")
    rejected_segments = tuple(
        segment
        for segment in rejected.segments
        if segment.segment_id in request.rejected_segment_ids
    )
    editable_batch = _editable_repair_batch(rejected_batch, rejected_segments)
    repair_hint = " ".join(
        (
            "Repair only the editable segments below and return each listed segment_id exactly.",
            "Deterministic merge code preserves every unlisted sibling segment.",
            "Editable segment records:",
            json.dumps(
                [segment.model_dump(mode="json") for segment in rejected_segments],
                sort_keys=True,
                ensure_ascii=False,
            ),
            "Apply only these grounded findings:",
            "; ".join(request.repair_instructions),
        )
    )
    repaired_tool, repaired_bound = compose_trusted_batch(
        graph.org_repo,
        editable_batch,
        prior.plan.envelope,
        client,
        initial_repair_hint=repair_hint,
        required_segment_ids=request.rejected_segment_ids,
    )
    available_replacements = list(repaired_bound.segments)
    selected_replacements = {}
    for segment in rejected.segments:
        if segment.segment_id not in request.rejected_segment_ids:
            continue
        replacement = _select_repaired_segment(segment, available_replacements)
        selected_replacements[segment.segment_id] = replacement.model_copy(
            update={"segment_id": segment.segment_id}
        )
        available_replacements.remove(replacement)
    merged_segments = tuple(
        selected_replacements.get(segment.segment_id, segment) for segment in rejected.segments
    )
    repaired_inventory = {item.fact_id: item for item in repaired_bound.source_inventory}
    merged_inventory = tuple(
        repaired_inventory.get(item.fact_id, item) for item in rejected.source_inventory
    )
    repaired_bound = repaired_bound.model_copy(
        update={
            "source_inventory": merged_inventory,
            "segments": merged_segments,
        }
    )
    repaired_tool = TrustedReadmeSectionToolDraftV1(
        editorial_summary=repaired_bound.editorial_summary,
        complete=True,
        source_inventory=repaired_bound.source_inventory,
        segments=merged_segments,
    )
    tool_drafts: list[TrustedReadmeSectionToolDraftV1] = []
    bound_drafts = []
    for draft in prior.plan.section_drafts:
        if draft.batch_id == request.rejected_batch_id:
            tool_drafts.append(repaired_tool)
            bound_drafts.append(repaired_bound)
        else:
            tool_drafts.append(
                TrustedReadmeSectionToolDraftV1(
                    editorial_summary=draft.editorial_summary,
                    complete=True,
                    source_inventory=draft.source_inventory,
                    segments=draft.segments,
                )
            )
            bound_drafts.append(draft)
    return finalize_trusted_composition(
        graph,
        source_text,
        prior.plan.envelope,
        tool_drafts,
        bound_drafts,
        llm_call_count=prior.llm_call_count + repaired_bound.attempt_count,
        protected_candidate=prior.candidate_markdown,
    )


def _editable_repair_batch(
    batch: TrustedCompositionBatch,
    segments: tuple[TrustedReadmeDraftSegmentV1, ...],
) -> TrustedCompositionBatch:
    """Restrict repair validation to provenance owned by editable segments."""

    fact_ids = {fact_id for segment in segments for fact_id in segment.inherited_fact_ids}
    standard_ids = {
        standard_id for segment in segments for standard_id in segment.configured_standard_ids
    }
    source_items = tuple(item for item in batch.source_items if item.fact_id in fact_ids)
    standards = tuple(
        standard for standard in batch.configured_standards if standard.standard_id in standard_ids
    )
    if not source_items and not standards:
        raise LLMError("trusted repair segments have no editable provenance")
    return TrustedCompositionBatch(
        batch_id=batch.batch_id,
        source_items=source_items,
        configured_standards=standards,
        global_structures_allowed=bool(standards),
    )


def _select_repaired_segment(
    original: TrustedReadmeDraftSegmentV1,
    candidates: list[TrustedReadmeDraftSegmentV1],
) -> TrustedReadmeDraftSegmentV1:
    """Select the one exact identity required by the repair contract."""

    exact = [candidate for candidate in candidates if candidate.segment_id == original.segment_id]
    if not exact:
        raise LLMError(f"trusted repair omitted rejected segment ID: {original.segment_id}")
    if len(exact) > 1:
        raise LLMError(f"trusted repair segment ownership is ambiguous: {original.segment_id}")
    return exact[0]
