"""Compact campaign briefs, repository packets, and worker receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.supervisor.stage_dependencies import StageDependencyManifestV1


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ActiveCampaignBriefV1(_StrictFrozenModel):
    schema_version: Literal["ActiveCampaignBriefV1"] = "ActiveCampaignBriefV1"
    campaign_id: str
    primary_task_id: str
    objective: str = Field(min_length=20)
    pipeline_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline_snapshot_root: str
    graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    allowed_effects: list[str]
    stop_conditions: list[str]


class RepositoryWorkPacketV1(_StrictFrozenModel):
    schema_version: Literal["RepositoryWorkPacketV1"] = "RepositoryWorkPacketV1"
    campaign_id: str
    task_id: str
    repository: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    target_stage: str
    stage_dependency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline_snapshot_root: str
    input_paths: list[str]
    output_root: str
    focused_checks: list[str]
    product_effects_allowed: Literal[False] = False


class WorkerStageReceiptV1(_StrictFrozenModel):
    schema_version: Literal["WorkerStageReceiptV1"] = "WorkerStageReceiptV1"
    campaign_id: str
    task_id: str
    repository: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    target_stage: str
    stage_dependency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_hashes: dict[str, str]
    focused_check_results: dict[str, Literal["PASSED", "FAILED"]]
    verdict: Literal["PASSED", "FAILED", "BLOCKED_EXTERNAL"]
    product_effect_count: Literal[0] = 0


def build_repository_work_packet(
    *,
    brief: ActiveCampaignBriefV1,
    task_id: str,
    dependency_manifest: StageDependencyManifestV1,
    input_paths: list[str],
    output_root: str,
    focused_checks: list[str],
) -> RepositoryWorkPacketV1:
    """Bind worker execution to one selected stage manifest and immutable snapshot."""

    return RepositoryWorkPacketV1(
        campaign_id=brief.campaign_id,
        task_id=task_id,
        repository=dependency_manifest.repository,
        source_revision=dependency_manifest.source_revision,
        target_stage=dependency_manifest.stage,
        stage_dependency_key=dependency_manifest.stage_key,
        pipeline_snapshot_id=brief.pipeline_snapshot_id,
        pipeline_snapshot_root=brief.pipeline_snapshot_root,
        input_paths=input_paths,
        output_root=output_root,
        focused_checks=focused_checks,
    )


def read_packet_input(packet: RepositoryWorkPacketV1, relative_path: str) -> bytes:
    """Read a declared input exclusively from the immutable pipeline snapshot."""

    normalized = relative_path.replace("\\", "/")
    if normalized not in packet.input_paths:
        raise ValueError(f"input is not declared by the work packet: {normalized}")
    root = Path(packet.pipeline_snapshot_root).resolve()
    target = (root / normalized).resolve()
    if root not in target.parents or not target.is_file():
        raise ValueError(f"packet input escapes or is absent from the snapshot: {normalized}")
    return target.read_bytes()
