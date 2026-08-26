"""Reauthor only reviewer-rejected bounded prose clusters."""

from __future__ import annotations

from dataclasses import replace

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_capability_precedence import (
    section_specs_without_superseded_capability_authoring,
)
from readme_agent.readme.section_authoring_specs import build_canonical_section_authoring_specs
from readme_agent.specialists.independent_readme_review import IndependentReadmeReviewResultV1
from readme_agent.specialists.readme_repair_validation import repair_findings
from readme_agent.specialists.section_authoring_cache import default_section_authoring_cache_dir
from readme_agent.specialists.section_authoring_contracts import SectionAuthoringDocumentV1
from readme_agent.specialists.section_authoring_document import author_and_persist_readme_sections
from readme_agent.specialists.section_cluster_authoring import SectionClusterAuthorClientLike

_REVIEW_SECTION_TO_AUTHORING_SLOT = {
    "summary": "summary",
    "front-matter": "summary",
    "key-capabilities": "key_capabilities",
    "capabilities": "key_capabilities",
    "installation": "installation",
    "quick-start": "quick_start",
    "scope-and-limitations": "scope_and_limitations",
    "limitations": "scope_and_limitations",
}


def _slot(value: str) -> str | None:
    return _REVIEW_SECTION_TO_AUTHORING_SLOT.get(value.strip().casefold().replace("_", "-"))


def _repair_specs(
    facts: ProductFactsV2,
    review: IndependentReadmeReviewResultV1,
    source_text: str,
):
    by_slot: dict[str, list] = {}
    for finding in repair_findings(review):
        slot = _slot(finding.section)
        if slot is not None:
            by_slot.setdefault(slot, []).append(finding)
    # Apply the same capability-precedence decision the first authoring pass made,
    # or a reviewer-driven repair would silently reinstate a cluster the source's
    # own fact-bound bullets supersede and recreate the duplicate section.
    specs = section_specs_without_superseded_capability_authoring(
        build_canonical_section_authoring_specs(facts),
        source_text,
        facts,
    )
    repaired = []
    for spec in specs:
        findings = by_slot.get(spec.section_id)
        if not findings:
            repaired.append(spec)
            continue
        directives = " ".join(dict.fromkeys(item.required_repair.strip() for item in findings))
        current = "\n\n".join(
            dict.fromkeys(item.quoted_candidate_span.strip() for item in findings)
        )
        repaired.append(
            replace(
                spec,
                section_objective=(
                    f"{spec.section_objective} Independent review requires this correction: "
                    f"{directives} Rewrite only this section's visitor-facing prose, preserve "
                    "every cited fact, and do not mention review or verification."
                ),
                current_source_text=current,
            )
        )
    # Report only slots that still have a spec: a reviewer finding against a
    # superseded capability cluster is answered by not authoring it at all, and
    # counting it here would spend a provider call that can change nothing.
    return tuple(repaired), frozenset(by_slot) & {spec.section_id for spec in repaired}


def reauthor_rejected_sections(
    *,
    org_repo: str,
    source_revision: str,
    source_text: str,
    product_facts_v2: dict,
    prior_document: dict | None,
    review: IndependentReadmeReviewResultV1,
    client: SectionClusterAuthorClientLike | None,
) -> SectionAuthoringDocumentV1 | None:
    """Reuse unchanged clusters and call Qwen only for mapped rejected prose slots."""

    if prior_document is None:
        return None
    previous = SectionAuthoringDocumentV1.model_validate(prior_document)
    facts = ProductFactsV2.model_validate(product_facts_v2)
    specs, affected_slots = _repair_specs(facts, review, source_text)
    if not affected_slots:
        return previous
    if client is None:
        raise RuntimeError("section-authoring repair requires the governed author client")
    org, repo = org_repo.split("/", maxsplit=1)
    return author_and_persist_readme_sections(
        org_repo=org_repo,
        source_revision=source_revision,
        source_text=source_text,
        product_facts=facts,
        protected_content=fingerprint_protected_content(source_text),
        section_specs=specs,
        client=client,
        cache_dir=default_section_authoring_cache_dir(org, repo, source_revision),
    )


def bind_section_authoring_to_render(
    render_result: dict,
    document: SectionAuthoringDocumentV1 | None,
) -> None:
    """Preserve exact section-authoring call accounting on a repaired render."""

    if document is None:
        return
    render_result["section_authoring_document"] = document.model_dump(mode="json")
    render_result["section_authoring_provider_calls"] = document.provider_logical_calls
    render_result["section_authoring_reused_clusters"] = document.reused_cluster_count
    if not document.provider_logical_calls:
        return
    render_result["llm_called"] = True
    render_result["llm_calls"] = [
        *render_result.get("llm_calls", []),
        *[
            {
                "job": "section_cluster_authoring",
                "model": outcome.receipt.provider_model,
                "prompt_sha256": outcome.receipt.prompt_sha256,
                "input_sha256": outcome.packet_hash,
            }
            for outcome in document.outcomes
            if not outcome.reused_from_cache
        ],
    ]


__all__ = ["bind_section_authoring_to_render", "reauthor_rejected_sections"]
