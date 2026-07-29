"""Typed contracts for complete repository-source discovery observations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

DiscoveryClassification = Literal["matched", "ambiguous", "unmatched"]
DiscoveryDisposition = Literal["admit_candidate", "review_required"]
SourceScanStatus = Literal["complete", "failed"]


class DiscoverySourceV1(BaseModel):
    """One explicitly authorized source that discovery may inventory read-only."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    source_id: str
    provider: Literal["github"] = "github"
    organization: str
    family_hint: str | None = None
    enabled: bool = True

    @classmethod
    def from_family(cls, family: dict) -> DiscoverySourceV1:
        organization = str(family["github_org"])
        return cls(
            source_id=f"github-org:{organization}",
            organization=organization,
            family_hint=str(family["family"]) if family.get("family") else None,
        )


class DiscoveryObservationV1(BaseModel):
    """One repository observed from an authorized source, matched or otherwise."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    source_id: str
    provider: Literal["github"] = "github"
    provider_repository_id: StrictInt
    provider_node_id: str
    full_name: str
    name: str
    html_url: str
    clone_url: str
    visibility: Literal["public", "private", "internal", "unknown"] = "unknown"
    default_branch: str | None = None
    archived: bool = False
    pushed_at: str | None = None
    updated_at: str | None = None
    topics: list[str] = Field(default_factory=list)
    primary_language: str | None = None
    observed_at: str
    classification: DiscoveryClassification
    classification_reason: str
    disposition: DiscoveryDisposition
    family: str | None = None
    platform: str | None = None

    @model_validator(mode="after")
    def matched_observations_have_registry_coordinates(self) -> DiscoveryObservationV1:
        coordinates = self.family is not None and self.platform is not None
        if self.classification == "matched" and not coordinates:
            raise ValueError("matched observations require family and platform")
        if self.classification != "matched" and coordinates:
            raise ValueError("only matched observations may carry family and platform")
        return self

    def to_registry_entry(self) -> dict:
        if self.classification != "matched":
            raise ValueError("only matched observations may become registry entries")
        assert self.family is not None
        assert self.platform is not None
        return {
            "family": self.family,
            "platform": self.platform,
            "repo_name": self.name,
            "repo_url": self.html_url,
            "clone_url": self.clone_url,
            "active": not self.archived,
            "discovered_via": "github",
        }


class DiscoverySourceResultV1(BaseModel):
    """One source's terminal scan result."""

    model_config = ConfigDict(extra="forbid")

    source: DiscoverySourceV1
    status: SourceScanStatus
    observed_at: str
    observation_count: int = Field(ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def failure_requires_error(self) -> DiscoverySourceResultV1:
        if self.status == "failed" and not self.error:
            raise ValueError("failed source results require an error")
        if self.status == "complete" and self.error is not None:
            raise ValueError("complete source results cannot carry an error")
        return self


class DiscoveryInventoryV1(BaseModel):
    """Complete-or-explicitly-incomplete inventory over all requested sources."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    captured_at: str
    sources: list[DiscoverySourceResultV1]
    observations: list[DiscoveryObservationV1]
    complete: bool

    @model_validator(mode="after")
    def completeness_matches_source_results(self) -> DiscoveryInventoryV1:
        expected = all(source.status == "complete" for source in self.sources)
        if self.complete != expected:
            raise ValueError("inventory completeness must match source results")
        return self

    @property
    def failures(self) -> list[DiscoverySourceResultV1]:
        return [source for source in self.sources if source.status == "failed"]

    @property
    def matched_observations(self) -> list[DiscoveryObservationV1]:
        return [
            observation
            for observation in self.observations
            if observation.classification == "matched"
        ]
