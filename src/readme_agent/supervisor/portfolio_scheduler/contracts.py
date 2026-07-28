"""Typed identities for private stage attempts and reducer-owned receipts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PortfolioStageV1 = Literal["CANDIDATE_GENERATED", "DETERMINISTIC_VALIDATED"]


def canonical_sha256(value: object) -> str:
    """Hash canonical JSON while excluding observation-only formatting."""

    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StageFenceV1(_StrictFrozenModel):
    """Repository lifecycle identity a reducer must recheck before promotion."""

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    lifecycle_status: str
    facts_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    fact_acceptance_contract_hash: str | None = None
    prompt_hash: str | None = None
    candidate_hash: str | None = None
    generation: int = Field(default=1, ge=1)
    fence_token: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("org_repo")
    @classmethod
    def _org_repo_shape(cls, value: str) -> str:
        if value.count("/") != 1 or any(not part for part in value.split("/")):
            raise ValueError("org_repo must look like 'org/repo'")
        return value


class PortfolioStageWorkItemV1(_StrictFrozenModel):
    """One stable stage computation request, independent of its retry attempt."""

    schema_version: Literal[1] = 1
    campaign_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_stage: PortfolioStageV1
    fence: StageFenceV1
    dependency_hashes: dict[str, str] = Field(min_length=1)


class StageArtifactV1(_StrictFrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if (
            not normalized
            or normalized.startswith("/")
            or normalized.startswith("../")
            or "/../" in normalized
        ):
            raise ValueError("artifact path must remain relative to the attempt root")
        return normalized


class LaneResultV1(_StrictFrozenModel):
    """Validated stage output written before the final SEALED marker."""

    schema_version: Literal[1] = 1
    campaign_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_stage: PortfolioStageV1
    attempt: int = Field(ge=1)
    worker_identity: str
    fence_token: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifacts: list[StageArtifactV1] = Field(min_length=1)
    output_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_at: str = Field(default_factory=utc_now_iso)


class StageSealV1(_StrictFrozenModel):
    """Final marker binding request, result, and inventory bytes."""

    schema_version: Literal[1] = 1
    campaign_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_stage: PortfolioStageV1
    attempt: int = Field(ge=1)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_at: str = Field(default_factory=utc_now_iso)


class StageReceiptV1(_StrictFrozenModel):
    """Reducer acceptance authority for one exact stage result."""

    schema_version: Literal[1] = 1
    campaign_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_stage: PortfolioStageV1
    org_repo: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    fence_token: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_inventory: list[StageArtifactV1] = Field(min_length=1)
    validation_passed: Literal[True] = True
    promoted_at: str = Field(default_factory=utc_now_iso)


def build_stage_fence(
    *,
    org_repo: str,
    source_revision: str,
    lifecycle_status: str,
    facts_hash: str,
    fact_acceptance_contract_hash: str | None,
    prompt_hash: str | None,
    candidate_hash: str | None,
    generation: int = 1,
) -> StageFenceV1:
    """Create the recheck token from every lifecycle input the stage depends on."""

    identity = {
        "org_repo": org_repo,
        "source_revision": source_revision,
        "lifecycle_status": lifecycle_status,
        "facts_hash": facts_hash,
        "fact_acceptance_contract_hash": fact_acceptance_contract_hash,
        "prompt_hash": prompt_hash,
        "candidate_hash": candidate_hash,
        "generation": generation,
    }
    return StageFenceV1(
        org_repo=org_repo,
        source_revision=source_revision,
        lifecycle_status=lifecycle_status,
        facts_hash=facts_hash,
        fact_acceptance_contract_hash=fact_acceptance_contract_hash,
        prompt_hash=prompt_hash,
        candidate_hash=candidate_hash,
        generation=generation,
        fence_token=canonical_sha256(identity),
    )


def build_stage_work_item(
    *,
    target_stage: PortfolioStageV1,
    fence: StageFenceV1,
    dependency_hashes: dict[str, str],
) -> PortfolioStageWorkItemV1:
    """Derive stable campaign/work identities from complete stage dependencies."""

    campaign_contract = {
        "schema": "serial-stage-transaction-v1",
        "org_repo": fence.org_repo,
        "source_revision": fence.source_revision,
        "dependency_hashes": dict(sorted(dependency_hashes.items())),
    }
    campaign_id = canonical_sha256(campaign_contract)
    work_identity = {
        "campaign_id": campaign_id,
        "org_repo": fence.org_repo,
        "source_revision": fence.source_revision,
        "target_stage": target_stage,
        "dependency_hashes": dict(sorted(dependency_hashes.items())),
    }
    return PortfolioStageWorkItemV1(
        campaign_id=campaign_id,
        work_id=canonical_sha256(work_identity),
        target_stage=target_stage,
        fence=fence,
        dependency_hashes=dependency_hashes,
    )
