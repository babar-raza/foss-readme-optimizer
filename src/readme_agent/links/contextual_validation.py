"""Validate contextual bindings, catalog truth, placement, and final ceilings."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.catalog import lookup_verified_target, normalize_target_url
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.occurrences import (
    count_aspose_link_occurrences,
    find_aspose_link_occurrences,
)
from readme_agent.links.terminology import find_enterprise_terminology_findings
from readme_agent.readme.document_structure import parse_headings


class ContextualLinkValidationV1(BaseModel):
    """Deterministic final-candidate contextual-link verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    errors: list[str]


def validate_contextual_link_candidate(
    plan: ContextualLinkPlanV1,
    catalogs: AsposeLinkCatalogSetV1,
    candidate: str,
    facts: ProductFactsV2,
) -> ContextualLinkValidationV1:
    """Fail closed on unverified, duplicated, promotional, or over-budget links."""

    errors: list[str] = []
    if plan.aspose_org_catalog_hash != catalogs.aspose_org.provenance.output_hash:
        errors.append("aspose.org catalog hash changed")
    if plan.aspose_com_catalog_hash != catalogs.aspose_com.provenance.output_hash:
        errors.append("aspose.com catalog hash changed")
    occurrences = find_aspose_link_occurrences(candidate)
    counts = count_aspose_link_occurrences(candidate)
    first_h2 = candidate.find("\n## ")
    candidate_url_counts = Counter(occurrence.normalized_url for occurrence in occurrences)
    binding_url_counts = Counter(
        normalize_target_url(binding.target_url) for binding in plan.bindings
    )
    expected_url_counts = Counter(plan.pre_link_url_counts)
    expected_url_counts.update(binding_url_counts)
    for normalized_url in sorted(set(candidate_url_counts) | set(expected_url_counts)):
        if candidate_url_counts[normalized_url] != expected_url_counts[normalized_url]:
            errors.append(
                "candidate Aspose-link occurrence delta is not owned by its contextual plan: "
                f"{normalized_url}"
            )
    for occurrence in occurrences:
        record = lookup_verified_target(catalogs, occurrence.url)
        if record is None or not record.linkable:
            errors.append(f"candidate contains non-linkable Aspose target: {occurrence.url}")
        if first_h2 < 0 or occurrence.character_start < first_h2:
            errors.append(f"Aspose target appears in the opening: {occurrence.url}")
    if counts.total > plan.budget.max_total:
        errors.append("candidate exceeds total Aspose-link ceiling")
    for domain, maximum in plan.budget.domain_maxima.items():
        if counts.by_parent_domain[domain] > maximum:
            errors.append(f"candidate exceeds {domain} ceiling")
    for surface, maximum in plan.budget.surface_maxima.items():
        if counts.by_surface[surface] > maximum:
            errors.append(f"candidate exceeds {surface} ceiling")
    if counts.repeated_targets:
        errors.append("candidate repeats an Aspose target")
    for binding in plan.bindings:
        record = lookup_verified_target(catalogs, binding.target_url)
        if record is None or not record.linkable:
            errors.append(f"binding target is not linkable: {binding.target_record_id}")
            continue
        if record.record_id != binding.target_record_id:
            errors.append(f"binding record mismatch: {binding.target_record_id}")
        normalized_binding = normalize_target_url(binding.target_url)
        matching = [
            occurrence
            for occurrence in occurrences
            if occurrence.normalized_url == normalized_binding
        ]
        if any(first_h2 < 0 or occurrence.character_start < first_h2 for occurrence in matching):
            errors.append(f"contextual target appears in the opening: {binding.target_url}")
        if len(matching) != 1:
            errors.append(f"binding target must occur exactly once: {binding.target_record_id}")
            continue
        try:
            context_fact = facts.fact_by_id(binding.context_id)
        except KeyError:
            errors.append(f"binding context fact is unknown: {binding.context_id}")
            continue
        if (
            facts.selected_fact_ids.get(context_fact.field) != context_fact.fact_id
            or context_fact.verification_state not in {"verified", "policy_approved"}
            or context_fact.has_unresolved_conflict
        ):
            errors.append(f"binding context fact is not accepted: {binding.context_id}")
            continue
        value = context_fact.value if isinstance(context_fact.value, dict) else {}
        code = str(value.get("code") or "").rstrip()
        code_start = candidate.find(code) if code else -1
        link_start = matching[0].character_start
        matching_sections = [
            heading
            for heading in parse_headings(candidate)
            if heading.level == 2
            and heading.title == binding.section_heading
            and heading.heading_end <= code_start < heading.section_end
        ]
        if (
            code_start < 0
            or link_start <= code_start + len(code)
            or not any(link_start < section.section_end for section in matching_sections)
        ):
            errors.append(
                "binding target is not adjacent after its accepted example: "
                f"{binding.target_record_id}"
            )
    if findings := find_enterprise_terminology_findings(
        candidate,
        enterprise_product_name=plan.enterprise_product_name,
    ):
        errors.extend(f"prohibited Enterprise terminology: {item.excerpt}" for item in findings)
    return ContextualLinkValidationV1(valid=not errors, errors=errors)
