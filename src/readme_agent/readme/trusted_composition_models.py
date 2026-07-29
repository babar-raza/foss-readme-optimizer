"""Typed contracts for bounded LLM-first trusted README composition."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.capabilities.schema import OrgRepoRef
from readme_agent.facts.trusted_readme_schema import ConfiguredStandardIdV1

TrustedSourceActionV1 = Literal["preserve_exact", "rewrite"]
TrustedDraftSegmentKindV1 = Literal["preserve_exact", "authored"]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TrustedCompositionEnvelopeV1(_StrictFrozenModel):
    """Qualified input/output limits used to split one arbitrary README."""

    max_input_characters: int = Field(default=24_000, ge=2_000)
    max_output_characters: int = Field(default=16_000, ge=1_000)
    max_facts_per_batch: int = Field(default=24, ge=1, le=100)
    oversize_fact_preview_characters: int = Field(default=2_000, ge=256)


class TrustedCompositionSourceItemV1(_StrictFrozenModel):
    """One source fact offered to one bounded authoring call."""

    fact_id: str = Field(pattern=r"^readme\.inherited:[0-9a-f]{24}$")
    material_kind: str = Field(min_length=1)
    heading_path: tuple[str, ...] = ()
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(gt=0)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str = Field(min_length=1)
    text_truncated_for_context: bool = False


class TrustedSourceInventoryDecisionV1(_StrictFrozenModel):
    """The model's explicit disposition for one inherited source unit."""

    fact_id: str = Field(pattern=r"^readme\.inherited:[0-9a-f]{24}$")
    action: TrustedSourceActionV1
    rationale: str = Field(min_length=1)


class TrustedReadmeDraftSegmentV1(_StrictFrozenModel):
    """One ordered exact-preservation or LLM-authored candidate segment."""

    segment_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    kind: TrustedDraftSegmentKindV1
    markdown: str
    inherited_fact_ids: tuple[str, ...] = ()
    configured_standard_ids: tuple[ConfiguredStandardIdV1, ...] = ()

    @model_validator(mode="after")
    def _kind_contract(self) -> TrustedReadmeDraftSegmentV1:
        if self.kind == "preserve_exact":
            if self.markdown:
                raise ValueError("preserve_exact segment cannot contain authored Markdown")
            if len(self.inherited_fact_ids) != 1 or self.configured_standard_ids:
                raise ValueError(
                    "preserve_exact segment requires exactly one inherited fact and no standard"
                )
        elif not self.markdown.strip():
            raise ValueError("authored segment must contain Markdown")
        if not self.inherited_fact_ids and not self.configured_standard_ids:
            raise ValueError("every draft segment requires inherited or configured provenance")
        return self


class TrustedReadmeSectionToolDraftV1(_StrictFrozenModel):
    """One forced-tool result before deterministic batch binding."""

    editorial_summary: str = Field(min_length=1)
    complete: Literal[True]
    source_inventory: tuple[TrustedSourceInventoryDecisionV1, ...] = Field(min_length=1)
    segments: tuple[TrustedReadmeDraftSegmentV1, ...] = Field(min_length=1)


class TrustedReadmeSectionDraftV1(_StrictFrozenModel):
    """Validated output of one context-bounded LLM authoring call."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    batch_id: str = Field(pattern=r"^batch-[0-9]{4}$")
    editorial_summary: str = Field(min_length=1)
    source_inventory: tuple[TrustedSourceInventoryDecisionV1, ...] = Field(min_length=1)
    segments: tuple[TrustedReadmeDraftSegmentV1, ...] = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tool_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model: str = Field(min_length=1)
    attempt_count: int = Field(ge=1, le=3)

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class TrustedReadmeTransformPlanV1(_StrictFrozenModel):
    """Complete source-bound plan produced by all bounded authoring calls."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    org_repo: OrgRepoRef
    source_revision: str = Field(min_length=7)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fact_graph_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    envelope: TrustedCompositionEnvelopeV1
    section_drafts: tuple[TrustedReadmeSectionDraftV1, ...] = Field(min_length=1)
    inherited_fact_ids: tuple[str, ...] = Field(min_length=1)
    configured_standard_ids: tuple[ConfiguredStandardIdV1, ...] = ()
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_accountability_complete: Literal[True] = True

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class TrustedReadmeSectionRepairRequestV1(_StrictFrozenModel):
    """Hash-bound request to replace one rejected section without reopening others."""

    schema_version: Literal[1] = 1
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    org_repo: OrgRepoRef
    source_revision: str = Field(min_length=7)
    rejected_batch_id: str = Field(pattern=r"^batch-[0-9]{4}$")
    rejected_draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    finding_ids: tuple[str, ...] = Field(min_length=1)
    repair_instructions: tuple[str, ...] = Field(min_length=1)
    accepted_section_sha256s: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _identifiers_are_unique(self) -> TrustedReadmeSectionRepairRequestV1:
        if len(self.finding_ids) != len(set(self.finding_ids)):
            raise ValueError("trusted repair finding IDs must be unique")
        if len(self.accepted_section_sha256s) != len(set(self.accepted_section_sha256s)):
            raise ValueError("accepted trusted section hashes must be unique")
        if any(
            not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in self.accepted_section_sha256s
        ):
            raise ValueError("accepted trusted section hashes must be SHA-256 values")
        return self


class TrustedReadmeCompositionOutputV1(_StrictFrozenModel):
    """Capability output containing the plan, candidate, patch, and call count."""

    org_repo: OrgRepoRef
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    plan: TrustedReadmeTransformPlanV1
    plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_markdown: str = Field(min_length=1)
    candidate_patch: str
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    llm_call_count: int = Field(ge=1)

    @model_validator(mode="after")
    def _hashes_match(self) -> TrustedReadmeCompositionOutputV1:
        if self.plan.org_repo != self.org_repo:
            raise ValueError("trusted composition plan belongs to another repository")
        if self.plan.canonical_hash() != self.plan_hash:
            raise ValueError("trusted composition plan checksum does not match")
        candidate_hash = hashlib.sha256(self.candidate_markdown.encode("utf-8")).hexdigest()
        if candidate_hash != self.candidate_sha256 or candidate_hash != self.plan.candidate_sha256:
            raise ValueError("trusted composition candidate checksum does not match")
        return self


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
