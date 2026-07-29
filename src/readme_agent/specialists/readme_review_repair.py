"""Regenerate a reviewer-rejected README and repeat deterministic gates."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.capabilities.dispatcher import DispatchResult, dispatch_tool_call
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import generate_run_id
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.repository_snapshot import current_repository_snapshot
from readme_agent.specialists.independent_readme_review import (
    IndependentReadmeReviewResultV1,
)
from readme_agent.specialists.readme_factuality import evaluate_candidate_factuality
from readme_agent.specialists.readme_repair_validation import (
    repair_findings,
    validate_repair_source_binding,
)
from readme_agent.specialists.readme_review_validation import (
    dispatch_build_presentation_plan,
    dispatch_verify_readme_candidate,
    materialize_and_verify_bundle,
    presentation_plan_record,
)
from readme_agent.state.backend import StateBackend
from readme_agent.state.readme_poc_lifecycle import record_readme_candidate_artifacts
from readme_agent.supervisor.local_poc_evidence import write_local_poc_readme_candidate
from readme_agent.verification.checks import compute_verification_token

_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _persist_local_candidate(
    org_repo: str,
    backend: StateBackend,
    render_result: dict,
    presentation_plan: dict,
) -> Path:
    snapshot = current_repository_snapshot(org_repo)
    if snapshot is None:
        raise StateBackendError("immutable repository snapshot disappeared during README repair")
    bundle_dir, assessment_hash, plan_hash, candidate_hash = write_local_poc_readme_candidate(
        snapshot,
        render_result,
        presentation_plan,
    )
    record_readme_candidate_artifacts(
        backend,
        org_repo,
        source_revision=snapshot.source_revision,
        assessment_hash=assessment_hash,
        presentation_plan_hash=plan_hash,
        candidate_hash=candidate_hash,
        reviewer_standard_hash=separated_reviewer_standard_hash(),
        evidence_refs=[
            str(bundle_dir / "assessment" / "current-readme-assessment.json"),
            str(bundle_dir / "planning" / "readme-document-plan.json"),
            str(bundle_dir / "candidate" / "README.md"),
            str(bundle_dir / "candidate" / "README.patch"),
            str(bundle_dir / "candidate" / "claim-map.json"),
        ],
    )
    return bundle_dir


def _dispatch_repair_composition(
    org_repo: str,
    product_facts_v2: dict,
    review: IndependentReadmeReviewResultV1,
    source_candidate_text: str,
    *,
    client: object | None,
) -> DispatchResult:
    findings = repair_findings(review)
    source_candidate_sha256 = validate_repair_source_binding(review, source_candidate_text)
    return dispatch_tool_call(
        {
            "function": {
                "name": "plan_readme_composition",
                "arguments": json.dumps({"org_repo": org_repo}),
            }
        },
        _READ_ONLY_PERMISSIONS,
        caller_domain=README_PRESENTATION,
        extra_kwargs={
            "product_facts_v2": product_facts_v2,
            "client": client,
            "review_repair": {
                "source_candidate_sha256": source_candidate_sha256,
                "failed_criteria": review.failed_criteria,
                "sections_affected": review.sections_affected,
                "required_repair": review.required_repair,
                "preserve": review.preserve,
                "findings": [finding.model_dump(mode="json") for finding in findings],
            },
        },
    )


def _dispatch_repaired_render(
    org_repo: str,
    product_facts_v2: dict,
    composition_plan: dict,
) -> DispatchResult:
    return dispatch_tool_call(
        {
            "function": {
                "name": "render_readme_candidate",
                "arguments": json.dumps({"org_repo": org_repo, "force_regenerate": True}),
            }
        },
        _READ_ONLY_PERMISSIONS,
        caller_domain=README_PRESENTATION,
        extra_kwargs={
            "product_facts_v2": product_facts_v2,
            "agentic_composition_plan": composition_plan,
        },
    )


def build_repaired_review_context(
    org_repo: str,
    backend: StateBackend | None,
    original_render_result: dict,
    review: IndependentReadmeReviewResultV1,
    attempt: int,
    *,
    composition_client: object | None,
) -> dict:
    """Regenerate from reviewer instructions and repeat every deterministic gate."""

    product_facts_v2 = original_render_result.get("product_facts_v2")
    if product_facts_v2 is None:
        raise StateBackendError("review repair requires the run-scoped ProductFactsV2 graph")
    composition = _dispatch_repair_composition(
        org_repo,
        product_facts_v2,
        review,
        str(original_render_result["final_text"]),
        client=composition_client,
    )
    if composition.outcome != "executed" or composition.result is None:
        raise RuntimeError(f"repair composition failed: {composition.outcome}:{composition.error}")
    rendered = _dispatch_repaired_render(org_repo, product_facts_v2, composition.result)
    if rendered.outcome != "executed" or rendered.result is None:
        raise RuntimeError(f"repair render failed: {rendered.outcome}:{rendered.error}")
    render_result = dict(rendered.result)

    plan_dispatch = dispatch_build_presentation_plan(org_repo, render_result)
    if plan_dispatch.outcome != "executed" or plan_dispatch.result is None:
        raise RuntimeError(
            f"repair presentation plan failed: {plan_dispatch.outcome}:{plan_dispatch.error}"
        )
    presentation_plan = plan_dispatch.result
    plan_record = presentation_plan_record(presentation_plan)
    evidence_refs: list[str] = []
    local_bundle_dir: Path | None = None
    factuality = evaluate_candidate_factuality(
        org_repo,
        render_result["original_text"],
        render_result["final_text"],
        _READ_ONLY_PERMISSIONS,
        source_text=render_result.get("source_text", render_result["original_text"]),
        product_facts_v2=product_facts_v2,
        agentic_composition_plan=render_result.get("agentic_composition_plan"),
    )
    verification_dispatch = dispatch_verify_readme_candidate(org_repo, render_result)
    if verification_dispatch.outcome != "executed" or verification_dispatch.result is None:
        verification = {
            "verdict": "reject",
            "reason": f"{verification_dispatch.outcome}:{verification_dispatch.error}",
        }
    else:
        verification = verification_dispatch.result
    if verification.get("verdict") == "accept":
        nonce = generate_run_id()
        verification = {
            **verification,
            "nonce": nonce,
            "token": compute_verification_token(
                org_repo,
                render_result["facts_hash"],
                render_result["fresh_fingerprint"],
                nonce,
            ),
        }

    bundle_record: dict = {
        "status": "blocked",
        "verified": False,
        "failures": ["structured readme_document_plan missing"],
    }
    if presentation_plan.get("readme_document_plan"):
        bundle_record, proposal_bundle_dir = materialize_and_verify_bundle(
            org_repo,
            render_result,
            presentation_plan,
            run_id=f"{generate_run_id()}-repair-{attempt}",
        )
        evidence_refs.append(str(proposal_bundle_dir))

    deterministic_passed = (
        presentation_plan.get("executable") is True
        and factuality.valid
        and verification.get("verdict") == "accept"
        and bundle_record.get("verified") is True
    )
    deterministic_result = {
        "verdict": "accept" if deterministic_passed else "reject",
        "candidate_verification": verification,
        "factuality": factuality.model_dump(mode="json"),
        "bundle_verification": bundle_record,
    }

    def promote_repaired_context() -> dict:
        if backend is None:
            return {}
        promoted_bundle_dir = _persist_local_candidate(
            org_repo,
            backend,
            render_result,
            presentation_plan,
        )
        return {
            "local_bundle_dir": str(promoted_bundle_dir),
            "evidence_refs": [*evidence_refs, str(promoted_bundle_dir)],
        }

    return {
        "original_text": render_result["original_text"],
        "final_text": render_result["final_text"],
        "presentation_plan": plan_record,
        "deterministic_validation_result": deterministic_result,
        "candidate_verification": verification,
        "deterministic_validation_passed": deterministic_passed,
        "product_facts_v2": product_facts_v2,
        "render_result": render_result,
        "presentation_plan_record": plan_record,
        "bundle_verification": bundle_record,
        "local_bundle_dir": str(local_bundle_dir) if local_bundle_dir is not None else None,
        "evidence_refs": evidence_refs,
        "promote_repaired_context": promote_repaired_context,
    }
