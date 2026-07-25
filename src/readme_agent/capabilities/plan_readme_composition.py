"""Produce a fact- and source-bound agentic README composition plan."""

from __future__ import annotations

from readme_agent import paths
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.readme.agentic_composition import plan_readme_composition
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import (
    capture_repository_snapshot,
    current_repository_snapshot,
)

CAPABILITY_ID = "plan_readme_composition"


def execute(
    org_repo: str,
    *,
    product_facts_v2: dict | None = None,
    client=None,
) -> dict:
    entry = require_listed(org_repo)
    snapshot = current_repository_snapshot(org_repo)
    if snapshot is None:
        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        clone_baseline(entry, baseline)
        snapshot = capture_repository_snapshot(entry, baseline)
    readme_path = snapshot.root_path / (snapshot.readme_path or "README.md")
    source_text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    facts = (
        ProductFactsV2.model_validate(product_facts_v2)
        if product_facts_v2 is not None
        else ProductFactsV2.model_validate(collect_product_facts(org_repo)["product_facts_v2"])
    )
    assessment = assess_readme_document(
        org_repo,
        source_text,
        facts,
        base_revision=snapshot.source_revision,
    )
    plan = plan_readme_composition(
        org_repo,
        source_text,
        facts,
        assessment,
        client=client,
    )
    return plan.model_dump(mode="json")


MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Plan README composition",
    purpose=(
        "Agentically interpret one repository's verified facts and current README into a "
        "source-bound editorial strategy whose fact and section references are validated "
        "before deterministic rendering."
    ),
    category="readme_presentation",
    owner="readme_agent.capabilities.plan_readme_composition",
    execution_type="agentic_planning",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "section_decisions": "array",
        "overview_sentences": "array",
        "prompt_sha256": "string",
        "input_sha256": "string",
        "model": "string",
    },
    preconditions=["org_repo is allow-listed and has an immutable repository snapshot"],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[README_PRESENTATION],
    input_model=OrgRepoOnlyInputV1,
    model_route="plan_readme_composition",
    tools_used=["llm.analysis_client.LiveAnalysisClient"],
    failure_modes=["LLMError on invalid schema, unknown references, or ungrounded prose"],
    rollback_behavior="not applicable -- read-only proposal",
    tests=["tests/unit/test_agentic_readme_composition.py"],
    evidence_outputs=["section_decisions", "overview_sentences", "prompt_sha256", "input_sha256"],
)
