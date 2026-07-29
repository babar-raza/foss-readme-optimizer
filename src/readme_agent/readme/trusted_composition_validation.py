"""Validate and assemble source-accountable trusted README section drafts."""

from __future__ import annotations

import re
from collections import Counter

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_batching import TrustedCompositionBatch
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedReadmeSectionToolDraftV1,
)

_HTML_COMMENT = "<!--"


def _render_batch_candidate(
    draft: TrustedReadmeSectionToolDraftV1,
    batch: TrustedCompositionBatch,
) -> str:
    """Render one batch exactly enough to validate its configured additions."""

    source_by_id = {item.fact_id: item.text for item in batch.source_items}
    rendered: list[str] = []
    for segment in draft.segments:
        if segment.kind == "preserve_exact":
            rendered.append(source_by_id[segment.inherited_fact_ids[0]])
        else:
            rendered.append(segment.markdown)
    return "\n".join(rendered)


def _validate_batch_standard_content(
    draft: TrustedReadmeSectionToolDraftV1,
    batch: TrustedCompositionBatch,
) -> None:
    """Reject a declared standard that the same bounded batch did not materialize."""

    if not batch.global_structures_allowed:
        candidate = _render_batch_candidate(draft, batch)
        if re.search(r"(?m)^# ", candidate) or "```mermaid" in candidate:
            raise LLMError("source-only batch authored a README-global header or Mermaid structure")
    if not batch.configured_standards:
        return
    candidate = _render_batch_candidate(draft, batch)
    candidate_folded = candidate.casefold()
    standards = {item.standard_id: item for item in batch.configured_standards}
    if "readme.header" in standards:
        headings = re.findall(r"(?m)^# (.+?)\s*$", candidate)
        if len(headings) != 1:
            raise LLMError("configured README header requires exactly one H1 in its owning batch")
    if "readme.badges" in standards:
        fragments = [
            str(item)
            for item in standards["readme.badges"].parameters.get("required_fragments", [])
        ]
        if not fragments or any(fragment not in candidate for fragment in fragments):
            raise LLMError("configured badge fragments are absent from their owning batch")
    if "readme.navigation" in standards:
        labels = [
            str(item).casefold()
            for item in standards["readme.navigation"].parameters.get("required_labels", [])
        ]
        if not labels or any(label not in candidate_folded for label in labels):
            raise LLMError("configured README navigation is incomplete in its owning batch")
    if "readme.at_a_glance_mermaid" in standards and candidate.count("```mermaid") != 1:
        raise LLMError(
            "configured at-a-glance Mermaid diagram is absent or duplicated in its owning batch"
        )


def validate_trusted_section_tool_draft(
    draft: TrustedReadmeSectionToolDraftV1,
    batch: TrustedCompositionBatch,
    envelope: TrustedCompositionEnvelopeV1,
) -> None:
    """Reject incomplete, unbound, duplicated, or truncated batch output."""

    expected_facts = [item.fact_id for item in batch.source_items]
    inventory_ids = [item.fact_id for item in draft.source_inventory]
    if Counter(inventory_ids) != Counter(expected_facts):
        raise LLMError("trusted composition inventory omitted or duplicated source facts")
    segment_ids = [segment.segment_id for segment in draft.segments]
    if len(segment_ids) != len(set(segment_ids)):
        raise LLMError("trusted composition returned duplicate segment IDs")
    expected_standards = [item.standard_id for item in batch.configured_standards]
    segment_facts = [
        fact_id for segment in draft.segments for fact_id in segment.inherited_fact_ids
    ]
    segment_standards = [
        standard_id for segment in draft.segments for standard_id in segment.configured_standard_ids
    ]
    if Counter(segment_facts) != Counter(expected_facts):
        counts = Counter(segment_facts)
        missing = [fact_id for fact_id in expected_facts if counts[fact_id] == 0]
        duplicated = sorted(fact_id for fact_id, count in counts.items() if count > 1)
        unknown = sorted(set(segment_facts) - set(expected_facts))
        raise LLMError(
            "trusted composition segment fact binding mismatch: "
            f"missing={missing}; duplicated={duplicated}; unknown={unknown}"
        )
    if Counter(segment_standards) != Counter(expected_standards):
        raise LLMError("trusted composition segments omitted or duplicated configured standards")
    inventory_by_id = {item.fact_id: item for item in draft.source_inventory}
    source_by_id = {item.fact_id: item for item in batch.source_items}
    for segment in draft.segments:
        for fact_id in segment.inherited_fact_ids:
            action = inventory_by_id[fact_id].action
            expected_kind = "preserve_exact" if action == "preserve_exact" else "authored"
            if segment.kind != expected_kind:
                raise LLMError(
                    f"trusted composition action/segment mismatch for {fact_id}: "
                    f"{action} versus {segment.kind}"
                )
            if source_by_id[fact_id].text_truncated_for_context and action != "preserve_exact":
                raise LLMError("context-truncated source facts must be preserved exactly")
        if len(segment.markdown) > envelope.max_output_characters:
            raise LLMError("trusted composition section exceeded the qualified output envelope")
        if _HTML_COMMENT in segment.markdown:
            raise LLMError("trusted composition authored an HTML comment")
    _validate_batch_standard_content(draft, batch)


def assemble_trusted_candidate(
    graph: TrustedReadmeFactGraphV1,
    drafts: list[TrustedReadmeSectionToolDraftV1],
) -> str:
    """Assemble ordered draft segments and copy exact-preserve units from the source graph."""

    facts = {fact.fact_id: fact for fact in graph.inherited_facts}
    rendered: list[str] = []
    for draft in drafts:
        for segment in draft.segments:
            if segment.kind == "preserve_exact":
                rendered.append(facts[segment.inherited_fact_ids[0]].value)
            else:
                rendered.append(segment.markdown.rstrip() + "\n")
    candidate = "\n".join(part.rstrip("\n") for part in rendered if part).strip() + "\n"
    if _HTML_COMMENT in candidate:
        raise LLMError("trusted composition candidate contains an HTML comment")
    return candidate
