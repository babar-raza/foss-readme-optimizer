"""Bridge a fine-grained README document plan into the repository surface plan."""

from __future__ import annotations

import re

from readme_agent.errors import ValidationFailure
from readme_agent.facts.gating import TechnicalClaimV1, validate_claim_citations
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.git_patch import (
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)
from readme_agent.presentation.planner import build_readme_findings, classify_archetype
from readme_agent.presentation.schema import (
    PlannedSourceSpanV1,
    PresentationActionV1,
    RepositoryPresentationPlanV1,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.registry.surface_ownership import (
    SurfaceOwnershipMapV1,
    operation_allowed,
)


def _claim_id(operation_id: str, field: str) -> str:
    normalized = re.sub(r"[^a-z0-9_.:-]", "-", field.lower())
    return f"{operation_id}.{normalized}"


def _claims(facts: ProductFactsV2, operations) -> list[TechnicalClaimV1]:
    claims = []
    for operation in operations:
        for fact_id in operation.fact_ids:
            fact = facts.fact_by_id(fact_id)
            surface = next(
                (surface for surface in fact.affected_surfaces if surface.startswith("readme")),
                "readme",
            )
            claims.append(
                TechnicalClaimV1(
                    claim_id=_claim_id(operation.operation_id, fact.field),
                    surface_id=surface,
                    text=f"{operation.rationale} [{fact.field}]",
                    fact_ids=[fact_id],
                )
            )
    return claims


def build_document_repository_presentation_plan(
    org_repo: str,
    source_text: str,
    current_work_text: str,
    candidate_text: str,
    facts: ProductFactsV2,
    ownership: SurfaceOwnershipMapV1,
    *,
    base_revision: str,
) -> tuple[RepositoryPresentationPlanV1, dict, bool, dict]:
    """Rebuild the document plan independently and prove the resulting Git patch."""

    expected_candidate, document_plan = build_readme_document_candidate(
        org_repo,
        source_text,
        facts,
        base_revision=base_revision,
    )
    if expected_candidate != candidate_text:
        raise ValidationFailure("README candidate differs from the independently rebuilt plan")
    assessment = assess_readme_document(
        org_repo,
        source_text,
        facts,
        base_revision=base_revision,
    )
    claim_map = build_readme_claim_map(document_plan, facts)
    validation = validate_readme_document_candidate(
        source_text,
        candidate_text,
        document_plan,
        facts,
    )

    ownership_rule = ownership.rule_for("readme")
    if ownership_rule.ownership_class != "repository_file" or not operation_allowed(
        ownership, "readme", "local_patch"
    ):
        raise ValidationFailure("README ownership does not permit a local patch")

    edit = SourceSpanEditV1(
        path="README.md",
        byte_start=0,
        byte_end=len(current_work_text.encode("utf-8")),
        expected_sha256=sha256_text(current_work_text),
        replacement=candidate_text,
        purpose=(
            "apply the independently reconstructed presentation-span adoption and its bounded "
            "inner document operations"
        ),
    )
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(current_work_text),
        edits=[edit],
    )
    proof = create_git_patch_proof(current_work_text, candidate_text, bounded)
    claims = _claims(facts, document_plan.operations)
    citations = validate_claim_citations(facts, claims)
    executable = validation.valid and citations.valid
    action = PresentationActionV1(
        action_id="readme.presentation.document-plan",
        surface_id="readme",
        region_id="readme.presentation",
        disposition="eligible" if executable else "blocked",
        claims=claims,
        fact_ids=sorted({fact_id for claim in claims for fact_id in claim.fact_ids}),
        ownership_class=ownership_rule.ownership_class,
        proposed_operation="local_patch",
        source_spans=[
            PlannedSourceSpanV1(
                path="README.md",
                byte_start=0,
                byte_end=len(current_work_text.encode("utf-8")),
                expected_sha256=sha256_text(current_work_text),
                replacement_sha256=sha256_text(candidate_text),
                purpose=edit.purpose,
            )
        ],
        validators=[
            "claim_citations",
            "surface_ownership",
            "source_span_hash",
            "git_apply_check",
            "protected_content",
            "independent_verifier",
        ],
        rollback=ownership_rule.rollback,
        stop_conditions=[
            "immutable base revision changed",
            "source or work-tree README hash changed",
            "document reconstruction differs",
            "a fact citation becomes unselected, unresolved, or unverified",
            "protected content outside a cited authoritative correction is lost",
            "Git apply or independent verification fails",
        ],
        patch_sha256=proof.patch_sha256,
    )
    plan = RepositoryPresentationPlanV1(
        org_repo=org_repo,
        immutable_base_revision=base_revision,
        facts_hash=facts.canonical_hash(),
        source_sha256=proof.source_sha256,
        archetype=classify_archetype(facts),
        findings=build_readme_findings(candidate_text, facts),
        actions=[action],
        candidate_sha256=proof.candidate_sha256,
    )
    validation_record = validation.model_dump(mode="json")
    validation_record["citation_errors"] = citations.reasons
    return (
        plan,
        proof.model_dump(mode="json"),
        executable,
        {
            "readme_assessment": assessment.model_dump(mode="json"),
            "readme_document_plan": document_plan.model_dump(mode="json"),
            "claim_map": claim_map.model_dump(mode="json"),
            "document_validation": validation_record,
        },
    )
