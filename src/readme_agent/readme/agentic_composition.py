"""Generate and validate a fact-bound agentic README composition strategy."""

from __future__ import annotations

import hashlib
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.analysis_client import AnalysisResult, LiveAnalysisClient
from readme_agent.llm.generation_prompts import build_readme_composition_messages
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.readme.assessment import AssessmentDisposition, ReadmeAssessmentV1

_JOB = "plan_readme_composition"
_ACCEPTED_STATES = {"verified", "policy_approved"}
_MAX_AUTHORING_ATTEMPTS = 3


class _AnalysisClient(Protocol):
    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


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


class ReadmeAgenticCompositionPlanV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str
    source_sha256: str
    facts_hash: str
    assessment_hash: str
    prompt_sha256: str
    input_sha256: str
    model: str
    attempt_count: int = Field(ge=1, le=_MAX_AUTHORING_ATTEMPTS)
    repository_summary: str
    section_decisions: list[AgenticSectionDecisionV1]
    overview_sentences: list[AgenticOverviewSentenceV1]

    def canonical_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _accepted_fact_ids(facts: ProductFactsV2) -> set[str]:
    return {
        fact.fact_id
        for fact in facts.facts
        if facts.selected_fact_ids.get(fact.field) == fact.fact_id
        and fact.verification_state in _ACCEPTED_STATES
        and not fact.has_unresolved_conflict
    }


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings(item)]
    return []


def _validate_draft(
    draft: AgenticCompositionDraftV1,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
) -> None:
    section_ids = {section.section_id for section in assessment.sections}
    decision_ids = [decision.section_id for decision in draft.section_decisions]
    if len(decision_ids) != len(set(decision_ids)):
        raise LLMError("composition returned duplicate section decisions")
    accepted_ids = _accepted_fact_ids(facts)
    unknown_sections = {
        decision.section_id
        for decision in draft.section_decisions
        if decision.section_id not in section_ids
    }
    if unknown_sections:
        raise LLMError(f"composition cited unknown section IDs: {sorted(unknown_sections)}")
    if missing_sections := section_ids - set(decision_ids):
        raise LLMError(
            f"composition omitted source-bound section decisions: {sorted(missing_sections)}"
        )
    cited_ids = {
        fact_id for decision in draft.section_decisions for fact_id in decision.supporting_fact_ids
    } | {
        fact_id for sentence in draft.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    if unknown_facts := cited_ids - accepted_ids:
        raise LLMError(f"composition cited unaccepted fact IDs: {sorted(unknown_facts)}")
    for sentence in draft.overview_sentences:
        grounded_phrases = [
            phrase.strip()
            for fact_id in sentence.supporting_fact_ids
            for phrase in _strings(facts.fact_by_id(fact_id).value)
            if len(phrase.strip()) >= 4
        ]
        normalized_sentence = sentence.text.strip().rstrip(".").casefold()
        if not any(
            normalized_sentence == phrase.rstrip(".").casefold() for phrase in grounded_phrases
        ):
            raise LLMError(
                "composition overview sentence is not an exact literal cited fact phrase"
            )
    required_overview_ids = {
        facts.selected_fact_ids[field]
        for field in ("product.audience", "product.problems_solved")
        if facts.selected_fact_ids.get(field) in accepted_ids
    }
    overview_ids = {
        fact_id for sentence in draft.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    if missing_overview_ids := required_overview_ids - overview_ids:
        raise LLMError(
            "composition omitted required audience/problem facts from overview: "
            f"{sorted(missing_overview_ids)}"
        )


def validate_readme_composition_plan(
    payload: dict,
    *,
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
) -> ReadmeAgenticCompositionPlanV1:
    """Rebind a serialized agentic plan before deterministic rendering."""

    try:
        plan = ReadmeAgenticCompositionPlanV1.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(f"README composition plan failed schema validation: {exc}") from exc
    expected_bindings = {
        "org_repo": org_repo,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "facts_hash": facts.canonical_hash(),
        "assessment_hash": assessment.canonical_hash(),
        "prompt_sha256": prompt_hash(_JOB),
    }
    mismatches = [
        field for field, expected in expected_bindings.items() if getattr(plan, field) != expected
    ]
    if mismatches:
        raise LLMError(f"README composition plan binding mismatch: {sorted(mismatches)}")
    _validate_draft(
        AgenticCompositionDraftV1(
            repository_summary=plan.repository_summary,
            section_decisions=plan.section_decisions,
            overview_sentences=plan.overview_sentences,
        ),
        assessment,
        facts,
    )
    return plan


def plan_readme_composition(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
    *,
    client: _AnalysisClient | None = None,
    max_attempts: int = _MAX_AUTHORING_ATTEMPTS,
) -> ReadmeAgenticCompositionPlanV1:
    """Call the authoring model once and fail closed on unbound editorial output."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    accepted_ids = _accepted_fact_ids(facts)
    facts_payload = [
        fact.model_dump(mode="json") for fact in facts.facts if fact.fact_id in accepted_ids
    ]
    assessment_payload = assessment.model_dump(mode="json")
    resolved_client = client or LiveAnalysisClient(
        base_url=env.llm_base_url(),
        api_key=env.llm_api_key(),
        model=env.llm_model_for_job(_JOB),
        timeout=env.llm_timeout_seconds(),
        max_tokens=6000,
    )
    repair_hints_section = ""
    last_error: LLMError | None = None
    for attempt in range(1, max_attempts + 1):
        input_payload = {
            "org_repo": org_repo,
            "source_text": source_text,
            "accepted_facts": facts_payload,
            "assessment": assessment_payload,
            "repair_hints_section": repair_hints_section,
        }
        input_json = json.dumps(input_payload, sort_keys=True, separators=(",", ":"))
        messages = build_readme_composition_messages(
            org_repo=org_repo,
            source_text=source_text,
            accepted_facts_json=json.dumps(facts_payload, sort_keys=True),
            assessment_json=json.dumps(assessment_payload, sort_keys=True),
            repair_hints_section=repair_hints_section,
        )
        try:
            result = resolved_client.analyze(messages)
            draft = AgenticCompositionDraftV1.model_validate(result.parsed)
            _validate_draft(draft, assessment, facts)
        except (LLMError, ValidationError) as exc:
            last_error = (
                exc
                if isinstance(exc, LLMError)
                else LLMError(f"README composition response failed schema validation: {exc}")
            )
            if attempt == max_attempts:
                raise last_error from exc
            repair_hints_section = _repair_hints(
                last_error,
                assessment,
                facts,
                attempt=attempt + 1,
            )
            continue
        return ReadmeAgenticCompositionPlanV1(
            org_repo=org_repo,
            source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            facts_hash=facts.canonical_hash(),
            assessment_hash=assessment.canonical_hash(),
            prompt_sha256=prompt_hash(_JOB),
            input_sha256=hashlib.sha256(input_json.encode("utf-8")).hexdigest(),
            model=result.meta.model or env.llm_model_for_job(_JOB),
            attempt_count=attempt,
            **draft.model_dump(),
        )
    assert last_error is not None
    raise last_error


def _repair_hints(
    error: LLMError,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
    *,
    attempt: int,
) -> str:
    exact_overview_phrases = [
        phrase.strip()
        for field in ("product.audience", "product.problems_solved")
        if (fact_id := facts.selected_fact_ids.get(field)) in _accepted_fact_ids(facts)
        for phrase in _strings(facts.fact_by_id(fact_id).value)
        if phrase.strip()
    ]
    return (
        f"REPAIR ATTEMPT {attempt}. The previous JSON was rejected: {error}\n"
        "Return a complete raw JSON object with no markdown fence. Include exactly one "
        "section_decision for each of these IDs:\n"
        + json.dumps([section.section_id for section in assessment.sections])
        + "\nFor overview_sentences, copy these strings exactly (optional terminal punctuation "
        "only) and cite their matching fact IDs:\n"
        + json.dumps(exact_overview_phrases, ensure_ascii=False)
    )
