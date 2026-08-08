"""Promote an unchanged approved local README bundle without rerunning its author."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.evidence.writer import generate_run_id
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    record_non_provider_call,
)
from readme_agent.state.backend import StateBackend
from readme_agent.state.domain_state import save_domain
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2, ReadmePocStatusV2
from readme_agent.state.readme_poc_lifecycle import transition_readme_poc_status
from readme_agent.state.schema import RunStateV2, SupervisorStateV1
from readme_agent.supervisor.evidence import (
    assert_evidence_complete,
    write_supervise_evidence,
)
from readme_agent.supervisor.local_poc_cache import (
    LocalPocCacheDecisionV1,
    evaluate_approved_local_poc_cache,
    evaluate_completed_local_poc_cache,
)
from readme_agent.supervisor.local_poc_manifest_recovery import (
    reconcile_approved_manifest_from_receipt,
    reconcile_completed_manifest_from_evidence,
)
from readme_agent.supervisor.local_poc_review_evidence import (
    write_local_poc_no_op_evidence,
)
from readme_agent.supervisor.models import DecisionSummary, SuperviseResult
from readme_agent.supervisor.state_tracking import record_supervisor_state
from readme_agent.supervisor.task import TaskGraph


class LocalPocNoOpReuseV1(BaseModel):
    """Inspectible outcome of the first approved-candidate reuse boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    promoted: bool
    decision: LocalPocCacheDecisionV1


class LocalPocCompletedReuseV1(BaseModel):
    """Inspectible decision for a fully completed bundle fallback."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reused: bool
    decision: LocalPocCacheDecisionV1


def reopen_invalidated_local_poc(
    *,
    backend: StateBackend,
    state: RunStateV2,
    bundle_dir: Path,
    decision: LocalPocCacheDecisionV1,
) -> bool:
    """Apply a denied cache decision to the durable lifecycle before execution.

    Cache evaluation is not itself an invalidation. Without this transition a
    completed lifecycle can keep dispatching only its old review boundary while
    recompiling stale plan bytes. A new source revision is deliberately left to
    ``record_repository_snapshot()``, which owns that immutable transition.
    """

    affected = decision.earliest_affected_stage
    if decision.reusable or affected is None or affected == "SNAPSHOTTED":
        return False
    target: ReadmePocStatusV2 = (
        "FACTS_COLLECTING" if affected == "FACTS_COLLECTING" else "README_ASSESSED"
    )
    transition_readme_poc_status(
        backend,
        state.org_repo,
        target,
        observed_by="local-poc-cache",
        reason=(
            f"completed bundle cache invalidated at {affected}: "
            + ", ".join(decision.mismatch_reasons)
        ),
        evidence_refs=[str(bundle_dir)],
        source_revision=(
            state.readme_poc_lifecycle.source_revision
            if isinstance(state.readme_poc_lifecycle, ReadmePocLifecycleStateV2)
            else None
        ),
    )
    return True


def promote_approved_local_poc_noop(
    *,
    backend: StateBackend,
    state: RunStateV2,
    bundle_dir: Path,
    current_source_revision: str,
    current_control_plane_fingerprint: str,
    ecosystem: str | None = None,
) -> LocalPocNoOpReuseV1:
    """Reuse a fully bound approved candidate and persist exact zero-call proof."""

    reconcile_approved_manifest_from_receipt(state, bundle_dir)
    decision = evaluate_approved_local_poc_cache(
        state,
        bundle_dir,
        current_source_revision=current_source_revision,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        ecosystem=ecosystem,
    )
    if not decision.reusable:
        return LocalPocNoOpReuseV1(promoted=False, decision=decision)
    lifecycle = state.readme_poc_lifecycle
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert lifecycle.candidate_hash is not None
    bind_llm_repository_revision(current_source_revision, stage="NO_OP_PROOF")
    record_non_provider_call(
        job="local_poc_approved_bundle",
        prompt_id="local_poc_approved_bundle",
        prompt_sha256=None,
        model="cache",
        disposition="cache_reuse",
        request={
            "org_repo": state.org_repo,
            "source_revision": current_source_revision,
            "status": "AGENT_APPROVED",
            "cache_key": decision.cache_key,
        },
    )
    transition_readme_poc_status(
        backend,
        state.org_repo,
        "NO_OP_PROVEN",
        observed_by=INDEPENDENT_VERIFICATION,
        reason="unchanged approved bundle reused before author or reviewer dispatch",
        evidence_refs=[str(bundle_dir)],
    )
    write_local_poc_no_op_evidence(
        bundle_dir,
        candidate_hash=lifecycle.candidate_hash,
        agentic_review_reused=True,
    )
    current = backend.load(state.org_repo)
    prior_readme = current.domain_states.get(README_PRESENTATION) if current is not None else None
    if prior_readme is not None:
        save_domain(
            backend,
            state.org_repo,
            README_PRESENTATION,
            prior_readme.model_copy(
                update={
                    "details": {
                        **prior_readme.details,
                        "agentic_composition_reused": True,
                        "no_op_bundle_reused": True,
                    }
                }
            ),
            current_revision=current_source_revision,
        )
    return LocalPocNoOpReuseV1(promoted=True, decision=decision)


def reuse_completed_local_poc_noop(
    *,
    state: RunStateV2,
    bundle_dir: Path,
    current_source_revision: str,
    current_control_plane_fingerprint: str,
    ecosystem: str | None = None,
) -> LocalPocCompletedReuseV1:
    """Reuse a completed bundle when generic repository freshness is unavailable."""

    reconcile_completed_manifest_from_evidence(state, bundle_dir)
    decision = evaluate_completed_local_poc_cache(
        state,
        bundle_dir,
        current_source_revision=current_source_revision,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        ecosystem=ecosystem,
    )
    if not decision.reusable:
        return LocalPocCompletedReuseV1(reused=False, decision=decision)
    bind_llm_repository_revision(current_source_revision, stage="NO_OP_PROOF")
    record_non_provider_call(
        job="local_poc_complete_bundle",
        prompt_id="local_poc_complete_bundle",
        prompt_sha256=None,
        model="cache",
        disposition="cache_reuse",
        request={
            "org_repo": state.org_repo,
            "source_revision": current_source_revision,
            "status": decision.status,
            "cache_key": decision.cache_key,
        },
    )
    return LocalPocCompletedReuseV1(reused=True, decision=decision)


def finish_local_poc_preclone_reuse(
    *,
    backend: StateBackend,
    org_repo: str,
    current_source_revision: str,
    current_control_plane_fingerprint: str,
    prior_surface_freshness: dict,
    decision_kind: str,
    decision_detail: str,
    write_evidence_bundle: bool,
    fail_closed_on_state_failure: bool,
) -> SuperviseResult:
    """Persist one zero-clone README reuse result through normal supervisor evidence."""

    status = "CONVERGED_NO_TRACKED_CHANGE"
    graph = TaskGraph()
    decisions = [
        DecisionSummary(
            turn=0,
            kind=decision_kind,
            detail=decision_detail,
        )
    ]
    record_supervisor_state(
        backend,
        org_repo,
        SupervisorStateV1(
            last_observed_upstream_revision=current_source_revision,
            last_status=status,
            last_run_timestamp=datetime.now(UTC).isoformat(),
            control_plane_fingerprint=current_control_plane_fingerprint,
            surface_freshness=prior_surface_freshness,
        ),
        strict=fail_closed_on_state_failure,
    )
    evidence_dir = None
    if write_evidence_bundle:
        current = backend.load(org_repo)
        lifecycle = current.readme_poc_lifecycle if current is not None else None
        if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
            raise RuntimeError("local-POC reuse evidence requires a V2 README lifecycle")
        run_id = generate_run_id()
        evidence_dir = paths.evidence_dir(run_id)
        write_supervise_evidence(
            evidence_dir,
            run_id,
            org_repo,
            status,
            graph,
            decisions,
            control_plane_fingerprint=current_control_plane_fingerprint,
            upstream_revision=current_source_revision,
            surface_freshness=prior_surface_freshness,
            readme_poc_lifecycle=lifecycle,
        )
        assert_evidence_complete(evidence_dir)
    return SuperviseResult(
        status=status,
        org_repo=org_repo,
        task_graph=graph,
        decisions=decisions,
        evidence_dir=evidence_dir,
    )
