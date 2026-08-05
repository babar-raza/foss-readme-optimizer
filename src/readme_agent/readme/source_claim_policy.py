"""Typed exact-span policy corrections within retained source claims."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SourceClaimPolicyCorrectionV1(BaseModel):
    """One policy-owned source span and its exact final-candidate replacement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    correction_id: str
    disposition: Literal["unwrap", "replace", "omit"]
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(gt=0)
    source_content_sha256: str
    candidate_byte_start: int = Field(ge=0)
    candidate_byte_end: int = Field(ge=0)
    candidate_content_sha256: str
    fact_ids: list[str] = Field(default_factory=list)
    configured_standard_ids: list[str] = Field(min_length=1)
    replacement_provenance_id: str | None = None
    operation_id: str

    @field_validator("source_content_sha256", "candidate_content_sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("source-claim policy correction requires lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _complete_correction(self) -> SourceClaimPolicyCorrectionV1:
        if self.source_byte_end <= self.source_byte_start:
            raise ValueError("source-claim policy correction requires a nonempty source span")
        if self.candidate_byte_end < self.candidate_byte_start:
            raise ValueError("source-claim policy correction has an inverted candidate span")
        has_replacement = self.candidate_byte_end > self.candidate_byte_start
        if has_replacement != (self.replacement_provenance_id is not None):
            raise ValueError("nonempty policy replacements require one exact provenance owner")
        if (
            has_replacement
            and "readme.enterprise_edition_terminology" in self.configured_standard_ids
            and not self.fact_ids
        ):
            raise ValueError("Enterprise terminology replacement requires an accepted fact")
        return self
