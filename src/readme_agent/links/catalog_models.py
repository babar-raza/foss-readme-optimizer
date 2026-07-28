"""Typed contracts for verified Aspose link catalogs and runtime lookup."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AsposeParentDomain = Literal["aspose.org", "aspose.com"]
AsposeLinkSurface = Literal["products", "docs", "kb", "blog", "reference"]
LinkContentEvidence = Literal["landing", "source_body", "live_body", "slug_only"]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkCatalogSourceV2(_StrictFrozenModel):
    """One reproducible input used to discover or verify catalog records."""

    source_type: Literal["sitemap", "source_db", "source_tree", "live_probe"]
    location: str = Field(min_length=1)
    revision_or_hash: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    http_status: int | None = None


class AsposeLinkRecordV2(_StrictFrozenModel):
    """One domain-bound target; only an HTTP-200 record can be selected."""

    record_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    parent_domain: AsposeParentDomain
    surface: AsposeLinkSurface
    url: str
    title: str = Field(min_length=1)
    family: str = Field(min_length=1)
    platforms: list[str] = Field(default_factory=list)
    subject_terms: list[str] = Field(default_factory=list)
    content_evidence: LinkContentEvidence
    source_type: Literal["sitemap", "source_db", "source_tree", "live_probe"]
    source_location: str = Field(min_length=1)
    source_revision_or_hash: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    http_status: int
    verified_at: str | None = None

    @field_validator("url")
    @classmethod
    def _https_parent_domain(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("catalog URLs must be absolute HTTPS URLs")
        return value

    @field_validator("platforms", "subject_terms")
    @classmethod
    def _normalized_unique_values(cls, values: list[str]) -> list[str]:
        normalized = [" ".join(value.casefold().split()) for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("catalog list values must be unique after normalization")
        return normalized

    @model_validator(mode="after")
    def _record_is_domain_pure_and_truthful(self) -> AsposeLinkRecordV2:
        hostname = (urlparse(self.url).hostname or "").casefold()
        if hostname != self.parent_domain and not hostname.endswith(f".{self.parent_domain}"):
            raise ValueError("catalog record URL crosses its parent-domain boundary")
        if self.http_status == 200 and self.verified_at is None:
            raise ValueError("HTTP-200 catalog records require verified_at")
        if self.http_status != 200 and self.verified_at is not None:
            raise ValueError("only HTTP-200 catalog records may carry verified_at")
        return self

    @property
    def linkable(self) -> bool:
        """Return whether deterministic selection may use this target."""

        if self.http_status != 200:
            return False
        if self.surface == "products":
            return self.content_evidence == "landing"
        return self.content_evidence in {"source_body", "live_body"}


class AsposeLinkCatalogProvenanceV2(_StrictFrozenModel):
    """Generation inputs and integrity metadata for one parent-domain catalog."""

    generated_at: str = Field(min_length=1)
    generator: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    sources: list[LinkCatalogSourceV2] = Field(min_length=1)
    total_records: int = Field(ge=1)
    verified_records: int = Field(ge=0)
    output_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class AsposeLinkCatalogV2(_StrictFrozenModel):
    """Domain-pure, checksum-addressed link catalog."""

    schema_version: Literal["2.0"] = "2.0"
    parent_domain: AsposeParentDomain
    provenance: AsposeLinkCatalogProvenanceV2
    records: dict[str, AsposeLinkRecordV2] = Field(min_length=1)

    @model_validator(mode="after")
    def _keys_counts_and_domains_match(self) -> AsposeLinkCatalogV2:
        if any(key != record.record_id for key, record in self.records.items()):
            raise ValueError("catalog record keys must match record_id")
        if any(record.parent_domain != self.parent_domain for record in self.records.values()):
            raise ValueError("catalog contains a record for another parent domain")
        urls = [record.url for record in self.records.values()]
        if len(urls) != len(set(urls)):
            raise ValueError("catalog contains duplicate target URLs")
        if self.provenance.total_records != len(self.records):
            raise ValueError("catalog total_records does not match records")
        verified = sum(record.http_status == 200 for record in self.records.values())
        if self.provenance.verified_records != verified:
            raise ValueError("catalog verified_records does not match records")
        return self


class AsposeLinkCatalogSetV1(_StrictFrozenModel):
    """The two parent-domain catalogs consumed through one lookup seam."""

    schema_version: Literal[1] = 1
    aspose_org: AsposeLinkCatalogV2
    aspose_com: AsposeLinkCatalogV2

    @model_validator(mode="after")
    def _domains_are_exact(self) -> AsposeLinkCatalogSetV1:
        if self.aspose_org.parent_domain != "aspose.org":
            raise ValueError("aspose_org catalog has the wrong parent domain")
        if self.aspose_com.parent_domain != "aspose.com":
            raise ValueError("aspose_com catalog has the wrong parent domain")
        return self

    @property
    def records(self) -> tuple[AsposeLinkRecordV2, ...]:
        return tuple(
            [
                *self.aspose_org.records.values(),
                *self.aspose_com.records.values(),
            ]
        )
