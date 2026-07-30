"""Run the bounded trusted README lane through registered capabilities."""

from __future__ import annotations

from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review_repair import (
    run_trusted_review_with_repair,
)
from readme_agent.state.backend import StateBackend
from readme_agent.state.readme_poc_lifecycle import transition_trusted_readme_poc_status
from readme_agent.supervisor.trusted_product_truth import prepare_trusted_readme_facts
from readme_agent.supervisor.trusted_readme_evidence import (
    load_trusted_readme_evidence,
    write_trusted_composition_evidence,
    write_trusted_review_evidence,
)
from readme_agent.supervisor.trusted_readme_noop import prove_trusted_no_op
from readme_agent.supervisor.trusted_readme_pipeline_models import (
    TrustedReadmePipelineResultV1,
)
from readme_agent.supervisor.trusted_readme_stage_execution import (
    dispatch_trusted_composition,
    dispatch_trusted_review,
    live_trusted_author_client,
    live_trusted_review_clients,
    load_trusted_lifecycle,
    record_trusted_composition,
    reopen_invalid_trusted_candidate,
    require_trusted_review_client,
    trusted_source_text,
)
from readme_agent.supervisor.trusted_review_state import record_trusted_review_execution

_APPROVED_OR_LATER = frozenset(
    {
        "TRUSTED_TRANSFORM_APPROVED",
        "TRUSTED_NO_OP_PROVEN",
        "TRUSTED_PR_ELIGIBLE",
        "TRUSTED_PR_OPEN",
    }
)


def run_trusted_readme_pipeline(
    org_repo: str,
    snapshot: RepositorySnapshotV1,
    backend: StateBackend,
    *,
    target_stage: str,
    author_client: ForcedToolClient | None = None,
    blind_client: AnalysisClientLike | None = None,
    fidelity_client: AnalysisClientLike | None = None,
    repair_client: ForcedToolClient | None = None,
) -> TrustedReadmePipelineResultV1:
    """Compose, independently review, repair, and prove an exact cached rerun."""

    prepared = prepare_trusted_readme_facts(org_repo, snapshot, backend)
    graph = prepared.fact_graph
    cached = load_trusted_readme_evidence(snapshot, graph)
    lifecycle = load_trusted_lifecycle(backend, org_repo)
    if cached is None:
        graph = reopen_invalid_trusted_candidate(
            org_repo,
            snapshot,
            backend,
            lifecycle,
            graph,
        )
        composition = dispatch_trusted_composition(
            org_repo,
            graph,
            backend,
            author_client=author_client,
        )
        bundle_dir = write_trusted_composition_evidence(snapshot, graph, composition)
        record_trusted_composition(backend, graph, composition, str(bundle_dir))
        cached_review = None
    else:
        composition = cached.composition
        bundle_dir = cached.bundle_dir
        cached_review = cached.review_execution

    if (blind_client is None) != (fidelity_client is None):
        raise ValueError("trusted pipeline reviewer clients must be supplied together")
    enable_fidelity_batch_cache = blind_client is None
    if blind_client is None or fidelity_client is None:
        blind_client, fidelity_client = live_trusted_review_clients()

    lifecycle = load_trusted_lifecycle(backend, org_repo)
    if (
        lifecycle.status in _APPROVED_OR_LATER
        and cached_review is not None
        and cached_review.review.verdict == "TRUSTED_TRANSFORM_APPROVED"
    ):
        if lifecycle.status != "TRUSTED_TRANSFORM_APPROVED":
            return TrustedReadmePipelineResultV1(
                status=lifecycle.status,
                reached=True,
                candidate_sha256=composition.candidate_sha256,
                evidence_dir=str(bundle_dir),
                cache_reused=True,
            )
        return prove_trusted_no_op(
            org_repo,
            snapshot,
            graph,
            composition,
            backend,
            cached_review,
            blind_client=blind_client,
            fidelity_client=fidelity_client,
        )

    execution = dispatch_trusted_review(
        org_repo,
        graph,
        composition,
        backend,
        blind_client=blind_client,
        fidelity_client=fidelity_client,
        enable_fidelity_batch_cache=enable_fidelity_batch_cache,
    )
    write_trusted_review_evidence(snapshot, graph, composition, execution)
    lifecycle = record_trusted_review_execution(
        backend,
        graph,
        composition,
        execution,
        evidence_refs=[str(bundle_dir / "review" / "independent-review.json")],
    )
    if lifecycle.status == "TRUSTED_TRANSFORM_APPROVED":
        if target_stage == "TRUSTED_NO_OP_PROVEN":
            return prove_trusted_no_op(
                org_repo,
                snapshot,
                graph,
                composition,
                backend,
                execution,
                blind_client=blind_client,
                fidelity_client=fidelity_client,
            )
        return TrustedReadmePipelineResultV1(
            status=lifecycle.status,
            reached=True,
            candidate_sha256=composition.candidate_sha256,
            evidence_dir=str(bundle_dir),
        )
    if lifecycle.status == "SYSTEM_FAILURE":
        return TrustedReadmePipelineResultV1(
            status=lifecycle.status,
            reached=False,
            candidate_sha256=composition.candidate_sha256,
            evidence_dir=str(bundle_dir),
            blocked_reason="trusted independent review system failure",
        )

    transition_trusted_readme_poc_status(
        backend,
        org_repo,
        "TRUSTED_REPAIRING",
        observed_by="trusted_readme_pipeline",
        reason="repair the section responsible for grounded independent-review findings",
        evidence_refs=[str(bundle_dir / "review" / "independent-review.json")],
        source_revision=snapshot.source_revision,
    )
    resolved_repair_client = repair_client or live_trusted_author_client()
    loop_result = run_trusted_review_with_repair(
        graph,
        trusted_source_text(snapshot),
        composition,
        blind_client=require_trusted_review_client(blind_client, "blind"),
        fidelity_client=require_trusted_review_client(fidelity_client, "fidelity"),
        repair_client=resolved_repair_client,
        initial_execution=execution,
        enable_fidelity_batch_cache=enable_fidelity_batch_cache,
    )
    final_composition = loop_result.final_composition
    if final_composition.candidate_sha256 != composition.candidate_sha256:
        bundle_dir = write_trusted_composition_evidence(snapshot, graph, final_composition)
        transition_trusted_readme_poc_status(
            backend,
            org_repo,
            "TRUSTED_CANDIDATE_GENERATED",
            observed_by="trusted_readme_pipeline",
            reason="section-scoped repair produced changed candidate bytes",
            evidence_refs=[str(bundle_dir / "candidate" / "README.md")],
            source_revision=snapshot.source_revision,
            facts_hash=graph.canonical_hash(),
            candidate_hash=final_composition.candidate_sha256,
        )
        write_trusted_review_evidence(
            snapshot,
            graph,
            final_composition,
            loop_result.final_execution,
            repair_history=loop_result.repair_history,
        )
        lifecycle = record_trusted_review_execution(
            backend,
            graph,
            final_composition,
            loop_result.final_execution,
            evidence_refs=[
                str(bundle_dir / "review" / "independent-review.json"),
                str(bundle_dir / "review" / "repair-history.json"),
            ],
        )
    elif loop_result.outcome == "system_failure":
        lifecycle = transition_trusted_readme_poc_status(
            backend,
            org_repo,
            "SYSTEM_FAILURE",
            observed_by="trusted_readme_pipeline",
            reason=loop_result.system_failure_reason or "trusted repair failed",
            evidence_refs=[str(bundle_dir / "review" / "repair-history.json")],
            source_revision=snapshot.source_revision,
        )
    if lifecycle.status == "TRUSTED_TRANSFORM_APPROVED" and target_stage == "TRUSTED_NO_OP_PROVEN":
        return prove_trusted_no_op(
            org_repo,
            snapshot,
            graph,
            final_composition,
            backend,
            loop_result.final_execution,
            blind_client=blind_client,
            fidelity_client=fidelity_client,
        )
    return TrustedReadmePipelineResultV1(
        status=lifecycle.status,
        reached=(
            lifecycle.status == "TRUSTED_TRANSFORM_APPROVED"
            and target_stage == "TRUSTED_TRANSFORM_APPROVED"
        ),
        candidate_sha256=final_composition.candidate_sha256,
        evidence_dir=str(bundle_dir),
        blocked_reason=(
            None
            if lifecycle.status == "TRUSTED_TRANSFORM_APPROVED"
            else loop_result.system_failure_reason or "trusted review repair did not reach approval"
        ),
    )
