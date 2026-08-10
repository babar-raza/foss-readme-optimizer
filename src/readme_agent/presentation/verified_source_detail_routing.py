"""Route valuable unresolved source detail into canonical presentation sections."""

from __future__ import annotations

from collections import defaultdict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_preservation_sections import PreservedBlock
from readme_agent.presentation.verified_source_claim_matching import (
    fact_bound_capability_candidate_claims,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import heading_identity
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding
from readme_agent.readme.source_claim_risk import (
    SourceClaimRiskContext,
    build_source_claim_risk_context,
    classify_source_claim_risk,
)

_TARGETS = {
    "additional_examples": ("Additional Examples", "View Additional Source Examples"),
    "api_public_surface": ("API Reference", "View Additional API Details"),
    "api_structure": ("API Reference", "View Additional API Details"),
    "at_a_glance": ("At a Glance", "View Additional Product Details"),
    "compatibility": ("Installation", "View Additional Compatibility Details"),
    "dependency_requirements": ("Installation", "View Dependency and Extra Details"),
    "contextual_product_relationship": (
        "Scope and Limitations",
        "View Additional Product Scope Details",
    ),
    "development_commands": (
        "Development and Testing",
        "View Additional Development Details",
    ),
    "repository_map": ("Development and Testing", "View Repository Layout Details"),
    "contribution_guidance": ("Contributing", "View Contribution Guidelines"),
    "security_guidance": ("Security", "View Security Implementation Details"),
    "documentation_resources": (
        "Documentation and Resources",
        "View Additional Documentation",
    ),
    "license": ("License", "View Additional License Details"),
    "major_capabilities": ("Key Capabilities", "View Detailed Capabilities"),
    "primary_example": ("Quick Start", "View Additional Quick Start Details"),
    "scope_and_limitations": (
        "Scope and Limitations",
        "View Additional Scope Details",
    ),
    "support_routes": ("Documentation and Resources", "View Additional Support Details"),
    "third_party_notices": ("Third-Party Notices", "View Additional Notices"),
    "verified_installation": ("Installation", "View Additional Installation Details"),
}

_FACT_FIELD_TARGETS = (
    ({"repository.examples", "example.minimal"}, _TARGETS["additional_examples"]),
    (
        {
            "installation.capability_dependencies",
            "installation.coordinates",
            "installation.optional_extras",
            "installation.verified_acquisition",
        },
        _TARGETS["verified_installation"],
    ),
    ({"api.public_surface"}, _TARGETS["api_public_surface"]),
    ({"product.capabilities", "product.formats"}, _TARGETS["major_capabilities"]),
    ({"documentation.links"}, _TARGETS["documentation_resources"]),
    ({"repository.documentation_assets"}, _TARGETS["documentation_resources"]),
    (
        {"development.assets", "development.commands", "development.golden_workflow"},
        _TARGETS["development_commands"],
    ),
)

_GUIDANCE_SECTION_TARGETS = {
    "at-a-glance": _TARGETS["at_a_glance"],
    "documentation-and-resources": _TARGETS["documentation_resources"],
    "installation": _TARGETS["verified_installation"],
    "key-capabilities": _TARGETS["major_capabilities"],
    "quick-start": _TARGETS["primary_example"],
    "scope-and-limitations": _TARGETS["scope_and_limitations"],
}


def _guidance_target_for_source_context(
    source_context: SourceClaimRiskContext,
    source_byte_start: int,
) -> tuple[str, str]:
    """Route verified public guidance by its enclosing source H2."""

    enclosing_h2 = None
    for heading in source_context.headings:
        if heading.start > source_byte_start:
            break
        if heading.level == 2:
            enclosing_h2 = heading
    if enclosing_h2 is None:
        return _TARGETS["at_a_glance"]
    return _GUIDANCE_SECTION_TARGETS.get(
        heading_identity(enclosing_h2.title),
        _TARGETS["at_a_glance"],
    )


def _api_reference_available(facts: ProductFactsV2) -> bool:
    """Return whether accepted facts can render at least one namespace table."""

    try:
        fact = facts.selected_fact("api.public_surface")
    except KeyError:
        return False
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return False
    modules = fact.value.get("modules")
    if isinstance(modules, list) and any(
        isinstance(module, dict)
        and str(module.get("module") or "").strip()
        and isinstance(module.get("exports"), list)
        and bool(module["exports"])
        for module in modules
    ):
        return True
    classes = fact.value.get("classes")
    return isinstance(classes, list) and any(
        isinstance(item, dict)
        and str(item.get("name") or "").strip()
        and str(item.get("module") or "").strip()
        for item in classes
    )


def _target_for_claim(
    source_text: str,
    facts: ProductFactsV2,
    claim: ReadmeMaterialClaimAssessmentV1,
    source_context: SourceClaimRiskContext,
) -> tuple[str, str] | None:
    obligation = classify_source_claim_risk(
        source_text,
        claim,
        context=source_context,
    ).obligation_id
    target = _TARGETS.get(obligation or "")
    if target is not None:
        if target == _TARGETS["api_public_surface"] and not _api_reference_available(facts):
            return None
        return target
    binding = complete_source_claim_fact_binding(source_text, claim, facts)
    if binding is None:
        return None
    fields = {facts.fact_by_id(fact_id).field for fact_id in binding.fact_ids}
    for eligible_fields, fact_target in _FACT_FIELD_TARGETS:
        if fields.intersection(eligible_fields):
            if fact_target == _TARGETS["api_public_surface"] and not _api_reference_available(
                facts
            ):
                return None
            return fact_target
    if "repository.public_guidance" in fields:
        return _guidance_target_for_source_context(source_context, claim.source_byte_start)
    return None


def source_section_routes_to_canonical_contract(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
    source_byte_start: int,
    source_byte_end: int,
) -> bool:
    """Return whether every material leaf in one source section has a canonical home."""

    claims = [
        claim
        for claim in assessment.material_claims
        if source_byte_start <= claim.source_byte_start
        and claim.source_byte_end <= source_byte_end
        and claim.disposition == "preserve"
    ]
    if not claims:
        return False
    source_context = build_source_claim_risk_context(source_text)
    targets = [_target_for_claim(source_text, facts, claim, source_context) for claim in claims]
    if any(target is None for target in targets):
        return False
    source_heading = next(
        (heading for heading in source_context.headings if heading.start == source_byte_start),
        None,
    )
    if source_heading is None:
        return False
    source_identity = heading_identity(source_heading.title)
    return all(
        target is not None and heading_identity(target[0]) != source_identity for target in targets
    )


def route_source_detail_blocks(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
    blocks: list[PreservedBlock],
    candidate_text: str,
    candidate_content_provenance: list[CandidateContentProvenanceV1],
) -> dict[tuple[str, str], list[PreservedBlock]]:
    """Group exact source blocks by their fact-governed canonical destination."""

    claims = {claim.claim_id: claim for claim in assessment.material_claims}
    source_context = build_source_claim_risk_context(source_text)
    routed: dict[tuple[str, str], list[PreservedBlock]] = defaultdict(list)
    candidate_bytes = candidate_text.encode("utf-8")
    candidate_claims = assess_material_claims(candidate_text)
    for block in blocks:
        claim = claims.get(block.source_owner_id)
        if claim is None:
            raise ValueError(f"source detail has no material-claim owner: {block.source_owner_id}")
        obligation = classify_source_claim_risk(
            source_text,
            claim,
            context=source_context,
        ).obligation_id
        target = _target_for_claim(source_text, facts, claim, source_context)
        if target is None:
            raise ValueError(
                "valuable source detail has no canonical presentation destination: "
                f"{block.source_owner_id}:{obligation or 'unclassified'}"
            )
        if (
            target == _TARGETS["major_capabilities"]
            and len(
                fact_bound_capability_candidate_claims(
                    block.markdown,
                    candidate_bytes,
                    candidate_claims,
                    facts,
                    candidate_content_provenance,
                )
            )
            == 1
        ):
            continue
        routed[target].append(block)
    return dict(routed)


__all__ = ["route_source_detail_blocks", "source_section_routes_to_canonical_contract"]
