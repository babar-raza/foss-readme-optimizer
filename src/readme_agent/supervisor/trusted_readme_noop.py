"""Prove unchanged trusted README reruns without new provider calls."""

from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review_models import TrustedReviewExecutionV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.readme_poc_lifecycle import transition_trusted_readme_poc_status
from readme_agent.supervisor.trusted_readme_evidence import write_trusted_review_evidence
from readme_agent.supervisor.trusted_readme_pipeline_models import (
    TrustedReadmePipelineResultV1,
)
from readme_agent.supervisor.trusted_readme_stage_execution import dispatch_trusted_review


def prove_trusted_no_op(
    org_repo: str,
    snapshot: RepositorySnapshotV1,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    backend: StateBackend,
    approved_execution: TrustedReviewExecutionV1,
    *,
    blind_client: AnalysisClientLike,
    fidelity_client: AnalysisClientLike,
) -> TrustedReadmePipelineResultV1:
    """Revalidate the exact accepted cache and persist its zero-call proof."""

    execution = dispatch_trusted_review(
        org_repo,
        graph,
        composition,
        backend,
        blind_client=blind_client,
        fidelity_client=fidelity_client,
        cached_review=approved_execution,
    )
    bundle_dir = write_trusted_review_evidence(
        snapshot,
        graph,
        composition,
        execution,
        no_op_proven=True,
    )
    if not execution.cache_reused or execution.new_provider_call_count != 0:
        lifecycle = transition_trusted_readme_poc_status(
            backend,
            org_repo,
            "SYSTEM_FAILURE",
            observed_by="trusted_readme_pipeline",
            reason="trusted unchanged rerun did not reuse the exact approved review",
            source_revision=snapshot.source_revision,
        )
        return TrustedReadmePipelineResultV1(
            status=lifecycle.status,
            reached=False,
            blocked_reason="trusted unchanged rerun did not reuse the exact approved review",
        )
    lifecycle = transition_trusted_readme_poc_status(
        backend,
        org_repo,
        "TRUSTED_NO_OP_PROVEN",
        observed_by="trusted_readme_pipeline",
        reason="exact trusted candidate and independent approval reused with zero provider calls",
        evidence_refs=[str(bundle_dir / "review" / "no-op-proof.json")],
        source_revision=snapshot.source_revision,
        facts_hash=graph.canonical_hash(),
        candidate_hash=composition.candidate_sha256,
        prompt_hash=execution.review.cache_identity_sha256,
    )
    return TrustedReadmePipelineResultV1(
        status=lifecycle.status,
        reached=True,
        candidate_sha256=composition.candidate_sha256,
        evidence_dir=str(bundle_dir),
        cache_reused=True,
    )
