"""Build a fact-backed structured presentation plan before verification."""

from readme_agent import paths
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.errors import ValidationFailure
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.inspection.file_inventory import scan
from readme_agent.presentation.document_planner import (
    build_document_repository_presentation_plan,
)
from readme_agent.presentation.planner import build_repository_presentation_plan
from readme_agent.readme.markers import find_presentation_span
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.registry.surface_ownership import SurfaceOwnershipMapV1

CAPABILITY_ID = "build_presentation_plan"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Build repository presentation plan",
    purpose="Read-only: re-derives ProductFactsV2 and surface ownership, assesses all ten "
    "presentation dimensions, and emits a source-span-bounded, Git-checked plan. Candidate "
    "text is wiring-only and never accepted from an LLM tool call.",
    category="readme_presentation",
    owner="readme_agent.presentation.planner",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "presentation_plan": "object",
        "git_patch_proof": "object",
        "readme_assessment": "object",
        "readme_document_plan": "object",
        "claim_map": "object",
        "document_validation": "object",
        "executable": "boolean",
    },
    preconditions=["org_repo must be listed in data/products.json"],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    allowed_domains=[README_PRESENTATION],
    input_model=OrgRepoOnlyInputV1,
    tools_used=[
        "facts.provider.collect_product_facts",
        "markdown_it.MarkdownIt",
        "git diff",
        "git apply --check",
    ],
    validators=["change_boundary"],
    failure_modes=[
        "ValidationFailure for stale, overlapping, unowned, uncited, or non-reconstructable edits"
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_presentation_planner.py", "tests/unit/test_git_patch.py"],
    requirement_ids=["RDM-003", "RDM-004", "FACT-003", "OWN-011", "L8-007"],
)


def execute(
    org_repo: str,
    *,
    original_text: str | None = None,
    candidate_text: str | None = None,
    source_revision: str | None = None,
    source_text: str | None = None,
    product_facts_v2: dict | None = None,
) -> dict:
    if product_facts_v2 is None:
        facts_result = collect_product_facts(org_repo)
        facts = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
        ownership = SurfaceOwnershipMapV1.model_validate(facts_result["surface_ownership"])
    else:
        facts = ProductFactsV2.model_validate(product_facts_v2)
        entry = require_listed(org_repo)
        if entry.policy_profile is None:
            raise ValueError(f"{org_repo!r} has no policy_profile")
        ownership = load_policy(entry.policy_profile).surface_ownership
    identity = facts.selected_fact("product.identity")
    observed_revision = identity.source.source_revision
    if observed_revision is None:
        raise ValueError("presentation planning requires an immutable repository revision")
    if source_revision is not None and source_revision != observed_revision:
        raise ValidationFailure(
            "render snapshot revision does not match the independently observed facts revision"
        )
    base_revision = source_revision or observed_revision

    if original_text is None:
        entry = require_listed(org_repo)
        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        clone_baseline(entry, baseline)
        inventory = scan(baseline)
        original_text = (
            inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""
        )
    if candidate_text is None:
        candidate_text = original_text

    if find_presentation_span(candidate_text) is not None:
        plan, document_patch_record, executable, document_records = (
            build_document_repository_presentation_plan(
                org_repo,
                source_text if source_text is not None else original_text,
                original_text,
                candidate_text,
                facts,
                ownership,
                base_revision=base_revision,
            )
        )
        return {
            "presentation_plan": plan.model_dump(mode="json"),
            "git_patch_proof": document_patch_record,
            "executable": executable,
            **document_records,
        }

    plan, legacy_patch_proof, executable = build_repository_presentation_plan(
        org_repo,
        original_text,
        candidate_text,
        facts,
        ownership,
        base_revision=base_revision,
    )
    return {
        "presentation_plan": plan.model_dump(mode="json"),
        "git_patch_proof": (
            legacy_patch_proof.model_dump(mode="json") if legacy_patch_proof is not None else {}
        ),
        "readme_assessment": {},
        "readme_document_plan": {},
        "claim_map": {},
        "document_validation": {},
        "executable": executable,
    }
