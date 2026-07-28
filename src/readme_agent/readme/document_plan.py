"""Typed, source-bound operations for a complete README presentation candidate."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1

DocumentOperation = Literal[
    "preserve",
    "insert_before",
    "insert_after",
    "replace",
    "move_exact",
    "remove",
]
ProtectedContentTreatment = Literal[
    "preserve",
    "additive",
    "authoritative_fact_correction",
    "presentation_policy_correction",
]
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.:-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationSpanAdoptionV1(_StrictModel):
    """Proof that adopting the outer span preserved the complete source document."""

    marker_schema_version: Literal[3] | None = None
    metadata_location: Literal["durable_evidence"] = "durable_evidence"
    already_adopted: bool
    source_document_sha256: str
    source_inner_sha256: str
    source_inner_bytes: int = Field(ge=0)
    preservation_check: Literal["byte_identical"]

    @field_validator("source_document_sha256", "source_inner_sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("adoption hashes must be lowercase SHA-256 values")
        return value


class ReadmeDocumentOperationV1(_StrictModel):
    """One deterministic operation against the pre-adoption inner README bytes."""

    operation_id: str
    operation: DocumentOperation
    path: Literal["README.md"] = "README.md"
    coordinate_space: Literal["presentation_inner_utf8"] = "presentation_inner_utf8"
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(ge=0)
    expected_sha256: str
    replacement_text: str
    replacement_sha256: str
    fact_ids: list[str] = Field(default_factory=list)
    protected_content_treatment: ProtectedContentTreatment
    rationale: str = Field(min_length=1)
    validators: list[str] = Field(min_length=1)
    rollback: str = Field(min_length=1)
    stop_conditions: list[str] = Field(min_length=1)

    @field_validator("operation_id")
    @classmethod
    def _descriptive_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError(f"invalid document operation ID {value!r}")
        return value

    @field_validator("expected_sha256", "replacement_sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("document-operation hashes must be lowercase SHA-256 values")
        return value

    @model_validator(mode="after")
    def _valid_span(self) -> ReadmeDocumentOperationV1:
        if self.source_byte_end < self.source_byte_start:
            raise ValueError("source_byte_end must be >= source_byte_start")
        if self.operation in {"insert_before", "insert_after"} and (
            self.source_byte_start != self.source_byte_end
        ):
            raise ValueError("insert operations require an empty source span")
        if self.operation == "remove" and self.replacement_text:
            raise ValueError("remove operations require an empty replacement")
        if (
            self.protected_content_treatment == "authoritative_fact_correction"
            and not self.fact_ids
        ):
            raise ValueError("authoritative corrections require fact citations")
        return self


class ReadmeDocumentPlanV1(_StrictModel):
    """Complete, reproducible README plan below the repository-surface plan."""

    schema_version: Literal[1] = 1
    org_repo: str
    immutable_base_revision: str
    facts_hash: str
    template_sha256: str
    source_sha256: str
    adoption: PresentationSpanAdoptionV1
    header_visuals: ReadmeHeaderVisualV1 | None = None
    operations: list[ReadmeDocumentOperationV1]
    candidate_sha256: str

    @field_validator("facts_hash", "template_sha256", "source_sha256", "candidate_sha256")
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("document-plan hashes must be lowercase SHA-256 values")
        return value

    @model_validator(mode="after")
    def _unique_non_overlapping_operations(self) -> ReadmeDocumentPlanV1:
        operation_ids = [operation.operation_id for operation in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("document plan contains duplicate operation IDs")
        occupied = sorted(
            (
                operation.source_byte_start,
                operation.source_byte_end,
                operation.operation_id,
            )
            for operation in self.operations
            if operation.source_byte_start != operation.source_byte_end
        )
        for previous, current in zip(occupied, occupied[1:], strict=False):
            if current[0] < previous[1]:
                raise ValueError(f"document operations {previous[2]!r} and {current[2]!r} overlap")
        return self
