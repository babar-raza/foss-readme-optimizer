"""Typed contracts for content-addressed Aspose.org format extraction."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ASPOSE_ORG_FORMATS_RELATIVE_PATH = "scripts/pipeline/extraction/formats.py"


def canonical_dependency_sha256(files: dict[str, str]) -> str:
    """Hash an exact path-to-content identity map."""

    payload = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AsposeOrgFormatEvidenceV1(BaseModel):
    """One direction result emitted by the upstream extractor."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    format: str = Field(min_length=1)
    direction: Literal["import", "export", "both", "detect", "enum_only", "none"]
    file: str = Field(min_length=1)
    line: int = Field(ge=1)
    functional: bool | None = None


class AsposeOrgFormatExtractionV1(BaseModel):
    """Version-bound result of one read-only Aspose.org extractor invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["available", "unavailable"]
    formats: list[AsposeOrgFormatEvidenceV1] = Field(default_factory=list)
    extractor_revision: str | None = None
    extractor_sha256: str | None = None
    dependency_sha256: str | None = None
    dependency_files: dict[str, str] = Field(default_factory=dict)
    detail: str

    @model_validator(mode="after")
    def _validate_provenance(self) -> AsposeOrgFormatExtractionV1:
        if self.dependency_files:
            if self.dependency_sha256 != canonical_dependency_sha256(self.dependency_files):
                raise ValueError("extractor dependency hash does not match dependency files")
            if self.extractor_sha256 != self.dependency_files.get(ASPOSE_ORG_FORMATS_RELATIVE_PATH):
                raise ValueError("direct extractor hash does not match formats.py dependency")
        if self.status == "available" and (
            self.extractor_revision is None
            or self.extractor_sha256 is None
            or self.dependency_sha256 is None
            or not self.dependency_files
        ):
            raise ValueError("available extraction requires complete content-addressed provenance")
        return self

    def receipt_sha256(self) -> str:
        """Return the checksum address of the complete immutable extraction receipt."""

        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
