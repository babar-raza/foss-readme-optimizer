"""Selected dependency manifests for narrow repository-stage invalidation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StageNameV1 = Literal["SNAPSHOT", "FACTS", "CANDIDATE", "DETERMINISTIC", "APPROVAL", "NOOP"]

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_CANDIDATE_DEPENDENCY_GROUPS: dict[str, tuple[str, ...]] = {
    "candidate_orchestration": (
        "src/readme_agent/capabilities/build_presentation_plan.py",
        "src/readme_agent/capabilities/render_readme_candidate.py",
        "src/readme_agent/readme/idea_candidate.py",
        "src/readme_agent/readme/verified_preservation_composition.py",
        "src/readme_agent/specialists/readme_presentation.py",
        "src/readme_agent/supervisor/portfolio_scheduler/stages.py",
    ),
    "composition_semantics": (
        "prompts/generation/plan_readme_composition.yaml",
        "src/readme_agent/readme/agentic_composition.py",
        "src/readme_agent/readme/agentic_composition_grounding.py",
        "src/readme_agent/readme/agentic_composition_inputs.py",
        "src/readme_agent/readme/agentic_composition_models.py",
        "src/readme_agent/readme/agentic_composition_validation.py",
        "src/readme_agent/readme/diagram_role_semantics.py",
    ),
    "document_compilation": (
        "src/readme_agent/presentation/verified_template_draft.py",
        "src/readme_agent/presentation/verified_template_runtime.py",
        "src/readme_agent/presentation/verified_template_sections.py",
        "src/readme_agent/readme/document_renderer.py",
        "src/readme_agent/readme/document_templates.py",
    ),
    "header_visual": (
        "src/readme_agent/readme/header_badges.py",
        "src/readme_agent/readme/header_visual.py",
        "src/readme_agent/readme/header_visual_models.py",
        "src/readme_agent/readme/header_visual_validation.py",
    ),
    "presentation_template": ("templates/readme/repository-presentation-v1.json",),
    "source_bound_plan_and_patch": (
        "src/readme_agent/presentation/document_planner.py",
        "src/readme_agent/presentation/git_patch.py",
        "src/readme_agent/presentation/planner.py",
    ),
    "stage_bundle_persistence": (
        "src/readme_agent/evidence/redaction.py",
        "src/readme_agent/evidence/writer.py",
        "src/readme_agent/supervisor/local_poc_evidence.py",
        "src/readme_agent/supervisor/local_poc_snapshot_evidence.py",
        "src/readme_agent/supervisor/portfolio_scheduler/contracts.py",
        "src/readme_agent/supervisor/portfolio_scheduler/lane.py",
        "src/readme_agent/supervisor/portfolio_scheduler/reducer.py",
    ),
}


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SelectedDependencyV1(_StrictFrozenModel):
    dependency_id: str = Field(min_length=3)
    files: dict[str, str] = Field(min_length=1)

    @field_validator("files")
    @classmethod
    def _hashes_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        invalid = any(
            len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)
            for digest in value.values()
        )
        if invalid:
            raise ValueError("dependency file identities must be lowercase SHA-256")
        return dict(sorted(value.items()))


class StageDependencyManifestV1(_StrictFrozenModel):
    schema_version: Literal["StageDependencyManifestV1"] = "StageDependencyManifestV1"
    repository: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    stage: StageNameV1
    ecosystem: str
    upstream_receipt_ids: list[str] = Field(default_factory=list)
    dependencies: list[SelectedDependencyV1] = Field(min_length=1)
    stage_key: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    identity: dict[str, object] = {
        "repository": repository,
        "source_revision": source_revision,
        "stage": stage,
        "ecosystem": ecosystem,
        "upstream_receipt_ids": upstream,
        "dependencies": [item.model_dump(mode="json") for item in ordered],
    }
    return StageDependencyManifestV1(
        repository=repository,
        source_revision=source_revision,
        stage=stage,
        ecosystem=ecosystem,
        upstream_receipt_ids=upstream,
        dependencies=ordered,
        stage_key=canonical_sha256(identity),
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
    for dependency_id, relative_paths in sorted(_CANDIDATE_DEPENDENCY_GROUPS.items()):
        files: dict[str, str] = {}
        for relative_path in relative_paths:
            path = _REPOSITORY_ROOT / relative_path
            if not path.is_file():
                raise FileNotFoundError(f"candidate stage dependency is missing: {relative_path}")
            files[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
        dependencies.append(SelectedDependencyV1(dependency_id=dependency_id, files=files))
    return build_stage_dependency_manifest(
        repository=repository,
        source_revision=source_revision,
        stage="CANDIDATE",
        ecosystem=ecosystem or "unknown",
        dependencies=dependencies,
    )
