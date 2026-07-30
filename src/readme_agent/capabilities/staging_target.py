"""Fail-closed disposable-staging target manifest validation."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.capabilities.schema import OrgRepoRef


class StagingTargetV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_repository: OrgRepoRef
    target_repository: OrgRepoRef
    target_repository_id: int = Field(gt=0)
    default_branch: str = Field(min_length=1)
    initial_revision: str = Field(min_length=1)
    initial_readme_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposable: Literal[True] = True


class StagingTargetManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    cohort_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    targets: tuple[StagingTargetV1, ...]

    def target_for(self, source_repository: str, target_repository: str) -> StagingTargetV1:
        matches = [
            item
            for item in self.targets
            if item.source_repository == source_repository
            and item.target_repository == target_repository
        ]
        if len(matches) != 1:
            raise ValueError("staging source/target pair is absent or duplicated")
        return matches[0]


def load_staging_target(
    manifest_path: str, source_repository: str, target_repository: str
) -> StagingTargetV1:
    path = Path(manifest_path).resolve()
    manifest = StagingTargetManifestV1.model_validate_json(path.read_text(encoding="utf-8"))
    return manifest.target_for(source_repository, target_repository)
