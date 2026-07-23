"""Lifecycle-complete manifest for restartable production supervision."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.state.lifecycle_schema import CheckpointV1, TriggerEnvelopeV2, TriggerStatusV2


class RunManifestV3(RunManifestV2):
    manifest_version: Literal[3] = 3
    trigger: TriggerEnvelopeV2 | None = None
    trigger_status: TriggerStatusV2 | None = None
    checkpoints: list[CheckpointV1] = Field(default_factory=list)
    facts: dict = Field(default_factory=dict)
    presentation_plan: dict = Field(default_factory=dict)
    authorization: dict = Field(default_factory=dict)
    verifier: dict = Field(default_factory=dict)
    effects: list[dict] = Field(default_factory=list)
    requirement_results: dict[str, bool] = Field(default_factory=dict)
