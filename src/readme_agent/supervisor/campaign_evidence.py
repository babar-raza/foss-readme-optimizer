"""Minimum campaign evidence aggregation for acceleration and three-slice work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SupportedCampaignId = Literal["CAMP-SHARED-ACCELERATION", "CAMP-THREE-SLICES"]
TaskEvidenceVerdict = Literal["OPEN", "PARTIAL", "CLOSED", "BLOCKED_EXTERNAL"]


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceBindingV1(_StrictFrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    requirement_ids: list[str] = Field(default_factory=list)


class CampaignTaskVerdictV1(_StrictFrozenModel):
    task_id: str
    requirement_ids: list[str]
    verdict: TaskEvidenceVerdict
    evidence: list[EvidenceBindingV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def _closed_requires_evidence(self) -> CampaignTaskVerdictV1:
        if self.verdict == "CLOSED" and not self.evidence:
            raise ValueError("CLOSED task verdict requires exact evidence bindings")
        covered = {rid for binding in self.evidence for rid in binding.requirement_ids}
        if self.verdict == "CLOSED" and covered != set(self.requirement_ids):
            raise ValueError("CLOSED task evidence must cover every mapped requirement exactly")
        return self


class CampaignEvidenceManifestV1(_StrictFrozenModel):
    schema_version: Literal["CampaignEvidenceManifestV1"] = "CampaignEvidenceManifestV1"
    campaign_id: SupportedCampaignId
    graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_verdicts: list[CampaignTaskVerdictV1] = Field(min_length=1)
    requirement_ids: list[str]
    durable_state_version: int = Field(ge=0)
    transition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    replay_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    replay_result: Literal["ACCEPTED", "PENDING"]


def build_campaign_evidence_manifest(
    *,
    campaign_id: SupportedCampaignId,
    graph_sha256: str,
    task_verdicts: list[CampaignTaskVerdictV1],
    durable_state_version: int,
    transition_payload: dict[str, object],
) -> CampaignEvidenceManifestV1:
    """Build a deterministic pending aggregate without caller-controlled acceptance."""

    return _construct_campaign_evidence_manifest(
        campaign_id=campaign_id,
        graph_sha256=graph_sha256,
        task_verdicts=task_verdicts,
        durable_state_version=durable_state_version,
        transition_id=canonical_sha256(transition_payload),
        replay_result="PENDING",
    )


def _construct_campaign_evidence_manifest(
    *,
    campaign_id: SupportedCampaignId,
    graph_sha256: str,
    task_verdicts: list[CampaignTaskVerdictV1],
    durable_state_version: int,
    transition_id: str,
    replay_result: Literal["ACCEPTED", "PENDING"],
) -> CampaignEvidenceManifestV1:

    ordered = sorted(task_verdicts, key=lambda item: item.task_id)
    requirement_ids = sorted({rid for item in ordered for rid in item.requirement_ids})
    replay_id = canonical_sha256(
        {
            "campaign_id": campaign_id,
            "graph_sha256": graph_sha256,
            "task_verdicts": [item.model_dump(mode="json") for item in ordered],
            "durable_state_version": durable_state_version,
            "transition_id": transition_id,
        }
    )
    body = {
        "campaign_id": campaign_id,
        "graph_sha256": graph_sha256,
        "task_verdicts": [item.model_dump(mode="json") for item in ordered],
        "requirement_ids": requirement_ids,
        "durable_state_version": durable_state_version,
        "transition_id": transition_id,
        "replay_id": replay_id,
        "replay_result": replay_result,
    }
    return CampaignEvidenceManifestV1(
        campaign_id=campaign_id,
        graph_sha256=graph_sha256,
        task_verdicts=ordered,
        requirement_ids=requirement_ids,
        durable_state_version=durable_state_version,
        transition_id=transition_id,
        replay_id=replay_id,
        replay_result=replay_result,
        manifest_sha256=canonical_sha256(body),
    )


def graph_campaign_tasks(
    graph_path: Path, campaign_id: SupportedCampaignId
) -> dict[str, list[str]]:
    """Load exact task and requirement membership from the governed graph."""

    payload = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
    return {
        task["task_id"]: sorted(task.get("requirement_ids", []))
        for task in payload["taskcards"]
        if task.get("campaign_id") == campaign_id
    }


def validate_campaign_evidence_manifest(
    manifest: CampaignEvidenceManifestV1,
    *,
    graph_path: Path,
    repository_root: Path,
    durable_transition_payload: dict[str, object],
) -> None:
    """Replay graph membership, manifest identity, and every claimed evidence byte."""

    graph_bytes = graph_path.read_bytes()
    if hashlib.sha256(graph_bytes).hexdigest() != manifest.graph_sha256:
        raise ValueError("campaign graph hash mismatch")
    if canonical_sha256(durable_transition_payload) != manifest.transition_id:
        raise ValueError("durable transition identity mismatch")
    transition_version = durable_transition_payload.get("state_version")
    if transition_version is not None and transition_version != manifest.durable_state_version:
        raise ValueError("durable state version mismatch")
    expected_tasks = graph_campaign_tasks(graph_path, manifest.campaign_id)
    actual_tasks = {item.task_id: sorted(item.requirement_ids) for item in manifest.task_verdicts}
    if actual_tasks != expected_tasks:
        raise ValueError("campaign task or requirement membership mismatch")
    expected_requirements = sorted({rid for values in expected_tasks.values() for rid in values})
    if manifest.requirement_ids != expected_requirements:
        raise ValueError("campaign requirement union mismatch")
    for task in manifest.task_verdicts:
        for binding in task.evidence:
            path = repository_root / binding.path
            if not path.is_file():
                raise ValueError(f"campaign evidence missing: {binding.path}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != binding.sha256:
                raise ValueError(f"campaign evidence hash mismatch: {binding.path}")
            if not set(binding.requirement_ids).issubset(task.requirement_ids):
                raise ValueError("evidence claims a requirement outside its task")
    rebuilt = _construct_campaign_evidence_manifest(
        campaign_id=manifest.campaign_id,
        graph_sha256=manifest.graph_sha256,
        task_verdicts=manifest.task_verdicts,
        durable_state_version=manifest.durable_state_version,
        transition_id=manifest.transition_id,
        replay_result=manifest.replay_result,
    )
    if (
        rebuilt.replay_id != manifest.replay_id
        or rebuilt.manifest_sha256 != manifest.manifest_sha256
    ):
        raise ValueError("campaign manifest replay identity mismatch")


def accept_campaign_evidence_manifest(
    manifest: CampaignEvidenceManifestV1,
    *,
    graph_path: Path,
    repository_root: Path,
    durable_transition_payload: dict[str, object],
) -> CampaignEvidenceManifestV1:
    """Promote only an independently replayed pending manifest to ACCEPTED."""

    if manifest.replay_result != "PENDING":
        raise ValueError("only a pending campaign manifest can be accepted")
    validate_campaign_evidence_manifest(
        manifest,
        graph_path=graph_path,
        repository_root=repository_root,
        durable_transition_payload=durable_transition_payload,
    )
    accepted = _construct_campaign_evidence_manifest(
        campaign_id=manifest.campaign_id,
        graph_sha256=manifest.graph_sha256,
        task_verdicts=manifest.task_verdicts,
        durable_state_version=manifest.durable_state_version,
        transition_id=manifest.transition_id,
        replay_result="ACCEPTED",
    )
    validate_campaign_evidence_manifest(
        accepted,
        graph_path=graph_path,
        repository_root=repository_root,
        durable_transition_payload=durable_transition_payload,
    )
    return accepted
