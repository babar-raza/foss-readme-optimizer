"""Repair one rejected trusted README section without reopening accepted batches."""

from __future__ import annotations

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.trusted_composition import finalize_trusted_composition
from readme_agent.readme.trusted_composition_batching import build_trusted_composition_batches
from readme_agent.readme.trusted_composition_execution import compose_trusted_batch
from readme_agent.readme.trusted_composition_models import (
    TrustedReadmeCompositionOutputV1,
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
    repair_hint = (
        "Repair only this rejected batch. Preserve all inherited meaning and obey configured "
        "standards. Findings: " + "; ".join(request.repair_instructions)
    )
    repaired_tool, repaired_bound = compose_trusted_batch(
        graph.org_repo,
        rejected_batch,
        prior.plan.envelope,
        client,
        initial_repair_hint=repair_hint,
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
    )
