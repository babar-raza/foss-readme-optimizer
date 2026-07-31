"""Define stable candidate-span ownership and typed trusted repair actions."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.capabilities.schema import OrgRepoRef
from readme_agent.facts.trusted_readme_schema import ConfiguredStandardIdV1

CandidateSpanOwnerKindV1 = Literal["authored", "preserved", "normalizer", "assembly"]
TrustedRepairActionKindV1 = Literal[
    "remove_exact",
    "move_exact",
    "replace_exact",
    "rewrite_owned_span",
]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateSpanOwnershipRecordV1(_StrictFrozenModel):
    """One contiguous byte range with a stable producer or deterministic owner."""

    record_id: str = Field(pattern=r"^span-[0-9a-f]{24}$")
    owner_id: str = Field(min_length=1)
    owner_kind: CandidateSpanOwnerKindV1
    byte_start: int = Field(ge=0)
    byte_end: int = Field(gt=0)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    batch_id: str | None = None
    stable_segment_id: str | None = None
    producer_segment_id: str | None = None
    inherited_fact_ids: tuple[str, ...] = ()
    configured_standard_ids: tuple[ConfiguredStandardIdV1, ...] = ()
    normalization_operations: tuple[str, ...] = ()


class CandidateSpanOwnershipMapV1(_StrictFrozenModel):
    """Complete non-overlapping ownership map for exact final candidate bytes."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    org_repo: OrgRepoRef
    source_revision: str = Field(min_length=7)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    presentation_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalization_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_byte_length: int = Field(gt=0)
    records: tuple[CandidateSpanOwnershipRecordV1, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _records_cover_candidate(self) -> CandidateSpanOwnershipMapV1:
        cursor = 0
        record_ids: set[str] = set()
        for record in self.records:
            if record.record_id in record_ids:
                raise ValueError("candidate ownership record IDs must be unique")
            record_ids.add(record.record_id)
            if record.byte_start != cursor:
                raise ValueError("candidate ownership records must be contiguous and ordered")
            cursor = record.byte_end
        if cursor != self.candidate_byte_length:
            raise ValueError("candidate ownership records do not cover the complete candidate")
        return self

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class TrustedRepairActionV1(_StrictFrozenModel):
    """One grounded, hash-bound mutation and its exact candidate result."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    action_id: str = Field(pattern=r"^repair-[0-9a-f]{24}$")
    org_repo: OrgRepoRef
    source_revision: str = Field(min_length=7)
    finding_id: str = Field(min_length=1)
    action: TrustedRepairActionKindV1
    instruction: str = Field(min_length=1)
    quoted_candidate_span: str = Field(min_length=1)
    candidate_sha256_before: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256_after: str = Field(pattern=r"^[0-9a-f]{64}$")
    ownership_map_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_record_ids: tuple[str, ...] = Field(min_length=1)
    byte_start: int = Field(ge=0)
    byte_end: int = Field(gt=0)
    expected_old_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    replacement_text: str = ""
    replacement_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_record_sha256s: tuple[str, ...] = ()
    llm_author_calls: int = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _action_contract(self) -> TrustedRepairActionV1:
        if self.byte_end <= self.byte_start:
            raise ValueError("trusted repair action byte range is empty")
        if len(self.owner_record_ids) != len(set(self.owner_record_ids)):
            raise ValueError("trusted repair owner record IDs must be unique")
        if self.action != "rewrite_owned_span" and self.llm_author_calls:
            raise ValueError("exact trusted repair actions cannot record an LLM author call")
        return self

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def stable_record_id(value: object) -> str:
    """Return one deterministic short identifier without making it an authority hash."""

    return "span-" + _canonical_hash(value)[:24]


def stable_action_id(value: object) -> str:
    """Return one deterministic repair identifier from immutable action inputs."""

    return "repair-" + _canonical_hash(value)[:24]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
