"""Validate a section-authoring document against its candidate dependencies."""

from __future__ import annotations

import hashlib

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.agentic_composition_validation import validate_readme_composition_plan
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.specialists.section_authoring_contracts import SectionAuthoringDocumentV1


def validate_section_authoring_document(
    document: SectionAuthoringDocumentV1 | dict | None,
    *,
    org_repo: str,
    source_text: str,
    base_revision: str,
    facts: ProductFactsV2,
) -> SectionAuthoringDocumentV1 | None:
    """Return an exact dependency-bound document or fail before rendering."""

    if document is None:
        return None
    validated = SectionAuthoringDocumentV1.model_validate(document)
    if not validated.complete:
        raise ValueError("incomplete section authoring cannot enter candidate rendering")
    if validated.org_repo != org_repo:
        raise ValueError("section authoring document belongs to a different repository")
    if validated.source_revision != base_revision:
        raise ValueError("section authoring document source revision changed")
    if validated.facts_hash != facts.canonical_hash():
        raise ValueError("section authoring document facts changed")
    if validated.source_sha256 != hashlib.sha256(source_text.encode("utf-8")).hexdigest():
        raise ValueError("section authoring document source README changed")
    if (
        validated.protected_literal_hash
        != fingerprint_protected_content(source_text).maintainer_region_hash
    ):
        raise ValueError("section authoring document protected-content fingerprint changed")
    return validated


def validate_candidate_authoring_inputs(
    *,
    agentic_composition_plan: dict | None,
    section_authoring_document: SectionAuthoringDocumentV1 | dict | None,
    org_repo: str,
    composition_source_text: str,
    section_source_text: str,
    base_revision: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
) -> tuple[ReadmeAgenticCompositionPlanV1 | None, SectionAuthoringDocumentV1 | None]:
    """Validate both agentic inputs before deterministic candidate composition."""

    plan = (
        validate_readme_composition_plan(
            agentic_composition_plan,
            org_repo=org_repo,
            source_text=composition_source_text,
            facts=facts,
            assessment=assessment,
        )
        if agentic_composition_plan
        else None
    )
    document = validate_section_authoring_document(
        section_authoring_document,
        org_repo=org_repo,
        source_text=section_source_text,
        base_revision=base_revision,
        facts=facts,
    )
    return plan, document


__all__ = ["validate_candidate_authoring_inputs", "validate_section_authoring_document"]
