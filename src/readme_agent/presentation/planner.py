"""Deterministic repository-presentation planning from facts and Markdown."""

from __future__ import annotations

import hashlib
import re

from readme_agent.errors import ValidationFailure
from readme_agent.facts.gating import validate_claim_citations
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.claim_validation import validate_candidate_claims
from readme_agent.presentation.git_patch import (
    BoundedSourcePatchV1,
    GitPatchProofV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)
from readme_agent.presentation.markdown_structure import parse_markdown_structure
from readme_agent.presentation.schema import (
    ActionDisposition,
    FindingDisposition,
    PlannedSourceSpanV1,
    PresentationActionV1,
    PresentationDimension,
    PresentationFindingV1,
    RepositoryPresentationPlanV1,
)
from readme_agent.readme.markers import find_span
from readme_agent.readme.presentation_report import (
    detect_presentation,
    product_explanation_offset,
)
from readme_agent.registry.surface_ownership import (
    SurfaceOwnershipMapV1,
    operation_allowed,
)

_COMMERCIAL_LINK = re.compile(r"https?://products\.[^/\s)]+\.com", re.IGNORECASE)
_ACCEPTED_FACT_STATES = {"verified", "policy_approved"}


def _fact_satisfied(facts: ProductFactsV2, field_name: str) -> tuple[bool, str]:
    fact = facts.selected_fact(field_name)
    satisfied = (
        fact.verification_state in _ACCEPTED_FACT_STATES and not fact.has_unresolved_conflict
    )
    return satisfied, f"{fact.fact_id}:{fact.verification_state}"


def _installation_satisfied(facts: ProductFactsV2) -> tuple[bool, str]:
    fact = facts.selected_fact("installation.verified_acquisition")
    if fact.verification_state not in _ACCEPTED_FACT_STATES or fact.has_unresolved_conflict:
        return False, f"{fact.fact_id}:{fact.verification_state}"
    outcomes = fact.value if isinstance(fact.value, list) else []
    rejected = [
        item.get("outcome")
        for item in outcomes
        if isinstance(item, dict)
        and item.get("outcome") not in {"REGISTRY_VERIFIED", "NOT_APPLICABLE"}
    ]
    return not rejected, f"{fact.fact_id}:outcomes={rejected or ['accepted']}"


def _findings(readme_text: str, facts: ProductFactsV2) -> list[PresentationFindingV1]:
    structure = parse_markdown_structure(readme_text)
    identity = facts.selected_fact("product.identity").value
    platform = identity.get("platform") if isinstance(identity, dict) else None
    report = detect_presentation(readme_text, platform=platform)
    license_ok, license_evidence = _fact_satisfied(facts, "product.license")
    installation_ok, installation_evidence = _installation_satisfied(facts)
    explanation_offset = product_explanation_offset(readme_text)
    commercial_offsets = [match.start() for match in _COMMERCIAL_LINK.finditer(readme_text)]
    commercial_ok = len(commercial_offsets) <= 1 and (
        not commercial_offsets
        or explanation_offset is not None
        and explanation_offset < commercial_offsets[0]
    )
    dimensions: list[tuple[PresentationDimension, bool | None, str]] = [
        (
            "product_clarity",
            report.explains_product_in_opening,
            str(report.evidence["explains_product_in_opening"]),
        ),
        (
            "audience_fit",
            report.states_audience_or_ecosystem,
            str(report.evidence["states_audience_or_ecosystem"]),
        ),
        ("trust_signals", license_ok, license_evidence),
        ("installation_path", installation_ok, installation_evidence),
        (
            "verified_examples",
            report.has_runnable_example,
            str(report.evidence["has_runnable_example"]),
        ),
        (
            "navigation",
            report.heading_levels_consistent,
            str(report.evidence["heading_levels_consistent"]),
        ),
        (
            "visual_usefulness",
            None,
            f"markdown images={len(structure.image_targets)}; factual review is separate",
        ),
        (
            "contribution_readiness",
            None,
            "repository-file recognition belongs to the community-files specialist",
        ),
        (
            "maintenance_signals",
            None,
            "GitHub-generated activity remains audit-only",
        ),
        (
            "commercial_context",
            commercial_ok,
            f"commercial_links={len(commercial_offsets)}; explanation_offset={explanation_offset}",
        ),
    ]
    findings = []
    for dimension, result, evidence in dimensions:
        disposition: FindingDisposition = (
            "observation" if result is None else "satisfied" if result else "gap"
        )
        findings.append(
            PresentationFindingV1(
                finding_id=f"readme.{dimension}",
                dimension=dimension,
                surface_id="readme",
                disposition=disposition,
                summary=(
                    f"{dimension.replace('_', ' ')} is satisfied"
                    if result
                    else f"{dimension.replace('_', ' ')} needs review"
                    if result is False
                    else f"{dimension.replace('_', ' ')} is observation-only here"
                ),
                evidence=[evidence],
            )
        )
    return findings


def _resources_edit(original_text: str, candidate_text: str) -> SourceSpanEditV1:
    original_span = find_span(original_text, "resources")
    candidate_span = find_span(candidate_text, "resources")
    if candidate_span is None:
        raise ValidationFailure("README candidate changed without a resources ownership marker")
    if original_span is None:
        if not candidate_text.startswith(original_text):
            raise ValidationFailure(
                "new resources span is not a pure append to the original README"
            )
        start = len(original_text.encode("utf-8"))
        end = start
        replacement = candidate_text[len(original_text) :]
        expected = b""
    else:
        if original_text[: original_span.start] != candidate_text[: candidate_span.start]:
            raise ValidationFailure("candidate changed bytes before the owned resources span")
        if original_text[original_span.end :] != candidate_text[candidate_span.end :]:
            raise ValidationFailure("candidate changed bytes after the owned resources span")
        start = len(original_text[: original_span.start].encode("utf-8"))
        end = len(original_text[: original_span.end].encode("utf-8"))
        replacement = candidate_text[candidate_span.start : candidate_span.end]
        expected = original_text[original_span.start : original_span.end].encode("utf-8")
    return SourceSpanEditV1(
        path="README.md",
        byte_start=start,
        byte_end=end,
        expected_sha256=hashlib.sha256(expected).hexdigest(),
        replacement=replacement,
        purpose="replace or append only the readme-agent-owned resources region",
    )


def _archetype(facts: ProductFactsV2) -> str:
    identity = facts.selected_fact("product.identity").value
    if isinstance(identity, dict):
        ecosystem = identity.get("ecosystem") or identity.get("platform") or "unknown"
    else:
        ecosystem = "unknown"
    return f"{ecosystem}-library"


def build_repository_presentation_plan(
    org_repo: str,
    original_text: str,
    candidate_text: str,
    facts: ProductFactsV2,
    ownership: SurfaceOwnershipMapV1,
    *,
    base_revision: str,
) -> tuple[RepositoryPresentationPlanV1, GitPatchProofV1 | None, bool]:
    """Build a plan whose only executable action is fully bounded and cited."""

    findings = _findings(original_text, facts)
    if original_text == candidate_text:
        plan = RepositoryPresentationPlanV1(
            org_repo=org_repo,
            immutable_base_revision=base_revision,
            facts_hash=facts.canonical_hash(),
            source_sha256=sha256_text(original_text),
            archetype=_archetype(facts),
            findings=findings,
            actions=[],
            candidate_sha256=sha256_text(candidate_text),
        )
        return plan, None, True

    try:
        ownership_rule = ownership.rule_for("readme")
    except KeyError as exc:
        raise ValidationFailure("README has no surface-ownership rule") from exc
    if ownership_rule.ownership_class != "repository_file":
        raise ValidationFailure("README local patch requires ownership_class='repository_file'")
    if not operation_allowed(ownership, "readme", "local_patch"):
        raise ValidationFailure("README ownership does not permit a local_patch operation")

    edit = _resources_edit(original_text, candidate_text)
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(original_text),
        edits=[edit],
    )
    proof = create_git_patch_proof(original_text, candidate_text, bounded)
    semantic_decision = validate_candidate_claims(candidate_text, facts)
    claims = semantic_decision.claims
    citation_decision = validate_claim_citations(facts, claims)
    action_valid = citation_decision.valid and semantic_decision.valid
    action_disposition: ActionDisposition = "eligible" if action_valid else "blocked"
    action = PresentationActionV1(
        action_id="readme.resources.bounded_patch",
        surface_id="readme",
        region_id="readme.resources",
        disposition=action_disposition,
        claims=claims,
        fact_ids=sorted({fact_id for claim in claims for fact_id in claim.fact_ids}),
        ownership_class=ownership_rule.ownership_class,
        proposed_operation="local_patch",
        source_spans=[
            PlannedSourceSpanV1(
                path=edit.path,
                byte_start=edit.byte_start,
                byte_end=edit.byte_end,
                expected_sha256=edit.expected_sha256,
                replacement_sha256=sha256_text(edit.replacement),
                purpose=edit.purpose,
            )
        ],
        validators=[
            "claim_citations",
            "candidate_claim_values",
            "surface_ownership",
            "source_span_hash",
            "git_apply_check",
            "protected_content",
            "independent_verifier",
        ],
        rollback=ownership_rule.rollback,
        stop_conditions=[
            "immutable base revision changed",
            "source span hash changed",
            "fact citation is missing, stale, conflicting, or not selected",
            "candidate claim value differs from its selected fact",
            "surface ownership no longer permits local_patch",
            "git apply check or independent verification fails",
        ],
        patch_sha256=proof.patch_sha256,
    )
    plan = RepositoryPresentationPlanV1(
        org_repo=org_repo,
        immutable_base_revision=base_revision,
        facts_hash=facts.canonical_hash(),
        source_sha256=proof.source_sha256,
        archetype=_archetype(facts),
        findings=findings,
        actions=[action],
        candidate_sha256=proof.candidate_sha256,
    )
    return plan, proof, action_valid
