"""Lifecycle-complete manifest for restartable production supervision."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.state.assurance import ContentAssuranceV1
from readme_agent.state.lifecycle_schema import (
    AssuranceReadmePocStatusV1,
    CheckpointV1,
    ContentAssuranceTransitionV1,
    ReadmePocStatusV1,
    ReadmePocTransitionV1,
    ReadmePocTransitionV2,
    TriggerEnvelopeV2,
    TriggerStatusV2,
)


class RunManifestV3(RunManifestV2):
    manifest_version: Literal[3] = 3
    content_assurance: ContentAssuranceV1 = "repository_verified"
    trigger: TriggerEnvelopeV2 | None = None
    trigger_status: TriggerStatusV2 | None = None
    checkpoints: list[CheckpointV1] = Field(default_factory=list)
    facts: dict = Field(default_factory=dict)
    presentation_plan: dict = Field(default_factory=dict)
    authorization: dict = Field(default_factory=dict)
    verifier: dict = Field(default_factory=dict)
    effects: list[dict] = Field(default_factory=list)
    requirement_results: dict[str, bool] = Field(default_factory=dict)
    # `RPOC-070` (sprint charter Part B.2 Phase 5 Lane S / Part C.7): this
    # run's org/repo's README-POC lifecycle status at evidence-write time,
    # mirroring `trigger`/`trigger_status`'s own flattened-snapshot-plus-
    # history shape one status dimension over -- `readme_poc_status` is the
    # cheap at-a-glance field a portfolio report (`RPOC-071`) scans across
    # every repo's manifest; `readme_poc_transitions` is the full append-only
    # history for a repo whose evidence bundle needs the detail. `None`/`[]`
    # for any run that does not populate this (every run before RPOC-071
    # wires real production transitions), not a faked "already tracked."
    readme_poc_status: ReadmePocStatusV1 | AssuranceReadmePocStatusV1 | None = None
    readme_poc_transitions: list[
        ReadmePocTransitionV1 | ReadmePocTransitionV2 | ContentAssuranceTransitionV1
    ] = Field(default_factory=list)
