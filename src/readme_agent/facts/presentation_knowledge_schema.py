"""Contracts for self-contained presentation-knowledge hints and selection evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationKnowledgeHintV1(_StrictModel):
    schema_version: Literal[1] = 1
    family: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    field: Literal["product.capabilities", "product.limitations"]
    text: str = Field(min_length=1)
    evidence_path: str = Field(min_length=1)
    anchors: list[str] = Field(min_length=1)
    source_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PresentationKnowledgeCatalogV1(_StrictModel):
    schema_version: Literal[1] = 1
    producer_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    producer_dirty_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository_count: int = Field(ge=1)
    source_file_count: int = Field(ge=1)
    hints: list[PresentationKnowledgeHintV1]


class PresentationKnowledgeDispositionV1(_StrictModel):
    hint_id: str = Field(min_length=1)
    field: Literal["product.capabilities", "product.limitations"]
    status: Literal["accepted", "rejected"]
    reason: str = Field(min_length=1)


class PresentationKnowledgeSelectionV1(_StrictModel):
    schema_version: Literal[1] = 1
    family: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    considered: int = Field(ge=0)
    accepted: int = Field(ge=0)
    rejected: int = Field(ge=0)
    dispositions: list[PresentationKnowledgeDispositionV1]


__all__ = [
    "PresentationKnowledgeCatalogV1",
    "PresentationKnowledgeDispositionV1",
    "PresentationKnowledgeHintV1",
    "PresentationKnowledgeSelectionV1",
]
