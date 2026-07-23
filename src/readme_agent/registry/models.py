"""Pydantic schemas for data/products.json and config/policies/*.yml."""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from readme_agent.registry.surface_ownership import (
    SurfaceOwnershipMapV1,
    default_surface_ownership_map,
)

Mode = Literal["full", "dry_run", "disabled"]


class ProductEntry(BaseModel):
    """One entry in data/products.json — the allow-list.

    The upstream-shaped fields (family, platform, repo_name, repo_url,
    clone_url, active, discovered_via, overrides) are copied verbatim from
    aspose.org's own data/products.json so the file stays re-syncable. mode/
    ecosystem/policy_profile are additive fields this project owns.
    """

    family: str
    platform: str
    repo_name: str
    repo_url: str
    clone_url: str
    active: bool
    discovered_via: str
    overrides: dict | None = None

    mode: Mode
    ecosystem: str | None = None
    policy_profile: str | None = None

    @property
    def org(self) -> str:
        # repo_url is https://github.com/{org}/{repo_name}
        path = urlparse(self.repo_url).path.strip("/")
        return path.split("/")[0]

    @property
    def org_repo(self) -> str:
        return f"{self.org}/{self.repo_name}"


class LinkSpec(BaseModel):
    url: str
    family_url: str
    label: str
    utm: dict[str, str] | None = None


class LicenseElement(BaseModel):
    detected_license: str


class RelationshipElement(BaseModel):
    min_sentences: int = 2
    talking_points: list[str] = Field(default_factory=list)


class RequiredElements(BaseModel):
    license_mentioned: LicenseElement
    products_org_link: LinkSpec
    products_com_link: LinkSpec
    relationship_explained: RelationshipElement


class WordLimit(BaseModel):
    min: int
    max: int


class BlockPolicy(BaseModel):
    word_limit: WordLimit
    prohibited_terms: list[str] = Field(default_factory=list)
    link_whitelist_domains: list[str] = Field(default_factory=list)


class PolicyProfile(BaseModel):
    schema_version: int
    policy_profile: str
    required_elements: RequiredElements
    secondary_links: list[str] = Field(default_factory=list)
    block: BlockPolicy
    surface_ownership: SurfaceOwnershipMapV1 = Field(default_factory=default_surface_ownership_map)

    @field_validator("schema_version")
    @classmethod
    def _supported_schema_version(cls, v: int) -> int:
        if v != 2:
            raise ValueError(f"unsupported policy schema_version {v!r}, expected 2")
        return v
