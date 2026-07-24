"""Typed checksum inventory for a reproducible local presentation proof."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalPilotProposalProofV1(_StrictModel):
    org_repo: str
    source_revision: str
    facts_hash: str
    candidate_sha256: str
    operation_ids: list[str]
    first_run_executable: bool
    independent_verdict: Literal["accepted", "rejected"]
    identical_rerun_noop: bool
    artifact_sha256: dict[str, str]


class LocalProofManifestV1(_StrictModel):
    schema_version: Literal[1] = 1
    generated_at: str
    control_revision: str
    source_facts_bundle_sha256: str
    runtime_authority: Literal["readme-agent supervise"]
    proof_execution: Literal["canonical deterministic proposal contracts"]
    product_remote_writes: Literal[0] = 0
    pilots: list[LocalPilotProposalProofV1] = Field(min_length=1)
    accepted: bool
