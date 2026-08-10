"""Adapt accepted README bytes into the assurance-neutral presentation slots."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.template_schema import (
    BoundTemplateContentV1,
    PresentationTemplateInputV1,
    ProductFactsTemplateDraftV1,
    RepositoryPresentationTemplateV1,
    TemplateContentSource,
    TemplateSlot,
    load_repository_presentation_template,
)
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
)


def _inherited(markdown: str, source_sha256: str) -> BoundTemplateContentV1:
    return BoundTemplateContentV1(
        markdown=markdown,
        source_kind="readme_inherited",
        source_sha256=source_sha256,
    )


def adopt_accepted_reference(
    markdown: str,
    *,
    org_repo: str,
    source_revision: str,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> PresentationTemplateInputV1:
    """Split accepted bytes into structural slots without promoting their factual assurance."""

    contract = template or load_repository_presentation_template()
    if contract.reference_status != "accepted":
        raise ValueError("presentation reference requires current canonical requalification")
    source_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if source_sha256 != contract.accepted_reference_sha256:
        raise ValueError("accepted reference bytes do not match the template provenance hash")
    headings = parse_headings(markdown)
    h1s = [heading for heading in headings if heading.level == 1]
    h2s = [heading for heading in headings if heading.level == 2]
    if len(h1s) != 1 or not h2s:
        raise ValueError("accepted reference must contain one H1 and H2 sections")

    opening = markdown[h1s[0].heading_end : h2s[0].start].strip()
    opening_parts = opening.split("\n\n", 1)
    if len(opening_parts) != 2:
        raise ValueError("accepted reference opening requires one badge row and summary")
    badge_row, summary = opening_parts

    slot_by_heading = {heading.casefold(): slot for slot, heading in contract.headings.items()}
    sections: dict[TemplateSlot, BoundTemplateContentV1] = {}
    for heading in h2s:
        slot = slot_by_heading.get(heading.title.casefold())
        if slot is None or slot == "navigation":
            continue
        body = markdown[heading.heading_end : heading.section_end].strip()
        sections[slot] = _inherited(body, source_sha256)
    return PresentationTemplateInputV1(
        org_repo=org_repo,
        source_revision=source_revision,
        source_line_count=len(markdown.splitlines()),
        profile="extended",
        title=_inherited(h1s[0].title, source_sha256),
        badges=_inherited(badge_row, source_sha256),
        summary=_inherited(summary, source_sha256),
        sections=sections,
    )


def _verified(
    markdown: str,
    fact_fields: list[str],
    facts: ProductFactsV2,
    *,
    standard_ids: list[str] | None = None,
) -> BoundTemplateContentV1:
    fact_ids: list[str] = []
    for field in fact_fields:
        fact = facts.selected_fact(field)
        if (
            fact.verification_state not in {"verified", "policy_approved"}
            or fact.has_unresolved_conflict
        ):
            raise ValueError(f"template field {field!r} is not an accepted selected fact")
        fact_ids.append(fact.fact_id)
    standards = sorted(set(standard_ids or []))
    source_kind: TemplateContentSource = (
        "repository_fact_and_configured_standard"
        if fact_ids and standards
        else "repository_fact"
        if fact_ids
        else "configured_standard"
    )
    return BoundTemplateContentV1(
        markdown=canonicalize_public_markdown(markdown, canonical_abbreviations_from_facts(facts)),
        source_kind=source_kind,
        fact_ids=sorted(set(fact_ids)),
        standard_ids=standards,
    )


def bind_product_facts(
    facts: ProductFactsV2,
    draft: ProductFactsTemplateDraftV1,
    *,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> PresentationTemplateInputV1:
    """Bind verified fact fields to the same structural input used by inherited evidence."""

    contract = template or load_repository_presentation_template()
    expected_slots = set(contract.section_order) - {"navigation"}
    if set(draft.sections) != expected_slots:
        missing = sorted(expected_slots - set(draft.sections))
        extra = sorted(set(draft.sections) - expected_slots)
        raise ValueError(
            "verified template draft must disposition every section; "
            f"missing={missing}, extra={extra}"
        )

    sections: dict[TemplateSlot, BoundTemplateContentV1] = {}
    for slot in contract.section_order:
        if slot == "navigation":
            continue
        content = draft.sections[slot]
        if content.disposition == "omit":
            sections[slot] = BoundTemplateContentV1(
                source_kind="omitted",
                omission_reason=content.omission_reason,
            )
        else:
            sections[slot] = _verified(
                content.markdown,
                content.fact_fields,
                facts,
                standard_ids=content.standard_ids,
            )
    return PresentationTemplateInputV1(
        org_repo=facts.org_repo,
        source_revision=draft.source_revision,
        source_line_count=draft.source_line_count,
        profile=draft.profile,
        title=_verified(
            draft.title.markdown,
            draft.title.fact_fields,
            facts,
            standard_ids=draft.title.standard_ids,
        ),
        badges=_verified(
            draft.badges.markdown,
            draft.badges.fact_fields,
            facts,
            standard_ids=draft.badges.standard_ids,
        ),
        summary=_verified(
            draft.summary.markdown,
            draft.summary.fact_fields,
            facts,
            standard_ids=draft.summary.standard_ids,
        ),
        sections=sections,
    )
