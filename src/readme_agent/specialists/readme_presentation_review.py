"""Gate README candidates through deterministic review and autonomous repair."""

from __future__ import annotations

import hashlib
from pathlib import Path

from langchain_core.runnables import RunnableConfig

from readme_agent import paths
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import generate_run_id
from readme_agent.llm import prompt_registry
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import current_repository_snapshot
from readme_agent.specialists.independent_readme_review import (
    run_independent_review_with_repair_loop,
)
from readme_agent.specialists.readme_review_repair import build_repaired_review_context
from readme_agent.specialists.readme_review_validation import (
    materialize_and_verify_bundle,
)
from readme_agent.state.backend import StateBackend
from readme_agent.state.domain_state import merge_details
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.readme_poc_lifecycle import transition_readme_poc_status
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.local_poc_review_evidence import (
    write_local_poc_no_op_evidence,
    write_local_poc_review_evidence,
)


def review_candidate_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    """Require bundle validation, independent review, and bounded autonomous repair."""

    if (state.accepted_status or "").startswith("ERROR:"):
        return {}
    render_result = state.details.get("render_result")
    assert render_result is not None
    if not render_result["needs_write"]:
        return {}

    org_repo = config["configurable"]["org_repo"]
    backend: StateBackend | None = config["configurable"].get("backend")
    durable_state = backend.load(org_repo) if backend is not None else None
    lifecycle_backend = (
        backend
        if durable_state is not None and durable_state.readme_poc_lifecycle is not None
        else None
    )
    presentation_plan_record = state.details["presentation_plan"]
    verification = state.details["verification"]
    state_without_patch = state.model_copy(
        update={
            "details": {
                key: value
                for key, value in state.details.items()
                if key != "presentation_plan_patch"
            }
        }
    )

    lifecycle = durable_state.readme_poc_lifecycle if durable_state is not None else None
    local_bundle_dir: Path | None = None
    snapshot = current_repository_snapshot(org_repo)
    if lifecycle_backend is not None and snapshot is not None:
        entry = require_listed(org_repo)
        local_bundle_dir = paths.readme_poc_repository_dir(
            entry.org,
            entry.repo_name,
            snapshot.source_revision,
        )

    # A byte-identical approved candidate must not create another run-scoped
    # proposal bundle. Earlier lifecycle invalidation checks bind source,
    # facts, prompts, reviewer standard, and protected content; this final
    # candidate hash check binds the exact rendered bytes before reuse.
    #
    # NO_OP_PROVEN and its later human/PR states are already beyond this
    # review boundary. A resumed portfolio pass can still enter this node
    # because the source README continues to differ from the candidate. It
    # must reuse the proven result, not invoke the reviewer again and attempt
    # the illegal NO_OP_PROVEN -> AGENT_APPROVED regression.
    if (
        lifecycle_backend is not None
        and lifecycle is not None
        and lifecycle.status
        in {
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ):
        if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
            raise StateBackendError("approved local README lifecycle must use the V2 contract")
        candidate_hash = hashlib.sha256(
            str(render_result["final_text"]).encode("utf-8")
        ).hexdigest()
        if candidate_hash != lifecycle.candidate_hash:
            raise StateBackendError(
                "approved README lifecycle candidate hash does not match the unchanged render"
            )
        if local_bundle_dir is None or not (local_bundle_dir / "manifest.json").is_file():
            raise StateBackendError(
                "approved README lifecycle has no revision-addressed evidence bundle"
            )
        if lifecycle.status == "AGENT_APPROVED":
            transition_readme_poc_status(
                lifecycle_backend,
                org_repo,
                "NO_OP_PROVEN",
                observed_by=INDEPENDENT_VERIFICATION,
                reason=(
                    "unchanged approved candidate reused without another bundle or agentic review"
                ),
                evidence_refs=[str(local_bundle_dir)],
            )
            write_local_poc_no_op_evidence(
                local_bundle_dir,
                candidate_hash=candidate_hash,
                agentic_review_reused=True,
            )
        return {
            "details": merge_details(
                state_without_patch,
                independent_review={
                    "outcome_kind": "unchanged_no_op",
                    "agentic_review_reused": True,
                    "lifecycle_status_reused": lifecycle.status,
                },
            )
        }

    document_plan_available = bool(presentation_plan_record.get("readme_document_plan"))
    bundle_verification_record: dict
    proposal_bundle_dir: Path | None = None
    if document_plan_available:
        if render_result.get("product_facts_v2") is None:
            return {"accepted_status": "ERROR:verified_product_facts_missing_from_candidate"}
        bundle_verification_record, proposal_bundle_dir = materialize_and_verify_bundle(
            org_repo,
            render_result,
            {
                **presentation_plan_record,
                "git_patch_proof": {
                    **presentation_plan_record["git_patch_proof"],
                    "patch": state.details.get("presentation_plan_patch") or "",
                },
            },
            run_id=str(verification.get("nonce") or generate_run_id()),
        )
        if not bundle_verification_record.get("verified"):
            if lifecycle_backend is not None:
                transition_readme_poc_status(
                    lifecycle_backend,
                    org_repo,
                    "DETERMINISTIC_VALIDATION_FAILED",
                    observed_by=INDEPENDENT_VERIFICATION,
                    reason="deterministic README proposal bundle verification rejected candidate",
                    evidence_refs=[str(proposal_bundle_dir)],
                )
            return {
                "accepted_status": (
                    "ERROR:bundle_verification_rejected:"
                    + "; ".join(bundle_verification_record.get("failures", []))
                ),
                "details": merge_details(
                    state_without_patch,
                    bundle_verification=bundle_verification_record,
                ),
            }
    else:
        if lifecycle_backend is not None:
            return {
                "accepted_status": "ERROR:bundle_verification_requires_readme_document_plan",
                "details": merge_details(
                    state_without_patch,
                    bundle_verification={
                        "status": "blocked",
                        "reason": "deterministic bundle verification requires a structured "
                        "readme_document_plan",
                    },
                ),
            }
        bundle_verification_record = {
            "status": "not_applicable",
            "reason": "compatibility candidate has no governed README-POC lifecycle",
        }

    if lifecycle_backend is not None:
        reviewer_standard_hash = prompt_registry.prompt_hash("independent_readme_review")
        current = lifecycle_backend.load(org_repo)
        lifecycle = current.readme_poc_lifecycle if current is not None else None
        if lifecycle is None:
            raise StateBackendError("durable README-POC lifecycle disappeared before review")
        if lifecycle.status == "CANDIDATE_GENERATED":
            lifecycle = transition_readme_poc_status(
                lifecycle_backend,
                org_repo,
                "DETERMINISTIC_VALIDATED",
                observed_by=INDEPENDENT_VERIFICATION,
                reason="deterministic README proposal bundle verification passed",
                evidence_refs=[str(proposal_bundle_dir)],
            )
        if lifecycle.status == "DETERMINISTIC_VALIDATED":
            transition_readme_poc_status(
                lifecycle_backend,
                org_repo,
                "AGENT_REVIEWING",
                observed_by=INDEPENDENT_VERIFICATION,
                reason="independent README review started after deterministic validation",
                evidence_refs=[str(proposal_bundle_dir)],
                reviewer_standard_hash=reviewer_standard_hash,
            )

    initial_context = {
        "original_text": render_result["original_text"],
        "final_text": render_result["final_text"],
        "presentation_plan": presentation_plan_record,
        "deterministic_validation_result": verification,
        "candidate_verification": verification,
        "deterministic_validation_passed": True,
        "product_facts_v2": render_result.get("product_facts_v2"),
        "render_result": render_result,
        "presentation_plan_record": presentation_plan_record,
        "bundle_verification": bundle_verification_record,
        "local_bundle_dir": str(local_bundle_dir) if local_bundle_dir is not None else None,
        "evidence_refs": [str(proposal_bundle_dir)] if proposal_bundle_dir is not None else [],
    }
    try:
        review_outcome = run_independent_review_with_repair_loop(
            org_repo,
            lifecycle_backend,
            initial_context,
            client=config["configurable"].get("independent_review_client"),
            regenerate_context=lambda review, attempt: build_repaired_review_context(
                org_repo,
                lifecycle_backend,
                render_result,
                review,
                attempt,
                composition_client=config["configurable"].get("composition_client"),
            ),
        )
    except Exception as exc:  # noqa: BLE001 -- fail closed and preserve the first boundary
        if lifecycle_backend is not None:
            loaded = lifecycle_backend.load(org_repo)
            lifecycle = loaded.readme_poc_lifecycle if loaded is not None else None
            if lifecycle is not None and lifecycle.status != "SYSTEM_FAILURE":
                transition_readme_poc_status(
                    lifecycle_backend,
                    org_repo,
                    "SYSTEM_FAILURE",
                    observed_by=INDEPENDENT_VERIFICATION,
                    reason=f"independent review wiring failed: {type(exc).__name__}: {exc}",
                )
        return {
            "accepted_status": f"ERROR:independent_review_exception:{type(exc).__name__}: {exc}",
            "details": merge_details(
                state_without_patch,
                bundle_verification=bundle_verification_record,
            ),
        }

    final_context = review_outcome.final_context
    final_render_result = final_context.get("render_result", render_result)
    final_plan_record = final_context.get(
        "presentation_plan_record",
        presentation_plan_record,
    )
    final_bundle_record = final_context.get(
        "bundle_verification",
        bundle_verification_record,
    )
    final_validation = final_context.get(
        "deterministic_validation_result",
        verification,
    )
    final_candidate_verification = final_context.get(
        "candidate_verification",
        verification,
    )
    final_state = state_without_patch.model_copy(
        update={
            "details": {
                **state_without_patch.details,
                "render_result": final_render_result,
                "presentation_plan": final_plan_record,
                "verification": final_candidate_verification,
            }
        }
    )
    independent_review_record = review_outcome.model_dump(mode="json")
    final_local_bundle = final_context.get("local_bundle_dir")
    if final_local_bundle:
        final_deterministic_passed = bool(
            final_context.get("deterministic_validation_passed", True)
        )
        final_lifecycle_status = (
            {
                "ACCEPT": "AGENT_APPROVED",
                "REJECT_REPAIRABLE": "AGENT_REVIEW_REJECTED",
                "BLOCKED_FACT_CONFLICT": "BLOCKED_FACT_CONFLICT",
                "BLOCKED_MISSING_EVIDENCE": "BLOCKED_MISSING_EVIDENCE",
                "SYSTEM_FAILURE": "SYSTEM_FAILURE",
            }[review_outcome.final_review.verdict]
            if final_deterministic_passed
            else "DETERMINISTIC_VALIDATION_FAILED"
        )
        write_local_poc_review_evidence(
            Path(final_local_bundle),
            deterministic_validation=final_validation,
            independent_review=review_outcome.final_review.model_dump(mode="json"),
            repair_history=review_outcome.repair_history,
            lifecycle_status=final_lifecycle_status,
            deterministic_validation_passed=final_deterministic_passed,
            reviewer_standard_hash=prompt_registry.prompt_hash("independent_readme_review"),
        )
    if review_outcome.outcome_kind != "accepted":
        return {
            "accepted_status": (
                f"ERROR:independent_review_{review_outcome.outcome_kind}:"
                f"{review_outcome.final_review.verdict}"
            ),
            "details": merge_details(
                final_state,
                bundle_verification=final_bundle_record,
                independent_review=independent_review_record,
            ),
        }
    return {
        "details": merge_details(
            final_state,
            bundle_verification=final_bundle_record,
            independent_review=independent_review_record,
        )
    }
