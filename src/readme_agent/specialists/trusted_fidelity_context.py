"""Build compact, source-complete context for trusted inheritance review."""

from __future__ import annotations

from typing import Any

from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_models import TrustedReadmeTransformPlanV1

_AUTHORIZED_EFFECTS = {
    "readme.header": "May rewrite the title into one factual H1.",
    "readme.badges": "May add the configured badge row below the H1.",
    "readme.navigation": "May add the configured navigation labels and links.",
    "readme.at_a_glance_mermaid": "May add one configured Mermaid overview.",
    "readme.no_comments": (
        "Must remove HTML comments plus code comments and docstrings while preserving executable "
        "statements; removed comments must never be requested for restoration."
    ),
    "readme.enterprise_edition_terminology": (
        "Must replace inherited commercial, commercial edition, and On-Premise edition labels "
        "with the configured Enterprise Edition term while preserving relationship meaning."
    ),
    "readme.contextual_links": (
        "May remove Markdown link syntax and destinations beyond the configured budget while "
        "preserving useful visible labels and meaning. When forbid_blockquotes is true, it must "
        "remove promotional blockquote placement while representing the useful FOSS and "
        "Enterprise Edition relationship below the opening."
    ),
}


def build_trusted_fidelity_context(
    graph: TrustedReadmeFactGraphV1,
    plan: TrustedReadmeTransformPlanV1,
    *,
    batch_id: str | None = None,
    selected_fact_ids: tuple[str, ...] | None = None,
    addition_evidence_fact_ids: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Remove repeated binding metadata while retaining every review-relevant byte."""

    if selected_fact_ids is not None and batch_id is None:
        raise ValueError("selected trusted fidelity facts require a batch")
    selected_drafts = [
        draft for draft in plan.section_drafts if batch_id is None or draft.batch_id == batch_id
    ]
    if not selected_drafts:
        raise ValueError(f"trusted fidelity batch {batch_id!r} does not exist")
    available_fact_ids = {
        item.fact_id for draft in selected_drafts for item in draft.source_inventory
    }
    selected_fact_id_set = (
        set(selected_fact_ids) if selected_fact_ids is not None else available_fact_ids
    )
    if not selected_fact_id_set or not selected_fact_id_set <= available_fact_ids:
        raise ValueError("trusted fidelity fact selection is empty or outside its batch")
    addition_evidence = set(addition_evidence_fact_ids)
    if not addition_evidence <= available_fact_ids:
        raise ValueError("trusted fidelity addition evidence is outside its batch")
    context_fact_ids = selected_fact_id_set | addition_evidence
    graph_payload = {
        "content_assurance": graph.content_assurance,
        "org_repo": graph.org_repo,
        "source_revision": graph.source_revision,
        "readme_path": graph.readme_path,
        "readme_sha256": graph.readme_sha256,
        "required_source_check_fact_ids": sorted(selected_fact_id_set),
        "review_unsupported_additions": bool(addition_evidence),
        "inherited_units": [
            {
                "fact_id": fact.fact_id,
                "material_kind": fact.material_kind,
                "heading_path": list(fact.heading_path),
                "text": fact.value,
                "instruction_risks": list(fact.instruction_risks),
            }
            for fact in graph.inherited_facts
            if batch_id is None or fact.fact_id in context_fact_ids
        ],
        "configured_standards": [
            {
                "standard_id": standard.standard_id,
                "parameters": standard.parameters,
                "authorized_effect": _AUTHORIZED_EFFECTS[standard.standard_id],
            }
            for standard in graph.configured_standards
        ],
    }
    plan_payload = {
        "content_assurance": plan.content_assurance,
        "org_repo": plan.org_repo,
        "source_revision": plan.source_revision,
        "source_sha256": plan.source_sha256,
        "candidate_sha256": plan.candidate_sha256,
        "source_accountability_complete": plan.source_accountability_complete,
        "batches": [
            {
                "batch_id": draft.batch_id,
                "source_inventory": [
                    {
                        "fact_id": item.fact_id,
                        "action": item.action,
                    }
                    for item in draft.source_inventory
                    if item.fact_id in context_fact_ids
                ],
                "segments": [
                    {
                        "segment_id": segment.segment_id,
                        "kind": segment.kind,
                        "markdown": segment.markdown,
                        "inherited_fact_ids": [
                            fact_id
                            for fact_id in segment.inherited_fact_ids
                            if fact_id in context_fact_ids
                        ],
                        "configured_standard_ids": list(segment.configured_standard_ids),
                    }
                    for segment in draft.segments
                    if any(fact_id in context_fact_ids for fact_id in segment.inherited_fact_ids)
                    or segment.configured_standard_ids
                ],
            }
            for draft in selected_drafts
        ],
    }
    return graph_payload, plan_payload
