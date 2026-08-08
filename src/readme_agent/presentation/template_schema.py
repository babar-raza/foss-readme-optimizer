"""Define the assurance-neutral repository-presentation template contracts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TemplateProfile = Literal["compact", "standard", "extended"]
TemplateSlot = Literal[
    "navigation",
    "at_a_glance",
    "key_capabilities",
    "installation",
    "quick_start",
    "additional_examples",
    "api_reference",
    "documentation_resources",
    "scope_and_limitations",
    "development_and_testing",
    "contributing",
    "security",
    "third_party_notices",
    "license",
]
TemplateContentSource = Literal[
    "repository_fact",
    "repository_fact_and_configured_standard",
    "configured_standard",
    "readme_inherited",
    "omitted",
]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_CONTRACT_PATH = _PROJECT_ROOT / "templates" / "readme" / "repository-presentation-v1.json"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TemplateProfileV1(_StrictModel):
    maximum_source_lines: int | None = Field(default=None, ge=1)
    collapse_slots: list[TemplateSlot] = Field(default_factory=list)


class TemplateInvariantsV1(_StrictModel):
    badge_rows: Literal[1] = 1
    minimum_badges: int = Field(ge=1)
    mermaid_visual_grammar: Literal["corporate-capability-landscape"]
    mermaid_capability_layout: Literal["adaptive_vertical_columns"]
    mermaid_capability_column_threshold: Literal[5]
    mermaid_capability_layout_constraint: Literal["balanced_consecutive_invisible_chains"]
    mermaid_topology: Literal["inputs-product-capabilities-outputs"]
    minimum_mermaid_inputs: int = Field(ge=1)
    minimum_mermaid_capabilities: int = Field(ge=1)
    minimum_mermaid_outputs: int = Field(ge=0)
    target_mermaid_inputs: int = Field(ge=1)
    target_mermaid_capabilities: int = Field(ge=1)
    target_mermaid_outputs: int = Field(ge=1)
    comments: Literal["forbidden"]
    emoji: Literal["forbidden"]
    copyright: Literal["omitted_by_default"]
    commercial_term: Literal["Enterprise Edition"]
    capability_titles: Literal["action_search_intent"]
    technical_abbreviation_case: Literal["canonical_uppercase"]
    heading_case: Literal["title_case"]
    semantic_section_repetition: Literal["forbidden"]
    source_detail_routing: Literal["canonical_section_only"]
    enterprise_link_anchor: Literal["natural_full_featured_enterprise_edition"]
    public_internal_assurance: Literal["forbidden"]
    additional_examples_intro: Literal["workflow_preview"]
    repository_link_style: Literal["normal_markdown_text"]
    primary_example_max_nonblank_lines: dict[str, int]

    @model_validator(mode="after")
    def _diagram_targets_exceed_hard_minimums(self) -> TemplateInvariantsV1:
        pairs = (
            (self.minimum_mermaid_inputs, self.target_mermaid_inputs),
            (self.minimum_mermaid_capabilities, self.target_mermaid_capabilities),
            (self.minimum_mermaid_outputs, self.target_mermaid_outputs),
        )
        if any(target < minimum for minimum, target in pairs):
            raise ValueError("Mermaid detail targets cannot be below hard evidence minimums")
        return self

    @field_validator("primary_example_max_nonblank_lines")
    @classmethod
    def _complete_example_limits(cls, value: dict[str, int]) -> dict[str, int]:
        required = {"default", "cpp", "dotnet", "go", "java", "python", "rust", "typescript"}
        if set(value) != required or any(limit < 1 for limit in value.values()):
            raise ValueError(
                "primary example limits must define positive bounds for every supported language"
            )
        return value


class RepositoryPresentationTemplateV1(_StrictModel):
    schema_version: Literal[1] = 1
    template_id: Literal["repository-presentation"]
    template_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    accepted_reference_sha256: str
    section_order: list[TemplateSlot]
    headings: dict[TemplateSlot, str]
    required_slots: list[TemplateSlot]
    profiles: dict[TemplateProfile, TemplateProfileV1]
    invariants: TemplateInvariantsV1

    @field_validator("accepted_reference_sha256")
    @classmethod
    def _valid_reference_hash(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("accepted reference hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _complete_contract(self) -> RepositoryPresentationTemplateV1:
        if len(self.section_order) != len(set(self.section_order)):
            raise ValueError("template section_order contains duplicates")
        if self.section_order[0] != "navigation":
            raise ValueError("template navigation must be the first H2 slot")
        if set(self.headings) != set(self.section_order):
            raise ValueError("template headings must cover section_order exactly")
        if not set(self.required_slots).issubset(self.section_order):
            raise ValueError("required template slots must occur in section_order")
        if set(self.profiles) != {"compact", "standard", "extended"}:
            raise ValueError("template must define compact, standard, and extended profiles")
        limits = [
            self.profiles["compact"].maximum_source_lines,
            self.profiles["standard"].maximum_source_lines,
            self.profiles["extended"].maximum_source_lines,
        ]
        if limits[0] is None or limits[1] is None or limits[2] is not None:
            raise ValueError("template profile line ceilings must end with unbounded extended")
        if limits[0] >= limits[1]:
            raise ValueError("compact source-line ceiling must precede standard")
        return self


class BoundTemplateContentV1(_StrictModel):
    markdown: str = ""
    source_kind: TemplateContentSource
    fact_ids: list[str] = Field(default_factory=list)
    standard_ids: list[str] = Field(default_factory=list)
    source_sha256: str | None = None
    omission_reason: str | None = None

    @field_validator("source_sha256")
    @classmethod
    def _valid_source_hash(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256.fullmatch(value):
            raise ValueError("bound content source_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _provenance_matches_source(self) -> BoundTemplateContentV1:
        if self.source_kind == "repository_fact" and not self.fact_ids:
            raise ValueError("repository-fact template content requires fact_ids")
        if self.source_kind == "repository_fact_and_configured_standard" and (
            not self.fact_ids or not self.standard_ids
        ):
            raise ValueError("mixed template content requires fact_ids and standard_ids")
        if self.source_kind == "configured_standard" and not self.standard_ids:
            raise ValueError("configured-standard template content requires standard_ids")
        if self.source_kind == "readme_inherited" and self.source_sha256 is None:
            raise ValueError("README-inherited template content requires source_sha256")
        if self.source_kind == "omitted":
            if self.markdown.strip() or not self.omission_reason:
                raise ValueError("omitted template content requires only an omission_reason")
        elif not self.markdown.strip():
            raise ValueError("included template content cannot be blank")
        return self


class PresentationTemplateInputV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str = Field(min_length=1)
    source_line_count: int = Field(ge=1)
    profile: TemplateProfile | None = None
    title: BoundTemplateContentV1
    badges: BoundTemplateContentV1
    summary: BoundTemplateContentV1
    sections: dict[TemplateSlot, BoundTemplateContentV1]

    @field_validator("org_repo")
    @classmethod
    def _valid_repo(cls, value: str) -> str:
        if len(value.split("/")) != 2:
            raise ValueError("org_repo must be org/repo")
        return value


class FactFieldTemplateContentV1(_StrictModel):
    disposition: Literal["include", "omit"]
    markdown: str = ""
    fact_fields: list[str] = Field(default_factory=list)
    standard_ids: list[str] = Field(default_factory=list)
    omission_reason: str | None = None

    @model_validator(mode="after")
    def _complete_disposition(self) -> FactFieldTemplateContentV1:
        if self.disposition == "include":
            if not self.markdown.strip() or not (self.fact_fields or self.standard_ids):
                raise ValueError("included fact-field content requires markdown and provenance")
            if self.omission_reason is not None:
                raise ValueError("included fact-field content cannot carry an omission_reason")
        elif (
            self.markdown.strip()
            or self.fact_fields
            or self.standard_ids
            or not self.omission_reason
        ):
            raise ValueError("omitted fact-field content requires only an omission_reason")
        return self


class ProductFactsTemplateDraftV1(_StrictModel):
    schema_version: Literal[1] = 1
    source_revision: str = Field(min_length=1)
    source_line_count: int = Field(ge=1)
    profile: TemplateProfile | None = None
    title: FactFieldTemplateContentV1
    badges: FactFieldTemplateContentV1
    summary: FactFieldTemplateContentV1
    sections: dict[TemplateSlot, FactFieldTemplateContentV1]

    @model_validator(mode="after")
    def _opening_is_included(self) -> ProductFactsTemplateDraftV1:
        for name, content in (
            ("title", self.title),
            ("badges", self.badges),
            ("summary", self.summary),
        ):
            if content.disposition != "include":
                raise ValueError(f"verified template {name} cannot be omitted")
        return self


class PresentationTemplateDependenciesV1(_StrictModel):
    template_version: str
    template_sha256: str
    accepted_reference_sha256: str
    source_revision: str = Field(min_length=1)
    fact_sha256: str
    prompt_sha256: str
    policy_sha256: str
    validator_version: str = Field(min_length=1)
    reviewer_standard_sha256: str
    protected_content_sha256: str

    @field_validator(
        "accepted_reference_sha256",
        "template_sha256",
        "fact_sha256",
        "prompt_sha256",
        "policy_sha256",
        "reviewer_standard_sha256",
        "protected_content_sha256",
    )
    @classmethod
    def _valid_hash(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("template dependency hashes must be lowercase SHA-256")
        return value

    def cache_key(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def load_repository_presentation_template() -> RepositoryPresentationTemplateV1:
    """Load the versioned repository-presentation contract from its governed data file."""

    return RepositoryPresentationTemplateV1.model_validate_json(
        TEMPLATE_CONTRACT_PATH.read_text(encoding="utf-8")
    )


def repository_presentation_template_hash() -> str:
    """Return the exact governed template-file hash used for cache invalidation."""

    return hashlib.sha256(TEMPLATE_CONTRACT_PATH.read_bytes()).hexdigest()
