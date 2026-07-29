"""Define the typed contracts for agentic README composition."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.readme.assessment import AssessmentDisposition

MAX_AUTHORING_ATTEMPTS = 3
OVERVIEW_FIELD_PREFERENCE = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.limitations",
    "product.compatibility",
    "product.identity",
    "relationship.commercial_foss",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgenticSectionDecisionV1(_StrictModel):
    section_id: str
    disposition: AssessmentDisposition
    priority: int = Field(ge=0, le=100)
    supporting_fact_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)


class AgenticOverviewSentenceV1(_StrictModel):
    text: str = Field(min_length=1)
    supporting_fact_ids: list[str] = Field(min_length=1)


class AgenticCompositionDraftV1(_StrictModel):
    repository_summary: str = Field(min_length=1)
    section_decisions: list[AgenticSectionDecisionV1] = Field(min_length=1)
    overview_sentences: list[AgenticOverviewSentenceV1] = Field(min_length=1)


class AgenticCompositionToolDraftV1(_StrictModel):
    repository_summary: str = Field(min_length=1)
    section_decisions: list[AgenticSectionDecisionV1] = Field(min_length=1)
    overview_fact_ids: list[str] = Field(min_length=1)


class ReadmeAgenticCompositionPlanV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str
    source_sha256: str
    facts_hash: str
    assessment_hash: str
    prompt_sha256: str
    tool_schema_sha256: str
    input_sha256: str
    model: str
    attempt_count: int = Field(ge=1, le=MAX_AUTHORING_ATTEMPTS)
    repository_summary: str
    section_decisions: list[AgenticSectionDecisionV1]
    overview_sentences: list[AgenticOverviewSentenceV1]

    def canonical_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ReadmeCompositionRepairFindingV1(_StrictModel):
    """One reviewer finding that the next authoring pass must address."""

    finding_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    section: str = Field(min_length=1)
    criterion: str = Field(min_length=1)
    quoted_candidate_span: str
    required_repair: str = Field(min_length=1)


class ReadmeCompositionRepairRequestV1(_StrictModel):
    """Bounded instructions from the independent reviewer to the authoring pass."""

    source_candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    failed_criteria: list[str] = Field(min_length=1)
    sections_affected: list[str] = Field(min_length=1)
    required_repair: str = Field(min_length=1)
    preserve: list[str] = Field(default_factory=list)
    findings: list[ReadmeCompositionRepairFindingV1] = Field(min_length=1)
