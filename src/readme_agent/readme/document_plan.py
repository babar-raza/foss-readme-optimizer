"""Typed, source-bound operations for a complete README presentation candidate."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.terminology import EnterpriseTerminologyCorrectionV1
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
    StructuredFactCoordinateV1,
)
from readme_agent.readme.composition_lineage_models import ReadmeCompositionLedgerV1
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1
from readme_agent.readme.source_claim_risk import SourceClaimObligation
from readme_agent.state.assurance import ContentAssuranceV1

DocumentOperation = Literal[
    "preserve",
    "insert_before",
    "insert_after",
    "replace",
    "move_exact",
    "remove",
]
DocumentCoordinateSpace = Literal["presentation_inner_utf8", "candidate_utf8"]
ProtectedContentTreatment = Literal[
    "preserve",
    "additive",
    "authoritative_fact_correction",
    "presentation_policy_correction",
]
SourceClaimResolution = Literal[
    "deferred_verification",
    "verified_omission",
    "verified_equivalence",
    "verified_obligation_replacement",
    "authoritative_correction",
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
    coordinate_space: DocumentCoordinateSpace = "presentation_inner_utf8"
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
        if self.coordinate_space == "candidate_utf8" and self.operation != "move_exact":
            raise ValueError("candidate_utf8 coordinates are reserved for move_exact operations")
        if (
            self.protected_content_treatment == "authoritative_fact_correction"
            and not self.fact_ids
        ):
            raise ValueError("authoritative corrections require fact citations")
        return self


class CandidateContentProvenanceV1(_StrictModel):
    """Exact candidate span owned by repository facts and/or governed standards."""

    provenance_id: str
    authority_scope: Literal["factual_or_configured", "lineage_only"] = "factual_or_configured"
    lineage_operation_id: str | None = None
    candidate_byte_start: int = Field(ge=0)
    candidate_byte_end: int = Field(ge=0)
    fact_ids: list[str] = Field(default_factory=list)
    fact_coordinates: list[StructuredFactCoordinateV1] = Field(default_factory=list)
    configured_standard_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _complete_binding(self) -> CandidateContentProvenanceV1:
        if self.candidate_byte_end <= self.candidate_byte_start:
            raise ValueError("candidate provenance requires a nonempty span")
        if not (self.fact_ids or self.configured_standard_ids):
            raise ValueError("candidate provenance requires facts or governed standards")
        if self.authority_scope == "lineage_only" and self.fact_ids:
            raise ValueError("lineage-only provenance cannot claim factual authority")
        if self.authority_scope == "lineage_only" and not self.lineage_operation_id:
            raise ValueError("lineage-only provenance requires an exact operation owner")
        if self.authority_scope != "lineage_only" and self.lineage_operation_id is not None:
            raise ValueError("operation ownership is reserved for lineage-only provenance")
        if any(coordinate.fact_id not in self.fact_ids for coordinate in self.fact_coordinates):
            raise ValueError("candidate provenance coordinates require their owning fact IDs")
        return self


class SourceClaimResolutionV1(_StrictModel):
    """Explicit evidence-backed disposition for one source material-claim unit."""

    claim_id: str
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(ge=0)
    content_sha256: str
    resolution: SourceClaimResolution
    obligation_id: SourceClaimObligation | None = None
    fact_ids: list[str] = Field(default_factory=list)
    contradiction_fact_ids: list[str] = Field(default_factory=list)
    replacement_provenance_ids: list[str] = Field(default_factory=list)
    policy_corrections: list[SourceClaimPolicyCorrectionV1] = Field(default_factory=list)
    candidate_claim_id: str | None = None
    candidate_byte_start: int | None = Field(default=None, ge=0)
    candidate_byte_end: int | None = Field(default=None, ge=0)
    candidate_content_sha256: str | None = None
    evidence: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("content_sha256", "candidate_content_sha256")
    @classmethod
    def _valid_content_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("source-claim hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _complete_resolution(self) -> SourceClaimResolutionV1:
        if self.source_byte_end <= self.source_byte_start:
            raise ValueError("source-claim resolution requires a nonempty span")
        if self.resolution == "authoritative_correction" and not self.fact_ids:
            raise ValueError("authoritative correction requires accepted facts")
        if self.resolution == "presentation_policy_correction":
            if not self.policy_corrections:
                raise ValueError("presentation policy correction requires exact corrected spans")
        elif self.policy_corrections:
            raise ValueError("exact policy spans are reserved for policy corrections")
        if self.resolution == "deferred_verification" and (
            self.fact_ids
            or self.contradiction_fact_ids
            or self.obligation_id
            or self.replacement_provenance_ids
        ):
            raise ValueError(
                "deferred verification cannot cite facts or replacements as if verified"
            )
        if self.resolution == "verified_obligation_replacement" and (
            not self.fact_ids or self.obligation_id is None or not self.replacement_provenance_ids
        ):
            raise ValueError(
                "verified obligation replacement requires an obligation, facts, and provenance"
            )
        if self.contradiction_fact_ids and self.resolution != "verified_obligation_replacement":
            raise ValueError(
                "contradiction facts are reserved for verified obligation replacements"
            )
        if self.resolution not in {
            "verified_obligation_replacement",
            "verified_omission",
        } and (self.obligation_id is not None or self.replacement_provenance_ids):
            raise ValueError(
                "obligation replacement bindings are reserved for replacements and omissions"
            )
        if (
            self.resolution == "verified_omission"
            and self.replacement_provenance_ids
            and (not self.fact_ids or self.obligation_id is None)
        ):
            raise ValueError(
                "a governed omission replacement requires an obligation and accepted facts"
            )
        equivalence_fields = (
            self.candidate_claim_id,
            self.candidate_byte_start,
            self.candidate_byte_end,
            self.candidate_content_sha256,
        )
        if self.resolution == "verified_equivalence":
            if not self.fact_ids or any(value is None for value in equivalence_fields):
                raise ValueError(
                    "verified equivalence requires facts and an exact candidate claim binding"
                )
            if self.candidate_byte_end <= self.candidate_byte_start:  # type: ignore[operator]
                raise ValueError("verified equivalence requires a nonempty candidate span")
        elif any(value is not None for value in equivalence_fields):
            raise ValueError("candidate claim bindings are reserved for verified equivalence")
        return self


class ReadmeDocumentPlanV1(_StrictModel):
    """Complete, reproducible README plan below the repository-surface plan."""

    schema_version: Literal[1] = 1
    content_assurance: ContentAssuranceV1 = "repository_verified"
    org_repo: str
    immutable_base_revision: str
    facts_hash: str
    template_sha256: str
    source_sha256: str
    adoption: PresentationSpanAdoptionV1
    header_visuals: ReadmeHeaderVisualV1 | None = None
    contextual_links: ContextualLinkPlanV1 | None = None
    enterprise_terminology_corrections: list[EnterpriseTerminologyCorrectionV1] = Field(
        default_factory=list
    )
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None = None
    candidate_content_provenance: list[CandidateContentProvenanceV1] = Field(default_factory=list)
    source_claim_resolutions: list[SourceClaimResolutionV1] = Field(default_factory=list)
    composition_ledger: ReadmeCompositionLedgerV1 | None = None
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
        for coordinate_space in {operation.coordinate_space for operation in self.operations}:
            occupied = sorted(
                (
                    operation.source_byte_start,
                    operation.source_byte_end,
                    operation.operation_id,
                )
                for operation in self.operations
                if operation.coordinate_space == coordinate_space
                and operation.source_byte_start != operation.source_byte_end
            )
            for previous, current in zip(occupied, occupied[1:], strict=False):
                if current[0] < previous[1]:
                    raise ValueError(
                        f"document operations {previous[2]!r} and {current[2]!r} overlap"
                    )
        return self
