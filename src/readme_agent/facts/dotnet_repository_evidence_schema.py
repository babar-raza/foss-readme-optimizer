"""Typed, content-addressed .NET repository evidence contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.aspose_org_format_contract import (
    AsposeOrgFormatExtractionV1,
    canonical_dependency_sha256,
)

ASPOSE_ORG_DOTNET_API_RELATIVE_PATH = "scripts/pipeline/extraction/api_surface.py"


def _canonical_hash(value: BaseModel) -> str:
    payload = json.dumps(
        value.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DotnetApiMemberEvidenceV1(BaseModel):
    """One repository-declared public member."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    kind: Literal["method", "property"]
    summary: str | None = None


class DotnetApiTypeEvidenceV1(BaseModel):
    """One public .NET type bound to exact repository bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    origin: Literal["aspose_org", "local_lexer"]
    name: str = Field(min_length=1)
    qualified_name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    summary: str | None = None
    source_path: str = Field(min_length=1)
    source_line: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    members: tuple[DotnetApiMemberEvidenceV1, ...] = ()


class DotnetExampleEvidenceV1(BaseModel):
    """One bounded repository-authored example candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    class_name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_paths: tuple[str, ...] = Field(min_length=1)
    required_symbols: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_code_hash(self) -> DotnetExampleEvidenceV1:
        actual = hashlib.sha256(self.code.encode("utf-8")).hexdigest()
        if actual != self.code_sha256:
            raise ValueError("example code hash does not match code")
        return self


class DotnetBoundaryEvidenceV1(BaseModel):
    """Raw implementation-boundary evidence, never visitor prose by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    kind: Literal["not_implemented", "not_supported", "obsolete"]
    source_path: str = Field(min_length=1)
    source_line: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_text: str = Field(min_length=1)


class DotnetFormatEvidenceV1(BaseModel):
    """One functionally corroborated format direction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    format: str = Field(min_length=1)
    direction: Literal["import", "export", "both"]
    source_path: str = Field(min_length=1)
    source_line: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AsposeOrgDotnetExtractionV1(BaseModel):
    """Content-addressed result from the sibling .NET API extractor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["available", "unavailable"]
    completeness: Literal["complete", "partial", "unavailable"]
    api_types: tuple[DotnetApiTypeEvidenceV1, ...] = ()
    extractor_revision: str | None = None
    extractor_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    dependency_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    dependency_files: dict[str, str] = Field(default_factory=dict)
    detail: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_provenance(self) -> AsposeOrgDotnetExtractionV1:
        if self.dependency_files:
            if self.dependency_sha256 != canonical_dependency_sha256(self.dependency_files):
                raise ValueError("API extractor dependency hash does not match dependency files")
            if self.extractor_sha256 != self.dependency_files.get(
                ASPOSE_ORG_DOTNET_API_RELATIVE_PATH
            ):
                raise ValueError("direct API extractor hash does not match dependency receipt")
        if self.status == "available" and not (
            self.extractor_revision
            and self.extractor_sha256
            and self.dependency_sha256
            and self.dependency_files
        ):
            raise ValueError("available API extraction requires complete provenance")
        if self.status == "unavailable" and self.completeness != "unavailable":
            raise ValueError("unavailable extraction must have unavailable completeness")
        return self

    def receipt_sha256(self) -> str:
        return _canonical_hash(self)


class DotnetRepositoryEvidenceCatalogV1(BaseModel):
    """Immutable evidence catalog consumed by later .NET truth selection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(min_length=7)
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_manifest_path: str = Field(min_length=1)
    selected_product_root: str = Field(min_length=1)
    root_role_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    api_extraction: AsposeOrgDotnetExtractionV1
    api_types: tuple[DotnetApiTypeEvidenceV1, ...] = ()
    format_extraction: AsposeOrgFormatExtractionV1
    formats: tuple[DotnetFormatEvidenceV1, ...] = ()
    examples: tuple[DotnetExampleEvidenceV1, ...] = ()
    boundaries: tuple[DotnetBoundaryEvidenceV1, ...] = ()
    readiness: Literal["ready", "partial", "blocked"]
    observations: tuple[str, ...] = ()

    def canonical_hash(self) -> str:
        return _canonical_hash(self)
