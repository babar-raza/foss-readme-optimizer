"""Typed evidence contracts for repository-native Python golden workflows."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldenSourceFileV1(_StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class GoldenArtifactInventoryV1(_StrictModel):
    root: str = Field(min_length=1)
    count: int = Field(ge=1)
    inventory_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    files: tuple[GoldenSourceFileV1, ...] = Field(min_length=1)


class GoldenWorkflowCommandV1(_StrictModel):
    kind: Literal["install_requirements", "regenerate_all", "regenerate_selected", "verify"]
    command: str = Field(min_length=1)
    source: GoldenSourceFileV1
    case_id: str | None = None


class GoldenEnvironmentControlV1(_StrictModel):
    name: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    enabled_values: tuple[str, ...] = Field(min_length=1)
    source: GoldenSourceFileV1


class GoldenRendererFallbackV1(_StrictModel):
    name: str = Field(min_length=1)
    mechanism: Literal["python_import", "executable"]
    identifier: str = Field(min_length=1)
    source: GoldenSourceFileV1


class GoldenDependencyGroupV1(_StrictModel):
    name: str = Field(min_length=1)
    requirements: tuple[str, ...] = Field(min_length=1)
    source: GoldenSourceFileV1


class GoldenVisualDiffPolicyV1(_StrictModel):
    required_python_packages: tuple[str, ...] = Field(min_length=1)
    renderer_any_of: tuple[str, ...] = Field(min_length=1)
    source: GoldenSourceFileV1


class GoldenFontPolicyV1(_StrictModel):
    environment_name: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    enabled_values: tuple[str, ...] = Field(min_length=1)
    default_strategy: Literal["built_in_fonts_unless_unicode_required"]
    enabled_strategy: Literal["search_system_font_directories"]
    source: GoldenSourceFileV1


class PythonGoldenWorkflowEvidenceV1(_StrictModel):
    schema_version: Literal[1] = 1
    artifact_inventory: GoldenArtifactInventoryV1
    regeneration_tool: GoldenSourceFileV1
    verification_test: GoldenSourceFileV1
    helper_module: GoldenSourceFileV1
    commands: tuple[GoldenWorkflowCommandV1, ...] = Field(min_length=2)
    case_ids: tuple[str, ...]
    representative_case_ids: tuple[str, ...]
    comparison_mode: Literal["semantic_manifest"]
    failure_output_path: str = Field(min_length=1)
    environment_controls: tuple[GoldenEnvironmentControlV1, ...]
    renderer_fallbacks: tuple[GoldenRendererFallbackV1, ...]
    dependency_groups: tuple[GoldenDependencyGroupV1, ...] = Field(min_length=1)
    visual_diff_policy: GoldenVisualDiffPolicyV1
    font_policy: GoldenFontPolicyV1 | None = None
    source_files: tuple[GoldenSourceFileV1, ...] = Field(min_length=3)
