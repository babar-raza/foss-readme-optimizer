"""Compose one trusted README candidate through bounded LLM section calls."""

from __future__ import annotations

from readme_agent.capabilities.contracts import materialize_contract_models
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.facts.trusted_readme_extraction import extract_trusted_readme_fact_graph
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition import compose_trusted_readme
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedReadmeCompositionOutputV1,
)
from readme_agent.readme.trusted_presentation_standards import (
    bind_trusted_presentation_standards,
)
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import current_repository_snapshot

CAPABILITY_ID = "compose_trusted_readme"

MANIFEST = materialize_contract_models(
    CapabilityManifest(
        capability_id=CAPABILITY_ID,
        version="1",
        name="Compose trusted README",
        purpose=(
            "Use bounded forced-tool LLM calls to inventory, plan, and author a README-trusted "
            "candidate while deterministic assembly preserves source and presentation contracts."
        ),
        category="readme_presentation",
        owner="readme_agent.readme.trusted_composition",
        execution_type="agentic_planning",
        required_inputs={"org_repo": "string"},
        produced_outputs={
            "org_repo": "string",
            "content_assurance": "string",
            "plan": "object",
            "plan_hash": "string",
            "candidate_markdown": "string",
            "candidate_patch": "string",
            "candidate_sha256": "string",
            "llm_call_count": "integer",
        },
        preconditions=[
            "org_repo is listed in data/products.json",
            "one immutable RepositorySnapshotV1 is bound to the current run",
            "trusted README facts have been extracted for that snapshot",
        ],
        required_permissions=["read_only_network"],
        side_effect_class="read_only_network",
        allowed_domains=[README_PRESENTATION],
        model_route="trusted_readme_section_transform",
        tools_used=[
            "llm.verifier_client.LiveForcedToolClient",
            "readme.trusted_composition.compose_trusted_readme",
        ],
        failure_modes=[
            "LLMError on incomplete source coverage, truncation, unknown provenance, "
            "or contract failure",
            "RepositorySnapshotError when immutable README bytes drift",
        ],
        rollback_behavior="reopen only the rejected section batch; no effect is performed",
        tests=["tests/unit/test_trusted_readme_composition.py"],
        requirement_ids=["TRP-003", "TRP-004", "TRP-005"],
        input_model=OrgRepoOnlyInputV1,
        output_model=TrustedReadmeCompositionOutputV1,
        evidence_outputs=[
            "plan",
            "plan_hash",
            "candidate_patch",
            "candidate_sha256",
            "llm_call_count",
        ],
    )
)


def execute(
    org_repo: str,
    *,
    fact_graph: dict | None = None,
    client=None,
    envelope: TrustedCompositionEnvelopeV1 | None = None,
) -> dict:
    """Compose from the bound snapshot; wiring-only arguments stay outside tool schema."""

    require_listed(org_repo)
    snapshot = current_repository_snapshot(org_repo)
    if snapshot is None or snapshot.readme_path is None:
        raise RuntimeError("compose_trusted_readme requires a bound README snapshot")
    graph = (
        TrustedReadmeFactGraphV1.model_validate(fact_graph)
        if fact_graph is not None
        else extract_trusted_readme_fact_graph(snapshot)
    )
    source_text = (snapshot.root_path / snapshot.readme_path).read_text(encoding="utf-8")
    graph = bind_trusted_presentation_standards(org_repo, graph, source_text)
    output = compose_trusted_readme(
        graph,
        source_text,
        client=client,
        envelope=envelope,
    )
    return output.model_dump(mode="json")
