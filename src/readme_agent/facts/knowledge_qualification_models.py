"""Typed outcomes for offline portfolio knowledge-to-README qualification."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QualificationStatus = Literal[
    "qualified",
    "qualified_stale_fact_contract",
    "non_processable_no_implementation",
    "baseline_unavailable",
    "baseline_revision_mismatch",
    "facts_unavailable",
    "facts_invalid",
    "plan_unavailable",
    "render_failed",
    "validation_rejected",
]


class RepositoryKnowledgeQualificationV1(BaseModel):
    """One repository's deterministic, no-effect qualification outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    family: str
    platform: str
    source_revision: str | None
    status: QualificationStatus
    detail: str
    artifact_root: str
    facts_path: str | None = None
    facts_hash: str | None = None
    fact_acceptance_contract_current: bool | None = None
    candidate_sha256: str | None = None
    candidate_generated: bool = False
    document_valid: bool = False
    check_count: int = Field(default=0, ge=0)
    blocking_finding_count: int = Field(default=0, ge=0)
    blocking_gap_count: int = Field(default=0, ge=0)
    knowledge_considered_count: int = Field(default=0, ge=0)
    knowledge_selected_count: int = Field(default=0, ge=0)
    knowledge_rendered_count: int = Field(default=0, ge=0)
    knowledge_omitted_count: int = Field(default=0, ge=0)
    llm_provider_calls: Literal[0] = 0
    product_effects: Literal[0] = 0


class PortfolioKnowledgeQualificationV1(BaseModel):
    """Aggregate diagnostic; never a Gate-A or independent-review verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    generated_at: str
    registry_sha256: str
    selection_receipt_sha256: str
    generator_sha256: str
    fact_acceptance_contract_sha256: str
    denominator: int = Field(ge=1)
    processable: int = Field(ge=0)
    typed_dispositions: int = Field(ge=0)
    candidate_generated: int = Field(ge=0)
    document_valid: int = Field(ge=0)
    qualified_current_contract: int = Field(ge=0)
    qualified_stale_contract: int = Field(ge=0)
    status_counts: dict[str, int]
    entries: tuple[RepositoryKnowledgeQualificationV1, ...]
    llm_provider_calls: Literal[0] = 0
    product_effects: Literal[0] = 0
    gate_a_satisfied: Literal[False] = False


__all__ = [
    "PortfolioKnowledgeQualificationV1",
    "QualificationStatus",
    "RepositoryKnowledgeQualificationV1",
]
