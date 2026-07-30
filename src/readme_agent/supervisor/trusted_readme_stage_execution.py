"""Dispatch trusted README stages and persist their durable boundaries."""

from __future__ import annotations

import json
from typing import Any

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.reviewer_client import (
    TRUSTED_REVIEW_MAX_TOKENS,
    build_live_trusted_review_clients,
)
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.review_role_execution import AnalysisClientLike
from readme_agent.specialists.trusted_transform_review_models import TrustedReviewExecutionV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.readme_poc_lifecycle import transition_trusted_readme_poc_status
from readme_agent.supervisor.trusted_product_truth import prepare_trusted_readme_facts


def dispatch_trusted_composition(
    org_repo: str,
    graph: TrustedReadmeFactGraphV1,
    backend: StateBackend,
    *,
    author_client: ForcedToolClient | None,
) -> TrustedReadmeCompositionOutputV1:
    """Compose through the registered presentation capability."""

    dispatch = dispatch_tool_call(
        {
            "id": f"trusted-compose:{org_repo}:{graph.source_revision}",
            "function": {
                "name": "compose_trusted_readme",
                "arguments": json.dumps({"org_repo": org_repo}),
            },
        },
        {"read_only_network"},
        caller_domain=README_PRESENTATION,
        extra_kwargs={
            "fact_graph": graph.model_dump(mode="json"),
            "client": author_client,
        },
        state_backend=backend,
    )
    if dispatch.outcome != "executed" or dispatch.result is None:
        raise RuntimeError(
            f"compose_trusted_readme dispatch failed: {dispatch.outcome}: "
            f"{dispatch.error or dispatch.gap}"
        )
    return TrustedReadmeCompositionOutputV1.model_validate(dispatch.result)


def dispatch_trusted_review(
    org_repo: str,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    backend: StateBackend,
    *,
    blind_client: AnalysisClientLike | None,
    fidelity_client: AnalysisClientLike | None,
    cached_review: TrustedReviewExecutionV1 | None = None,
    enable_fidelity_batch_cache: bool = False,
) -> TrustedReviewExecutionV1:
    """Review through the registered independent-verification capability."""

    dispatch = dispatch_tool_call(
        {
            "id": f"trusted-review:{org_repo}:{composition.candidate_sha256}",
            "function": {
                "name": "review_trusted_readme",
                "arguments": json.dumps({"org_repo": org_repo}),
            },
        },
        {"read_only_network"},
        caller_domain=INDEPENDENT_VERIFICATION,
        extra_kwargs={
            "fact_graph": graph.model_dump(mode="json"),
            "composition_output": composition.model_dump(mode="json"),
            "blind_client": blind_client,
            "fidelity_client": fidelity_client,
            "cached_review": (
                cached_review.review.model_dump(mode="json") if cached_review is not None else None
            ),
            "enable_fidelity_batch_cache": enable_fidelity_batch_cache,
        },
        state_backend=backend,
    )
    if dispatch.outcome != "executed" or dispatch.result is None:
        raise RuntimeError(
            f"review_trusted_readme dispatch failed: {dispatch.outcome}: "
            f"{dispatch.error or dispatch.gap}"
        )
    return TrustedReviewExecutionV1.model_validate(dispatch.result)


def record_trusted_composition(
    backend: StateBackend,
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    evidence_dir: str,
) -> None:
    """Advance plan and candidate states once their evidence is durable."""

    lifecycle = load_trusted_lifecycle(backend, graph.org_repo)
    if lifecycle.status == "TRUSTED_FACTS_EXTRACTED":
        lifecycle = transition_trusted_readme_poc_status(
            backend,
            graph.org_repo,
            "TRUSTED_PLAN_READY",
            observed_by="trusted_readme_pipeline",
            reason="complete source-accountable trusted transform plan persisted",
            evidence_refs=[f"{evidence_dir}/planning/transform-plan.json"],
            source_revision=graph.source_revision,
            facts_hash=graph.canonical_hash(),
        )
    if lifecycle.status == "TRUSTED_PLAN_READY":
        transition_trusted_readme_poc_status(
            backend,
            graph.org_repo,
            "TRUSTED_CANDIDATE_GENERATED",
            observed_by="trusted_readme_pipeline",
            reason="trusted README candidate and native patch persisted",
            evidence_refs=[
                f"{evidence_dir}/candidate/README.md",
                f"{evidence_dir}/candidate/README.patch",
            ],
            source_revision=graph.source_revision,
            facts_hash=graph.canonical_hash(),
            candidate_hash=composition.candidate_sha256,
        )


def reopen_invalid_trusted_candidate(
    org_repo: str,
    snapshot: RepositorySnapshotV1,
    backend: StateBackend,
    lifecycle: ReadmePocLifecycleStateV2,
    graph: TrustedReadmeFactGraphV1,
) -> TrustedReadmeFactGraphV1:
    """Invalidate only trusted candidate dependencies after cache corruption."""

    if lifecycle.status == "TRUSTED_FACTS_EXTRACTED":
        return graph
    transition_trusted_readme_poc_status(
        backend,
        org_repo,
        "TRUSTED_FACTS_EXTRACTING",
        observed_by="trusted_readme_pipeline",
        reason="trusted candidate or review cache failed checksum or binding validation",
        source_revision=snapshot.source_revision,
    )
    return prepare_trusted_readme_facts(org_repo, snapshot, backend).fact_graph


def load_trusted_lifecycle(
    backend: StateBackend,
    org_repo: str,
) -> ReadmePocLifecycleStateV2:
    """Load the assurance-bound durable lifecycle or fail closed."""

    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise RuntimeError("trusted README pipeline requires durable V2 lifecycle state")
    return lifecycle


def trusted_source_text(snapshot: RepositorySnapshotV1) -> str:
    """Read the exact immutable README bytes bound to the snapshot."""

    if snapshot.readme_path is None:
        raise RuntimeError("trusted README pipeline requires an immutable source README")
    return (snapshot.root_path / snapshot.readme_path).read_text(encoding="utf-8")


def live_trusted_author_client() -> LiveForcedToolClient:
    """Build the governed live client used for authoring and repair."""

    job = "trusted_readme_section_transform"
    return LiveForcedToolClient(
        env.llm_base_url(),
        env.llm_api_key(),
        env.llm_model_for_job(job),
        timeout=env.llm_timeout_seconds(),
        max_tokens=8_000,
        job=job,
        prompt_id=job,
    )


def live_trusted_review_clients() -> tuple[AnalysisClientLike, AnalysisClientLike]:
    """Build the two separately identified governed reviewer clients."""

    return build_live_trusted_review_clients(
        env.llm_base_url(),
        env.llm_api_key(),
        timeout=env.llm_timeout_seconds(),
        max_tokens=TRUSTED_REVIEW_MAX_TOKENS,
    )


def require_trusted_review_client(
    client: Any | None,
    role: str,
) -> AnalysisClientLike:
    """Keep repair bound to the same independently identified review role."""

    if client is None:
        raise RuntimeError(
            f"trusted repair requires the same explicit {role} reviewer client used initially"
        )
    return client
