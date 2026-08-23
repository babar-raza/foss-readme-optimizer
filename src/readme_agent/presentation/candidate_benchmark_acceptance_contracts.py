"""Typed evidence contracts for candidate benchmark acceptance."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.presentation.candidate_benchmark_comparison import BenchmarkDispositionV1
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.validation.public_quality_contracts import PublicQualityCategory

DimensionVerdict = Literal["PASS", "FAIL", "NOT_APPLICABLE", "QUARANTINED", "UNKNOWN"]
AcceptanceStatus = Literal["BENCHMARK_ACCEPTANCE_PROVEN", "BENCHMARK_ACCEPTANCE_NOT_PROVEN"]

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def canonical_benchmark_acceptance_payload_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CandidateRubricEvidenceV1(_StrictModel):
    """Bind an otherwise-unbound rubric outcome to the exact candidate it scored."""

    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    outcome: RubricAcceptanceOutcome

    def canonical_hash(self) -> str:
        return canonical_benchmark_acceptance_payload_hash(self.model_dump(mode="json"))


class BenchmarkDimensionAcceptanceV1(_StrictModel):
    dimension_id: str = Field(min_length=1)
    benchmark_disposition: BenchmarkDispositionV1
    obligation: str = Field(min_length=1)
    verdict: DimensionVerdict
    evidence_paths_considered: tuple[str, ...] = ()
    evidence_categories_considered: tuple[PublicQualityCategory, ...] = ()
    blocking_finding_ids: tuple[str, ...] = ()
    failure_reason: str | None = None


class CandidateBenchmarkAcceptanceV1(_StrictModel):
    """Per-dimension benchmark evidence that cannot itself authorize publication."""

    schema_version: Literal[1] = 1
    acceptance_contract_version: Literal[1] = 1
    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    facts_hash: str = Field(min_length=1)
    comparison_identity_sha256: str = Field(pattern=_SHA256_PATTERN)
    benchmark_profile_sha256: str = Field(pattern=_SHA256_PATTERN)
    deterministic_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    factual_review_sha256: str = Field(pattern=_SHA256_PATTERN)
    visitor_review_sha256: str = Field(pattern=_SHA256_PATTERN)
    rubric_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    evidence_bundle_sha256: str = Field(pattern=_SHA256_PATTERN)
    predecessor_acceptance_sha256: str | None = None
    dimensions: tuple[BenchmarkDimensionAcceptanceV1, ...] = Field(min_length=1)
    applicable_dimension_ids: tuple[str, ...]
    quarantined_dimension_ids: tuple[str, ...]
    not_applicable_dimension_ids: tuple[str, ...]
    unresolved_dimension_ids: tuple[str, ...]
    hard_disqualifiers: tuple[str, ...] = ()
    acceptance_status: AcceptanceStatus
    failure_reasons: tuple[str, ...] = ()
    publishes_acceptance: Literal[False] = False
    transitions_lifecycle_state: Literal[False] = False
    replaces_rubric_30_of_30: Literal[False] = False

    @model_validator(mode="after")
    def _dimensions_are_unique(self) -> CandidateBenchmarkAcceptanceV1:
        ids = [item.dimension_id for item in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate benchmark acceptance dimensions must be unique")
        return self

    def canonical_hash(self) -> str:
        return canonical_benchmark_acceptance_payload_hash(self.model_dump(mode="json"))


__all__ = [
    "AcceptanceStatus",
    "BenchmarkDimensionAcceptanceV1",
    "CandidateBenchmarkAcceptanceV1",
    "CandidateRubricEvidenceV1",
    "DimensionVerdict",
    "canonical_benchmark_acceptance_payload_hash",
]
