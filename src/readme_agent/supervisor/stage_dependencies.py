"""Selected dependency manifests for narrow repository-stage invalidation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.supervisor.presentation_component_versions import (
    AffectedStageV1,
    PresentationSemanticScopeV1,
    SelectedDependencyV1,
    canonical_sha256,
)

StageNameV1 = Literal["SNAPSHOT", "FACTS", "CANDIDATE", "DETERMINISTIC", "APPROVAL", "NOOP"]

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_CANDIDATE_DEPENDENCY_GROUPS: dict[
    str, tuple[PresentationSemanticScopeV1, AffectedStageV1, tuple[str, ...]]
] = {
    "candidate_orchestration": (
        "safety",
        "PLAN_READY",
        (
            "src/readme_agent/capabilities/build_presentation_plan.py",
            "src/readme_agent/capabilities/render_readme_candidate.py",
            "src/readme_agent/readme/idea_candidate.py",
            "src/readme_agent/readme/verified_preservation_composition.py",
            "src/readme_agent/specialists/readme_presentation.py",
            "src/readme_agent/supervisor/portfolio_scheduler/stages.py",
        ),
    ),
    "composition_semantics": (
        "severe_acceptance",
        "PLAN_READY",
        (
            "src/readme_agent/readme/agentic_composition.py",
            "src/readme_agent/readme/agentic_composition_grounding.py",
            "src/readme_agent/readme/agentic_composition_inputs.py",
            "src/readme_agent/readme/agentic_composition_models.py",
            "src/readme_agent/readme/agentic_composition_validation.py",
            "src/readme_agent/readme/capability_semantics.py",
            "src/readme_agent/readme/diagram_semantic_candidates.py",
            "src/readme_agent/readme/diagram_role_semantics.py",
            "src/readme_agent/readme/opening_summary_fallback.py",
        ),
    ),
    "contextual_link_policy": (
        "prose_policy",
        "PLAN_READY",
        (
            "src/readme_agent/links/allocation.py",
            "src/readme_agent/links/contextual_selection.py",
            "src/readme_agent/presentation/verified_template_document.py",
            "src/readme_agent/presentation/verified_template_documentation.py",
            "src/readme_agent/presentation/verified_template_link_budget.py",
            "data/aspose_com_links.json",
            "data/aspose_org_links.json",
        ),
    ),
    "document_compilation": (
        "structural",
        "PLAN_READY",
        (
            "src/readme_agent/presentation/verified_template_draft.py",
            "src/readme_agent/presentation/template_adapters.py",
            "src/readme_agent/presentation/verified_template_api_descriptions.py",
            "src/readme_agent/presentation/verified_template_api_members.py",
            "src/readme_agent/presentation/verified_template_api_reference.py",
            "src/readme_agent/presentation/verified_template_api_text.py",
            "src/readme_agent/presentation/verified_template_capabilities.py",
            "src/readme_agent/presentation/verified_template_capability_seo.py",
            "src/readme_agent/presentation/verified_template_example_presentation.py",
            "src/readme_agent/presentation/verified_template_golden_workflow.py",
            "src/readme_agent/presentation/verified_template_runtime.py",
            "src/readme_agent/presentation/verified_template_sections.py",
            "src/readme_agent/readme/acquisition_contracts.py",
            "src/readme_agent/readme/public_limitations.py",
            "src/readme_agent/readme/document_acquisition.py",
            "src/readme_agent/readme/document_renderer.py",
            "src/readme_agent/readme/document_templates.py",
            "src/readme_agent/readme/public_text.py",
            "templates/readme/additional-examples-details.md",
            "templates/readme/agentic-overview-and-navigation.md",
            "templates/readme/contextual-enterprise-relationship.md",
            "templates/readme/contextual-example-link.md",
            "templates/readme/contextual-foss-product.md",
            "templates/readme/contextual-product-relationship.md",
            "templates/readme/product-overview-and-navigation.md",
            "templates/readme/verified-cpp-nuget-acquisition.md",
            "templates/readme/verified-dotnet-nuget-acquisition.md",
            "templates/readme/verified-go-acquisition.md",
            "templates/readme/verified-limitations.md",
            "templates/readme/verified-maven-acquisition.md",
            "templates/readme/verified-minimal-example.md",
            "templates/readme/verified-python-pypi-acquisition.md",
            "templates/readme/verified-repository-constraints.md",
            "templates/readme/verified-source-acquisition.md",
        ),
    ),
    "header_visual": (
        "cosmetic",
        "PLAN_READY",
        (
            "src/readme_agent/readme/header_badges.py",
            "src/readme_agent/readme/header_visual.py",
            "src/readme_agent/readme/header_visual_mermaid.py",
            "src/readme_agent/readme/header_visual_layout.py",
            "src/readme_agent/readme/header_visual_models.py",
            "src/readme_agent/readme/header_visual_validation.py",
            "src/readme_agent/verification/mermaid_render.py",
            "src/readme_agent/specialists/readme_visual_render_gate.py",
        ),
    ),
    "presentation_template": (
        "fact_slot",
        "PLAN_READY",
        ("templates/readme/repository-presentation-v1.json",),
    ),
    "presentation_validation": (
        "severe_acceptance",
        "CANDIDATE_GENERATED",
        (
            "src/readme_agent/links/contextual_validation.py",
            "src/readme_agent/readme/claim_accountability_validation.py",
            "src/readme_agent/readme/document_validation.py",
            "src/readme_agent/readme/header_visual_validation.py",
            "src/readme_agent/readme/limitation_semantics.py",
            "src/readme_agent/readme/limitation_validation.py",
            "src/readme_agent/readme/presentation_lint.py",
            "src/readme_agent/readme/presentation_lint_api_reference.py",
            "src/readme_agent/readme/presentation_lint_public_contract.py",
            "src/readme_agent/readme/presentation_lint_semantics.py",
            "src/readme_agent/readme/presentation_lint_structure.py",
            "src/readme_agent/validation/presentation_template.py",
        ),
    ),
    "source_bound_plan_and_patch": (
        "protected_content",
        "README_ASSESSED",
        (
            "src/readme_agent/presentation/document_planner.py",
            "src/readme_agent/presentation/git_patch.py",
            "src/readme_agent/presentation/planner.py",
        ),
    ),
    "source_claim_accountability": (
        "protected_content",
        "README_ASSESSED",
        (
            "src/readme_agent/presentation/verified_source_assurance_projection.py",
            "src/readme_agent/presentation/verified_source_claim_matching.py",
            "src/readme_agent/presentation/verified_source_claim_obligations.py",
            "src/readme_agent/presentation/verified_source_claim_omissions.py",
            "src/readme_agent/presentation/verified_source_claim_resolution_engine.py",
            "src/readme_agent/presentation/verified_source_detail_routing.py",
            "src/readme_agent/presentation/verified_source_detail_presentation.py",
            "src/readme_agent/presentation/verified_source_limitation_matching.py",
            "src/readme_agent/presentation/verified_source_placements.py",
            "src/readme_agent/presentation/verified_source_policy.py",
            "src/readme_agent/presentation/verified_source_policy_application.py",
            "src/readme_agent/presentation/verified_source_preservation.py",
            "src/readme_agent/presentation/verified_template_provenance.py",
            "src/readme_agent/readme/example_assurance_validation.py",
            "src/readme_agent/readme/limitation_semantics.py",
            "src/readme_agent/readme/claim_accountability.py",
            "src/readme_agent/readme/claim_accountability_candidate_policy.py",
            "src/readme_agent/readme/claim_accountability_coordinates.py",
            "src/readme_agent/readme/claim_accountability_golden_workflow_coordinates.py",
            "src/readme_agent/readme/claim_replacement_validation.py",
            "src/readme_agent/readme/source_claim_assurance.py",
            "src/readme_agent/readme/source_claim_conversion_binding.py",
            "src/readme_agent/readme/source_claim_fact_binding.py",
            "src/readme_agent/readme/source_claim_mcp_binding.py",
            "src/readme_agent/readme/source_claim_obligations.py",
            "src/readme_agent/readme/source_claim_repository_asset_binding.py",
            "src/readme_agent/readme/source_claim_risk.py",
            "src/readme_agent/readme/source_claim_structured_matching.py",
        ),
    ),
    "stage_bundle_persistence": (
        "safety",
        "CANDIDATE_GENERATED",
        (
            "src/readme_agent/evidence/redaction.py",
            "src/readme_agent/evidence/writer.py",
            "src/readme_agent/supervisor/local_poc_evidence.py",
            "src/readme_agent/supervisor/local_poc_snapshot_evidence.py",
            "src/readme_agent/supervisor/portfolio_scheduler/contracts.py",
            "src/readme_agent/supervisor/portfolio_scheduler/lane.py",
            "src/readme_agent/supervisor/portfolio_scheduler/reducer.py",
        ),
    ),
}

_PROMPT_SCOPE_COMPONENT_POLICY: dict[str, tuple[PresentationSemanticScopeV1, AffectedStageV1]] = {
    "FACTS_COLLECTING": ("factuality", "FACTS_COLLECTING"),
    "README_ASSESSED": ("severe_acceptance", "README_ASSESSED"),
    "PLAN_READY": ("prose_policy", "PLAN_READY"),
    "CANDIDATE_GENERATED": ("factuality", "CANDIDATE_GENERATED"),
    "DETERMINISTIC_VALIDATED": ("severe_acceptance", "DETERMINISTIC_VALIDATED"),
    "AGENT_REVIEWING": ("severe_acceptance", "AGENT_REVIEWING"),
    "REPAIRING": ("severe_acceptance", "REPAIRING"),
    "SPECIALIST_SELECTION": ("safety", "FACTS_COLLECTING"),
    "SUPERVISOR_PLANNING": ("safety", "FACTS_COLLECTING"),
    "TRUSTED_PLAN_READY": ("safety", "FACTS_COLLECTING"),
    "TRUSTED_REVIEWING": ("safety", "FACTS_COLLECTING"),
}


def _runtime_component_dependencies(repository: str) -> list[SelectedDependencyV1]:
    """Version prompt, capability, validation, and policy owners independently."""

    from readme_agent.capabilities import registry as capability_registry
    from readme_agent.errors import ConfigError, NotAllowlistedError
    from readme_agent.llm import prompt_registry
    from readme_agent.registry.loader import load_policy, require_listed
    from readme_agent.validation.registry import VALIDATION_RULESET_VERSION

    dependencies: list[SelectedDependencyV1] = []
    for prompt_id, manifest in sorted(prompt_registry.all_manifests().items()):
        semantic_scope, earliest_stage = _PROMPT_SCOPE_COMPONENT_POLICY[manifest.invalidation_scope]
        relative_path = f"prompts/{manifest.category}/{prompt_id}.yaml"
        dependencies.append(
            SelectedDependencyV1(
                dependency_id=f"prompt:{prompt_id}",
                files={relative_path: prompt_registry.prompt_hash(prompt_id)},
                semantic_scope=semantic_scope,
                earliest_affected_stage=earliest_stage,
            )
        )

    capability_versions = {
        item.capability_id: item.version for item in capability_registry.list_all()
    }
    dependencies.append(
        SelectedDependencyV1(
            dependency_id="capability_registry",
            files={"virtual/capability-versions.json": canonical_sha256(capability_versions)},
            semantic_scope="safety",
            earliest_affected_stage="FACTS_COLLECTING",
        )
    )
    dependencies.append(
        SelectedDependencyV1(
            dependency_id="validation_ruleset",
            files={
                "virtual/validation-ruleset-version": canonical_sha256(VALIDATION_RULESET_VERSION)
            },
            semantic_scope="severe_acceptance",
            earliest_affected_stage="DETERMINISTIC_VALIDATED",
        )
    )
    try:
        entry = require_listed(repository)
        policy_profile = entry.policy_profile
        if policy_profile:
            policy = load_policy(policy_profile)
            dependencies.append(
                SelectedDependencyV1(
                    dependency_id="repository_policy",
                    files={
                        f"config/policies/{policy_profile}.yml": canonical_sha256(
                            policy.model_dump(mode="json")
                        )
                    },
                    semantic_scope="factuality",
                    earliest_affected_stage="FACTS_COLLECTING",
                )
            )
    except (ConfigError, NotAllowlistedError):
        # Synthetic unit fixtures are intentionally not registry members. Real supervised
        # repositories have already passed the allow-list gate before this function runs.
        pass
    return dependencies


class StageDependencyManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["StageDependencyManifestV1"] = "StageDependencyManifestV1"
    repository: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    stage: StageNameV1
    ecosystem: str
    upstream_receipt_ids: list[str] = Field(default_factory=list)
    dependencies: list[SelectedDependencyV1] = Field(min_length=1)
    stage_key: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _stage_key_matches_manifest(self) -> StageDependencyManifestV1:
        expected = _stage_manifest_key(
            repository=self.repository,
            source_revision=self.source_revision,
            stage=self.stage,
            ecosystem=self.ecosystem,
            upstream_receipt_ids=self.upstream_receipt_ids,
            dependencies=self.dependencies,
        )
        if self.stage_key != expected:
            raise ValueError("stage_key does not match the selected dependency manifest")
        return self


def _stage_manifest_key(
    *,
    repository: str,
    source_revision: str,
    stage: StageNameV1,
    ecosystem: str,
    upstream_receipt_ids: list[str],
    dependencies: list[SelectedDependencyV1],
) -> str:
    identity: dict[str, object] = {
        "repository": repository,
        "source_revision": source_revision,
        "stage": stage,
        "ecosystem": ecosystem,
        "upstream_receipt_ids": upstream_receipt_ids,
        "dependencies": [item.model_dump(mode="json") for item in dependencies],
    }
    return canonical_sha256(identity)


def build_stage_dependency_manifest(
    *,
    repository: str,
    source_revision: str,
    stage: StageNameV1,
    ecosystem: str,
    dependencies: list[SelectedDependencyV1],
    upstream_receipt_ids: list[str] | None = None,
) -> StageDependencyManifestV1:
    """Hash only dependencies selected for this stage and ecosystem."""

    ordered = sorted(dependencies, key=lambda item: item.dependency_id)
    upstream = sorted(upstream_receipt_ids or [])
    return StageDependencyManifestV1(
        repository=repository,
        source_revision=source_revision,
        stage=stage,
        ecosystem=ecosystem,
        upstream_receipt_ids=upstream,
        dependencies=ordered,
        stage_key=_stage_manifest_key(
            repository=repository,
            source_revision=source_revision,
            stage=stage,
            ecosystem=ecosystem,
            upstream_receipt_ids=upstream,
            dependencies=ordered,
        ),
    )


def invalidated_stage(
    prior: StageDependencyManifestV1,
    current: StageDependencyManifestV1,
) -> bool:
    """Return whether the exact selected stage contract changed."""

    return prior.stage_key != current.stage_key


def current_candidate_stage_dependency_manifest(
    *,
    repository: str,
    source_revision: str,
    ecosystem: str | None,
) -> StageDependencyManifestV1:
    """Bind candidate reuse to the exact selected composition and rendering bytes."""

    dependencies: list[SelectedDependencyV1] = []
    for dependency_id, (semantic_scope, earliest_stage, relative_paths) in sorted(
        _CANDIDATE_DEPENDENCY_GROUPS.items()
    ):
        files: dict[str, str] = {}
        for relative_path in relative_paths:
            path = _REPOSITORY_ROOT / relative_path
            if not path.is_file():
                raise FileNotFoundError(f"candidate stage dependency is missing: {relative_path}")
            files[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
        dependencies.append(
            SelectedDependencyV1(
                dependency_id=dependency_id,
                files=files,
                semantic_scope=semantic_scope,
                earliest_affected_stage=earliest_stage,
            )
        )
    dependencies.extend(_runtime_component_dependencies(repository))
    return build_stage_dependency_manifest(
        repository=repository,
        source_revision=source_revision,
        stage="CANDIDATE",
        ecosystem=ecosystem or "unknown",
        dependencies=dependencies,
    )
