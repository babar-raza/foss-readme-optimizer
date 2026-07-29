"""Typed README-inherited evidence contracts for the temporary trusted lane."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.capabilities.schema import OrgRepoRef
from readme_agent.state.assurance import ContentAssuranceV1

TrustedReadmeProvenanceV1 = Literal["README_INHERITED", "CONFIGURED_STANDARD"]
ReadmeMaterialKindV1 = Literal[
    "heading",
    "paragraph",
    "unordered_list",
    "ordered_list",
    "blockquote",
    "code",
    "html",
    "thematic_break",
    "table",
]
InstructionRiskV1 = Literal["prompt_injection", "hidden_content"]
ConfiguredStandardIdV1 = Literal[
    "readme.header",
    "readme.badges",
    "readme.navigation",
    "readme.at_a_glance_mermaid",
    "readme.enterprise_edition_terminology",
    "readme.contextual_links",
]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadmeSourceSpanV1(_StrictFrozenModel):
    """Exact UTF-8 source bytes supporting one inherited content unit."""

    source_path: str = Field(min_length=1)
    source_revision: str = Field(min_length=7)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_start: int = Field(ge=0)
    byte_end: int = Field(gt=0)
    start_line: int = Field(ge=1)
    end_line_exclusive: int = Field(ge=2)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _ordered_span(self) -> ReadmeSourceSpanV1:
        if self.byte_end <= self.byte_start:
            raise ValueError("README source span must contain at least one byte")
        if self.end_line_exclusive <= self.start_line:
            raise ValueError("README source span line range must be ordered")
        return self


class InheritedReadmeFactV1(_StrictFrozenModel):
    """One material README unit retained as content, never as a verified claim."""

    fact_id: str = Field(pattern=r"^readme\.inherited:[0-9a-f]{24}$")
    field: Literal["readme.material"] = "readme.material"
    value: str = Field(min_length=1)
    material_kind: ReadmeMaterialKindV1
    heading_path: tuple[str, ...] = ()
    provenance: Literal["README_INHERITED"] = "README_INHERITED"
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    source_span: ReadmeSourceSpanV1
    instruction_risks: tuple[InstructionRiskV1, ...] = ()

    @model_validator(mode="after")
    def _value_matches_exact_span(self) -> InheritedReadmeFactV1:
        encoded = self.value.encode("utf-8")
        if len(encoded) != self.source_span.byte_end - self.source_span.byte_start:
            raise ValueError("inherited fact value does not fill its declared UTF-8 byte span")
        if hashlib.sha256(encoded).hexdigest() != self.source_span.content_sha256:
            raise ValueError("inherited fact value does not match its content checksum")
        return self


class ConfiguredStandardAdditionV1(_StrictFrozenModel):
    """One presentation-contract addition kept separate from inherited claims."""

    standard_id: ConfiguredStandardIdV1
    provenance: Literal["CONFIGURED_STANDARD"] = "CONFIGURED_STANDARD"
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    authority_requirement_ids: tuple[str, ...] = Field(min_length=1)
    configuration_source: str = Field(min_length=1)
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("authority_requirement_ids")
    @classmethod
    def _unique_authorities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("configured-standard authority IDs must be unique")
        return value


class TrustedReadmeFactGraphV1(_StrictFrozenModel):
    """Complete source-bound material inventory for one immutable README."""

    schema_version: Literal[1] = 1
    content_assurance: ContentAssuranceV1 = "trusted_inherited"
    org_repo: OrgRepoRef
    source_revision: str = Field(min_length=7)
    readme_path: str = Field(min_length=1)
    readme_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_byte_count: int = Field(gt=0)
    covered_material_byte_count: int = Field(gt=0)
    non_whitespace_source_coverage_complete: Literal[True] = True
    inherited_facts: tuple[InheritedReadmeFactV1, ...] = Field(min_length=1)
    configured_standards: tuple[ConfiguredStandardAdditionV1, ...] = ()

    @model_validator(mode="after")
    def _complete_and_disjoint(self) -> TrustedReadmeFactGraphV1:
        if self.content_assurance != "trusted_inherited":
            raise ValueError("trusted README fact graphs require trusted_inherited assurance")
        if self.covered_material_byte_count > self.source_byte_count:
            raise ValueError("covered README bytes cannot exceed total source bytes")
        fact_ids = [fact.fact_id for fact in self.inherited_facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("trusted README fact IDs must be unique")
        prior_end = -1
        for fact in self.inherited_facts:
            span = fact.source_span
            if span.source_revision != self.source_revision:
                raise ValueError("inherited fact revision differs from the graph revision")
            if span.source_path != self.readme_path:
                raise ValueError("inherited fact path differs from the graph README path")
            if span.source_sha256 != self.readme_sha256:
                raise ValueError("inherited fact source checksum differs from the graph checksum")
            if span.byte_start < prior_end:
                raise ValueError("trusted README fact spans must be ordered and non-overlapping")
            prior_end = span.byte_end
        standard_ids = [addition.standard_id for addition in self.configured_standards]
        if len(standard_ids) != len(set(standard_ids)):
            raise ValueError("configured standard additions must be unique")
        return self

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TrustedReadmeFactsOutputV1(_StrictFrozenModel):
    """Capability output wrapper with a structural output contract."""

    org_repo: OrgRepoRef
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    fact_graph: TrustedReadmeFactGraphV1
    fact_graph_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _graph_identity_matches(self) -> TrustedReadmeFactsOutputV1:
        if self.fact_graph.org_repo != self.org_repo:
            raise ValueError("trusted fact graph belongs to a different repository")
        if self.fact_graph.canonical_hash() != self.fact_graph_hash:
            raise ValueError("trusted fact graph checksum does not match")
        return self
