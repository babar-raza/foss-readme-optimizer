"""Typed context bindings and decisions for natural README links."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.links.allocation import ResolvedLinkBudgetV1
from readme_agent.links.catalog_models import AsposeLinkSurface, AsposeParentDomain
from readme_agent.links.occurrences import AsposeLinkOccurrenceCountsV1

ContextualLinkOmissionReason = Literal[
    "none",
    "no_accepted_example",
    "no_example_section",
    "no_strong_context_match",
    "target_already_present",
    "budget_exhausted",
]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContextualLinkBindingV1(_StrictFrozenModel):
    """One verified target bound to exact adjacent candidate content."""

    schema_version: Literal[1] = 1
    binding_id: str = Field(pattern=r"^[a-z][a-z0-9._:-]*$")
    context_kind: Literal["code_example", "claim", "command", "format_workflow", "relationship"]
    section_heading: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    target_record_id: str = Field(min_length=1)
    target_url: str = Field(min_length=1)
    target_title: str = Field(min_length=1)
    parent_domain: AsposeParentDomain
    surface: AsposeLinkSurface
    support_rationale: str = Field(min_length=1)
    placement: Literal["after_verified_example", "inline_supporting_prose", "end_resources"]
    accepted_fact_ids: list[str] = Field(min_length=1)
    matched_subject_terms: list[str] = Field(min_length=1)


class ContextualLinkPlanV1(_StrictFrozenModel):
    """Reproducible configured-or-automatic selection result."""

    schema_version: Literal[1] = 1
    family: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    enterprise_product_name: str = Field(min_length=1)
    aspose_org_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    aspose_com_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    budget: ResolvedLinkBudgetV1
    pre_link_occurrences: AsposeLinkOccurrenceCountsV1
    pre_link_url_counts: dict[str, int]
    considered_record_ids: list[str]
    bindings: list[ContextualLinkBindingV1]
    omission_reason: ContextualLinkOmissionReason
