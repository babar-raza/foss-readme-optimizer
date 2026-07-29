"""Expose immutable README-derived trusted facts as a registered capability."""

from __future__ import annotations

from readme_agent.capabilities.contracts import materialize_contract_models
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.facts.trusted_readme_extraction import extract_trusted_readme_fact_graph
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactsOutputV1
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import current_repository_snapshot

CAPABILITY_ID = "extract_trusted_readme_facts"

MANIFEST = materialize_contract_models(
    CapabilityManifest(
        capability_id=CAPABILITY_ID,
        version="1",
        name="Extract trusted README facts",
        purpose=(
            "Read-only: inventory material content from the bound immutable README with exact "
            "UTF-8 source spans and README_INHERITED provenance. This intentionally performs no "
            "repository-source, package, documentation, or external fact verification."
        ),
        category="product_facts",
        owner="readme_agent.facts.trusted_readme_extraction",
        execution_type="deterministic_tool",
        required_inputs={"org_repo": "string"},
        produced_outputs={
            "org_repo": "string",
            "content_assurance": "string",
            "fact_graph": "object",
            "fact_graph_hash": "string",
        },
        preconditions=[
            "org_repo is listed in data/products.json",
            "one immutable RepositorySnapshotV1 is bound to the current run",
            "the snapshot contains a UTF-8 README",
        ],
        required_permissions=["read_only_local"],
        side_effect_class="read_only_local",
        allowed_domains=[README_PRESENTATION],
        tools_used=[
            "registry.loader.require_listed",
            "repository_snapshot.current_repository_snapshot",
            "facts.trusted_readme_extraction.extract_trusted_readme_fact_graph",
        ],
        failure_modes=[
            "NotAllowlistedError when the target is not registered",
            "RepositorySnapshotError when no immutable README is bound",
            "RepositorySnapshotError when README bytes drift or are not UTF-8",
        ],
        rollback_behavior="not applicable -- read-only",
        tests=["tests/unit/test_trusted_readme_extraction.py"],
        requirement_ids=["TRP-002", "TRP-003"],
        input_model=OrgRepoOnlyInputV1,
        output_model=TrustedReadmeFactsOutputV1,
    )
)


def execute(org_repo: str) -> dict:
    """Extract only from the run-scoped snapshot after the hard allow-list gate."""

    require_listed(org_repo)
    snapshot = current_repository_snapshot(org_repo)
    if snapshot is None:
        raise RuntimeError("extract_trusted_readme_facts requires a bound RepositorySnapshotV1")
    graph = extract_trusted_readme_fact_graph(snapshot)
    return TrustedReadmeFactsOutputV1(
        org_repo=org_repo,
        fact_graph=graph,
        fact_graph_hash=graph.canonical_hash(),
    ).model_dump(mode="json")
