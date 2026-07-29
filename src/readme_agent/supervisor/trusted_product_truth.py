"""Prepare and durably bind README-derived facts for the trusted lane."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.facts.trusted_readme_schema import (
    TrustedReadmeFactGraphV1,
    TrustedReadmeFactsOutputV1,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import (
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.readme_poc_lifecycle import (
    migrate_readme_poc_lifecycle,
    switch_content_assurance,
    transition_trusted_readme_poc_status,
)
from readme_agent.supervisor.local_poc_evidence import write_local_poc_trusted_readme_facts

_TRUSTED_FACTS_READY_OR_LATER = frozenset(
    {
        "TRUSTED_FACTS_EXTRACTED",
        "TRUSTED_PLAN_READY",
        "TRUSTED_CANDIDATE_GENERATED",
        "TRUSTED_DETERMINISTIC_VALIDATED",
        "TRUSTED_REVIEWING",
        "TRUSTED_REVIEW_REJECTED",
        "TRUSTED_REPAIRING",
        "TRUSTED_TRANSFORM_APPROVED",
        "TRUSTED_NO_OP_PROVEN",
        "TRUSTED_PR_ELIGIBLE",
        "TRUSTED_PR_OPEN",
    }
)


class PreparedTrustedReadmeFactsV1(BaseModel):
    """Run-scoped trusted fact graph and its assurance-specific evidence root."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_graph: TrustedReadmeFactGraphV1
    resolution_source: str = "immutable_readme"
    lifecycle_status: str = "TRUSTED_FACTS_EXTRACTED"
    bundle_dir: str
    cache_reused: bool = False


def _trusted_bundle_dir(snapshot: RepositorySnapshotV1) -> Path:
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    return (
        paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
        / "assurance"
        / "trusted_inherited"
    )


def load_prepared_trusted_readme_facts(
    org_repo: str,
    snapshot: RepositorySnapshotV1,
    state_backend: StateBackend,
) -> PreparedTrustedReadmeFactsV1 | None:
    """Reuse only a checksum-matching trusted graph at the same immutable revision."""

    state = state_backend.load(org_repo)
    stored = state.readme_poc_lifecycle if state is not None else None
    lifecycle = (
        migrate_readme_poc_lifecycle(stored)
        if isinstance(stored, ReadmePocLifecycleStateV1)
        else stored
    )
    if (
        not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or lifecycle.content_assurance != "trusted_inherited"
        or lifecycle.source_revision != snapshot.source_revision
        or lifecycle.status not in _TRUSTED_FACTS_READY_OR_LATER
        or lifecycle.facts_hash is None
    ):
        return None
    bundle_dir = _trusted_bundle_dir(snapshot)
    fact_path = bundle_dir / "facts" / "readme-inherited-facts.json"
    manifest_path = bundle_dir / "manifest.json"
    if not fact_path.is_file() or not manifest_path.is_file() or not verify_sha256sums(bundle_dir):
        return None
    fact_graph = TrustedReadmeFactGraphV1.model_validate_json(fact_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    graph_hash = fact_graph.canonical_hash()
    if (
        fact_graph.org_repo != org_repo
        or fact_graph.source_revision != snapshot.source_revision
        or fact_graph.readme_sha256 != snapshot.readme_sha256
        or graph_hash != lifecycle.facts_hash
        or graph_hash != manifest.get("facts_hash")
        or manifest.get("content_assurance") != "trusted_inherited"
    ):
        return None
    return PreparedTrustedReadmeFactsV1(
        fact_graph=fact_graph,
        lifecycle_status=lifecycle.status,
        bundle_dir=str(bundle_dir),
        cache_reused=True,
    )


def prepare_trusted_readme_facts(
    org_repo: str,
    snapshot: RepositorySnapshotV1,
    state_backend: StateBackend,
) -> PreparedTrustedReadmeFactsV1:
    """Dispatch, persist, and advance trusted extraction without external fact providers."""

    cached = load_prepared_trusted_readme_facts(org_repo, snapshot, state_backend)
    if cached is not None:
        return cached
    state = state_backend.load(org_repo)
    stored = state.readme_poc_lifecycle if state is not None else None
    lifecycle = (
        migrate_readme_poc_lifecycle(stored)
        if isinstance(stored, ReadmePocLifecycleStateV1)
        else stored
    )
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise RuntimeError("trusted fact extraction requires a durable V2 README lifecycle")
    if lifecycle.content_assurance != "trusted_inherited":
        lifecycle = switch_content_assurance(
            state_backend,
            org_repo,
            "trusted_inherited",
            observed_by="trusted_product_truth",
            reason="begin README-derived trusted transformation",
        )
    if lifecycle.status not in {
        "PROFILED",
        "SYSTEM_FAILURE",
        *_TRUSTED_FACTS_READY_OR_LATER,
        "TRUSTED_FACTS_EXTRACTING",
    }:
        raise RuntimeError(
            f"trusted fact extraction cannot resume from lifecycle {lifecycle.status!r}"
        )
    if lifecycle.status != "TRUSTED_FACTS_EXTRACTING":
        transition_trusted_readme_poc_status(
            state_backend,
            org_repo,
            "TRUSTED_FACTS_EXTRACTING",
            observed_by="trusted_product_truth",
            reason="inventory immutable README material as inherited facts",
            source_revision=snapshot.source_revision,
        )
    try:
        dispatch = dispatch_tool_call(
            {
                "id": f"trusted-facts:{org_repo}:{snapshot.source_revision}",
                "function": {
                    "name": "extract_trusted_readme_facts",
                    "arguments": json.dumps({"org_repo": org_repo}),
                },
            },
            {"read_only_local"},
            caller_domain=README_PRESENTATION,
            state_backend=state_backend,
        )
        if dispatch.outcome != "executed" or dispatch.result is None:
            raise RuntimeError(
                f"extract_trusted_readme_facts dispatch failed: "
                f"{dispatch.outcome}: {dispatch.error or dispatch.gap}"
            )
        output = TrustedReadmeFactsOutputV1.model_validate(dispatch.result)
        trusted_dir = write_local_poc_trusted_readme_facts(snapshot, output.fact_graph)
    except Exception as exc:
        transition_trusted_readme_poc_status(
            state_backend,
            org_repo,
            "SYSTEM_FAILURE",
            observed_by="trusted_product_truth",
            reason=f"trusted fact extraction failed: {type(exc).__name__}",
            source_revision=snapshot.source_revision,
        )
        raise
    transition_trusted_readme_poc_status(
        state_backend,
        org_repo,
        "TRUSTED_FACTS_EXTRACTED",
        observed_by="trusted_product_truth",
        reason="README-derived trusted fact graph persisted with exact source accountability",
        evidence_refs=[
            str(trusted_dir / "facts" / "readme-inherited-facts.json"),
            str(trusted_dir / "facts" / "source-to-fact-map.json"),
            str(trusted_dir / "facts" / "configured-standards.json"),
        ],
        source_revision=snapshot.source_revision,
        facts_hash=output.fact_graph_hash,
    )
    return PreparedTrustedReadmeFactsV1(
        fact_graph=output.fact_graph,
        bundle_dir=str(trusted_dir),
    )
