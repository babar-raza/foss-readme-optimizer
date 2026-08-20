"""Typed contracts for one bounded section-cluster authoring call.

A `SectionAuthoringPacketV1` is the exact, minimal request an authoring call is allowed to see:
2-4 accepted facts, zero or more `do_not_claim` facts (context only -- never citable, see
`llm/section_authoring_prompts.py::build_section_cluster_authoring_tool_schema`), protected
literals, bounded SEO vocabulary, and current source text when preservation applies. It never
carries the complete claim corpus or a full `ProductFactsV2` dump.

`SectionAuthoringFactV1` is a typed validation of the SAME canonical, compact projection every
other authoring/reviewing caller already uses -- `readme/agentic_composition_inputs.py::
composition_fact_payloads()` -- not a second parallel fact schema. A fact's structured `value`
(acquisition coordinates, API visibility/reachability/implementation state, minimal-example
metadata, ...) survives here exactly as that shared projection produces it; this module never
flattens it through `fact_strings()[0]` the way an earlier version of this packet did.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.llm.schema import Usage
from readme_agent.llm.section_authoring_prompts import SectionAuthoringTaskFamily

MAX_ACCEPTED_FACTS = 4


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactEvidenceAnchorV1(_StrictModel):
    source_path: str
    line_number: int


class FactCorroborationV1(_StrictModel):
    """Distinct from `verification_state`: how many independent evidence anchors actually
    back this fact and whether any competing source still disagrees -- reused unchanged from
    `agentic_composition_inputs.py::_fact_corroboration`."""

    evidence_assessment_count: int = Field(ge=0)
    accepted_evidence_anchors: tuple[FactEvidenceAnchorV1, ...] = ()
    has_unresolved_conflict: bool
    resolved_conflict_count: int = Field(ge=0)


class FactSourceRefV1(_StrictModel):
    source_type: str
    location: str
    source_revision: str | None = None


class SectionAuthoringFactV1(_StrictModel):
    fact_id: str = Field(min_length=1)
    field: str = Field(min_length=1)
    value: Any = None
    verification_state: str = Field(min_length=1)
    corroboration: FactCorroborationV1
    polarity: Literal["positive_implementation", "explicit_constraint"]
    protected_literals: tuple[str, ...] = ()
    source: FactSourceRefV1
    supporting_fact_ids: tuple[str, ...] = ()


class SectionAuthoringPacketV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str = Field(min_length=3)
    source_revision: str = Field(min_length=1)
    target_section_id: str = Field(min_length=1)
    task_family: SectionAuthoringTaskFamily
    section_objective: str = Field(min_length=1)
    accepted_facts: tuple[SectionAuthoringFactV1, ...]
    do_not_claim: tuple[SectionAuthoringFactV1, ...] = ()
    protected_literal_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    seo_vocabulary: tuple[str, ...] = ()
    current_source_text: str | None = None

    @model_validator(mode="after")
    def _bounded_and_disjoint(self) -> SectionAuthoringPacketV1:
        if not 1 <= len(self.accepted_facts) <= MAX_ACCEPTED_FACTS:
            raise ValueError(
                f"section authoring packet must carry 1-{MAX_ACCEPTED_FACTS} accepted facts, "
                f"got {len(self.accepted_facts)}"
            )
        accepted_ids = {fact.fact_id for fact in self.accepted_facts}
        if len(accepted_ids) != len(self.accepted_facts):
            raise ValueError("section authoring packet has duplicate accepted fact_ids")
        do_not_claim_ids = {fact.fact_id for fact in self.do_not_claim}
        overlap = accepted_ids & do_not_claim_ids
        if overlap:
            raise ValueError(f"fact_ids appear in both accepted_facts and do_not_claim: {overlap}")
        return self

    @property
    def allowed_fact_ids(self) -> list[str]:
        """Only accepted facts are ever citable -- see the module docstring."""

        return [fact.fact_id for fact in self.accepted_facts]

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class SectionClusterUnitV1(_StrictModel):
    heading: str = Field(min_length=1)
    text: str = Field(min_length=1)
    fact_ids: tuple[str, ...] = Field(min_length=1)


class OmittedFactV1(_StrictModel):
    fact_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class SectionClusterAuthoringResultV1(_StrictModel):
    units: tuple[SectionClusterUnitV1, ...] = Field(min_length=1)
    omitted: tuple[OmittedFactV1, ...] = ()


class SectionAuthoringReceiptV1(_StrictModel):
    """Sanitized call evidence: identity/provenance hashes and observable telemetry only --
    no secrets, no raw prompt/response content, no model reasoning. Physical HTTP-level
    transport retries (bounded to `section_author_client.TRANSPORT_MAX_ATTEMPTS`, at most 2 per
    logical call) are recorded separately in the LLM call ledger (`llm/call_ledger.py`);
    `logical_call_count` here counts this specialist's own bounded semantic-correction attempts
    (1 normal + at most 1 retry). Worst-case physical provider calls for one cluster is therefore
    `logical_call_count(<=2) * TRANSPORT_MAX_ATTEMPTS(<=2)` = at most 4 -- see
    `section_cluster_authoring.py`'s module docstring for the full breakdown."""

    actor_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_request_id: str | None = None
    provider_model: str | None = None
    semantic_retry_used: bool
    logical_call_count: int = Field(ge=1, le=2)
    token_usage: list[Usage] = Field(default_factory=list)
    latency_ms: list[float] = Field(default_factory=list)


class SectionAuthoringOutcomeV1(_StrictModel):
    """One section cluster's final, accepted authoring result and its evidence."""

    target_section_id: str = Field(min_length=1)
    packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: SectionClusterAuthoringResultV1
    receipt: SectionAuthoringReceiptV1
    reused_from_cache: bool = False


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
