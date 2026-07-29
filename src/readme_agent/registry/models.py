"""Pydantic schemas for data/products.json and config/policies/*.yml."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from readme_agent.registry.surface_ownership import (
    SurfaceOwnershipMapV1,
    default_surface_ownership_map,
)

Mode = Literal["full", "dry_run", "disabled"]


class ProviderRepositoryIdentityV1(BaseModel):
    """Stable provider identity for one admitted repository."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    provider: Literal["github"] = "github"
    repository_id: StrictInt = Field(gt=0)
    node_id: str = Field(min_length=1)


class ProductEntry(BaseModel):
    """One entry in data/products.json — the allow-list.

    Schema-v2 entries bind a stable provider repository identity. The upstream-
    shaped fields remain refreshable; mode/ecosystem/policy_profile/overrides
    are agent-owned and stable-identity reconciliation preserves them.
    """

    registry_schema_version: Literal[1, 2] = 1
    provider_identity: ProviderRepositoryIdentityV1 | None = None

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

    @model_validator(mode="after")
    def version_two_requires_stable_provider_identity(self) -> ProductEntry:
        if self.registry_schema_version == 2 and self.provider_identity is None:
            raise ValueError("registry schema v2 entries require provider_identity")
        return self

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


class EvidenceBackedProductFact(BaseModel):
    """A policy-selected technical statement that repository files must prove."""

    value: str
    evidence_paths: list[str] = Field(min_length=1)
    required_symbols: list[str] = Field(default_factory=list)


class MinimalExamplePolicy(BaseModel):
    """Exact example text compiled in a disposable, secret-free workspace."""

    language: Literal["java", "dotnet", "python", "typescript", "go", "cpp", "rust"]
    class_name: str
    code: str
    evidence_paths: list[str] = Field(min_length=1)
    required_symbols: list[str] = Field(default_factory=list)


class ProductTruthPolicy(BaseModel):
    """Subjective positioning plus repository-verifiable technical assertions."""

    audience: list[str] = Field(min_length=1)
    problems_solved: list[str] = Field(min_length=1)
    capabilities: list[EvidenceBackedProductFact] = Field(min_length=1)
    formats: list[EvidenceBackedProductFact] = Field(min_length=1)
    limitations: list[EvidenceBackedProductFact] = Field(default_factory=list)
    minimal_example: MinimalExamplePolicy


class LinkDomainMaximaV1(BaseModel):
    """Configured Aspose parent-domain ceilings."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    aspose_org: StrictInt = Field(alias="aspose.org", ge=0)
    aspose_com: StrictInt = Field(alias="aspose.com", ge=0)


class LinkSurfaceMaximaV1(BaseModel):
    """Configured ceilings for every governed Aspose content surface."""

    model_config = ConfigDict(extra="forbid")

    products: StrictInt = Field(ge=0)
    docs: StrictInt = Field(ge=0)
    kb: StrictInt = Field(ge=0)
    blog: StrictInt = Field(ge=0)
    reference: StrictInt = Field(ge=0)


class LinkAllocationPolicyV1(BaseModel):
    """Configured-or-automatic README Aspose-link allocation contract."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    mode: Literal["auto", "configured"] = "auto"
    max_total: StrictInt | None = Field(default=None, ge=0)
    domain_maxima: LinkDomainMaximaV1 | None = None
    surface_maxima: LinkSurfaceMaximaV1 | None = None

    @model_validator(mode="after")
    def _mode_is_complete_and_consistent(self) -> LinkAllocationPolicyV1:
        configured_values = (self.max_total, self.domain_maxima, self.surface_maxima)
        if self.mode == "auto":
            if any(value is not None for value in configured_values):
                raise ValueError("auto link allocation cannot include configured maxima")
            return self
        if any(value is None for value in configured_values):
            raise ValueError(
                "configured link allocation requires max_total, domain_maxima, and surface_maxima"
            )
        assert self.max_total is not None
        assert self.domain_maxima is not None
        assert self.surface_maxima is not None
        maxima = [
            self.domain_maxima.aspose_org,
            self.domain_maxima.aspose_com,
            self.surface_maxima.products,
            self.surface_maxima.docs,
            self.surface_maxima.kb,
            self.surface_maxima.blog,
            self.surface_maxima.reference,
        ]
        if any(value > self.max_total for value in maxima):
            raise ValueError("configured domain and surface maxima cannot exceed max_total")
        return self


class PolicyProfile(BaseModel):
    schema_version: int
    policy_profile: str
    required_elements: RequiredElements
    secondary_links: list[str] = Field(default_factory=list)
    block: BlockPolicy
    link_allocation: LinkAllocationPolicyV1 = Field(default_factory=LinkAllocationPolicyV1)
    surface_ownership: SurfaceOwnershipMapV1 = Field(default_factory=default_surface_ownership_map)
    product_truth: ProductTruthPolicy | None = None

    @field_validator("schema_version")
    @classmethod
    def _supported_schema_version(cls, v: int) -> int:
        if v != 2:
            raise ValueError(f"unsupported policy schema_version {v!r}, expected 2")
        return v
