"""Generate and validate a fact-bound agentic README composition strategy."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.generation_prompts import (
    build_readme_composition_messages,
    build_readme_composition_tool_schema,
)
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.assessment import AssessmentDisposition, ReadmeAssessmentV1

_JOB = "plan_readme_composition"
_ACCEPTED_STATES = {"verified", "policy_approved"}
_MAX_AUTHORING_ATTEMPTS = 3
_OVERVIEW_FIELD_PREFERENCE = (
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


class _AgenticCompositionToolDraftV1(_StrictModel):
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
    attempt_count: int = Field(ge=1, le=_MAX_AUTHORING_ATTEMPTS)
    repository_summary: str
    section_decisions: list[AgenticSectionDecisionV1]
    overview_sentences: list[AgenticOverviewSentenceV1]

    def canonical_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ReadmeCompositionRepairRequestV1(_StrictModel):
    """Bounded instructions from the independent reviewer to the authoring pass."""

    failed_criteria: list[str] = Field(min_length=1)
    sections_affected: list[str] = Field(min_length=1)
    required_repair: str = Field(min_length=1)
    preserve: list[str] = Field(default_factory=list)


def _accepted_fact_ids(facts: ProductFactsV2) -> set[str]:
    return {
        fact.fact_id
        for fact in facts.facts
        if facts.selected_fact_ids.get(fact.field) == fact.fact_id
        and fact.verification_state in _ACCEPTED_STATES
        and not fact.has_unresolved_conflict
    }


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _overview_phrase_options(facts: ProductFactsV2) -> list[dict]:
    accepted_ids = _accepted_fact_ids(facts)
    options = []
    for field in _OVERVIEW_FIELD_PREFERENCE:
        view = visitor_fact_render_view(facts, field)
        if view is None or view.fact_id not in accepted_ids:
            continue
        phrases = [phrase.strip() for phrase in view.phrases if len(phrase.strip()) >= 4]
        if phrases:
            options.append({"fact_id": view.fact_id, "phrases": phrases[:8]})
    return options


def _planning_sections(assessment: ReadmeAssessmentV1):
    """Bound agentic output to structural/material sections; deterministic assessment stays full."""

    return [
        section
        for section in assessment.sections
        if section.level <= 2 or section.disposition != "preserve"
    ]


def _required_overview_ids(facts: ProductFactsV2) -> set[str]:
    options = _overview_phrase_options(facts)
    option_ids = {option["fact_id"] for option in options}
    audience_problem = {
        facts.selected_fact_ids[field]
        for field in ("product.audience", "product.problems_solved")
        if facts.selected_fact_ids.get(field) in option_ids
    }
    return audience_problem or {option["fact_id"] for option in options[:2]}


def _overview_words(text: str) -> str:
    """Normalize punctuation so one grounded phrase can subsume another."""

    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _phrases_overlap(left: str, right: str) -> bool:
    left_words = _overview_words(left)
    right_words = _overview_words(right)
    return bool(
        left_words and right_words and (left_words in right_words or right_words in left_words)
    )


def _materialize_tool_draft(
    tool_draft: _AgenticCompositionToolDraftV1,
    overview_phrase_options: list[dict],
    facts: ProductFactsV2,
) -> AgenticCompositionDraftV1:
    """Turn model-selected fact IDs into literal fact text deterministically."""

    phrases_by_fact_id = {
        option["fact_id"]: option["phrases"] for option in overview_phrase_options
    }
    selected_ids = tool_draft.overview_fact_ids
    unknown_ids = set(selected_ids) - set(phrases_by_fact_id)
    if unknown_ids:
        raise LLMError(f"composition selected ineligible overview fact IDs: {sorted(unknown_ids)}")
    if len(selected_ids) != len(set(selected_ids)):
        raise LLMError("composition selected duplicate overview fact IDs")
    required_ids = _required_overview_ids(facts)
    materialized_ids = list(dict.fromkeys([*selected_ids, *sorted(required_ids)]))
    used_phrases: set[str] = set()
    overview_sentences: list[AgenticOverviewSentenceV1] = []
    for fact_id in materialized_ids:
        phrases = phrases_by_fact_id[fact_id]
        text = next(
            (
                phrase
                for phrase in phrases
                if phrase.strip().rstrip(".").casefold() not in used_phrases
            ),
            phrases[0],
        )
        used_phrases.add(text.strip().rstrip(".").casefold())
        overlapping_index = next(
            (
                index
                for index, sentence in enumerate(overview_sentences)
                if _phrases_overlap(sentence.text, text)
            ),
            None,
        )
        if overlapping_index is not None:
            existing = overview_sentences[overlapping_index]
            rendered_text = (
                text
                if len(_overview_words(text)) > len(_overview_words(existing.text))
                else existing.text
            )
            overview_sentences[overlapping_index] = AgenticOverviewSentenceV1(
                text=rendered_text,
                supporting_fact_ids=list(dict.fromkeys([*existing.supporting_fact_ids, fact_id])),
            )
            continue
        overview_sentences.append(
            AgenticOverviewSentenceV1(
                text=text,
                supporting_fact_ids=[fact_id],
            )
        )
    return AgenticCompositionDraftV1(
        repository_summary=tool_draft.repository_summary,
        section_decisions=tool_draft.section_decisions,
        overview_sentences=overview_sentences,
    )


def _validate_draft(
    draft: AgenticCompositionDraftV1,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
) -> None:
    section_ids = {section.section_id for section in _planning_sections(assessment)}
    decision_ids = [decision.section_id for decision in draft.section_decisions]
    if len(decision_ids) != len(set(decision_ids)):
        raise LLMError("composition returned duplicate section decisions")
    if duplicate_fact_lists := [
        decision.section_id
        for decision in draft.section_decisions
        if len(decision.supporting_fact_ids) != len(set(decision.supporting_fact_ids))
    ]:
        raise LLMError(
            "composition returned duplicate supporting fact IDs for sections: "
            f"{sorted(duplicate_fact_lists)}"
        )
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
    dispositions = {
        section.section_id: section.disposition for section in _planning_sections(assessment)
    }
    if mismatched_dispositions := [
        f"{decision.section_id}:{decision.disposition}!={dispositions[decision.section_id]}"
        for decision in draft.section_decisions
        if decision.section_id in dispositions
        and decision.disposition != dispositions[decision.section_id]
    ]:
        raise LLMError(
            "composition changed deterministic source-bound dispositions: "
            f"{sorted(mismatched_dispositions)}"
        )
    cited_ids = {
        fact_id for decision in draft.section_decisions for fact_id in decision.supporting_fact_ids
    } | {
        fact_id for sentence in draft.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    if unknown_facts := cited_ids - accepted_ids:
        raise LLMError(f"composition cited unaccepted fact IDs: {sorted(unknown_facts)}")
    for sentence in draft.overview_sentences:
        views = [
            visitor_fact_render_view(facts, facts.fact_by_id(fact_id).field)
            for fact_id in sentence.supporting_fact_ids
        ]
        grounded_phrases = [
            phrase.strip()
            for view in views
            if view is not None
            for phrase in view.phrases
            if len(phrase.strip()) >= 4
        ]
        normalized_sentence = sentence.text.strip().rstrip(".").casefold()
        if not any(
            normalized_sentence == phrase.rstrip(".").casefold() for phrase in grounded_phrases
        ):
            raise LLMError(
                "composition overview sentence is not an exact literal cited fact phrase"
            )
    for index, sentence in enumerate(draft.overview_sentences):
        if any(
            _phrases_overlap(sentence.text, other.text)
            for other in draft.overview_sentences[index + 1 :]
        ):
            raise LLMError("composition returned semantically duplicate overview sentences")
    required_overview_ids = _required_overview_ids(facts)
    overview_ids = {
        fact_id for sentence in draft.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    if missing_overview_ids := required_overview_ids - overview_ids:
        raise LLMError(
            f"composition omitted required overview facts: {sorted(missing_overview_ids)}"
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
    accepted_ids = _accepted_fact_ids(facts)
    overview_phrase_options = _overview_phrase_options(facts)
    assessment_payload = assessment.model_copy(
        update={"sections": _planning_sections(assessment)}
    ).model_dump(mode="json")
    tool_schema = build_readme_composition_tool_schema(
        section_ids=[section["section_id"] for section in assessment_payload["sections"]],
        accepted_fact_ids=sorted(accepted_ids),
        overview_fact_ids=[option["fact_id"] for option in overview_phrase_options],
    )
    expected_bindings = {
        "org_repo": org_repo,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "facts_hash": facts.canonical_hash(),
        "assessment_hash": assessment.canonical_hash(),
        "prompt_sha256": prompt_hash(_JOB),
        "tool_schema_sha256": _canonical_hash(tool_schema),
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
    client: ForcedToolClient | None = None,
    max_attempts: int = _MAX_AUTHORING_ATTEMPTS,
    review_repair: ReadmeCompositionRepairRequestV1 | dict | None = None,
) -> ReadmeAgenticCompositionPlanV1:
    """Call the authoring model and fail closed on unbound editorial output.

    ``review_repair`` is internal wiring from the independent reviewer, not a
    planner-selectable argument.  It changes the authoring input hash and is
    included in the prompt from the first attempt, while the same deterministic
    section/fact/reference validators remain authoritative.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    accepted_ids = _accepted_fact_ids(facts)
    facts_payload = [
        fact.model_dump(mode="json") for fact in facts.facts if fact.fact_id in accepted_ids
    ]
    overview_phrase_options = _overview_phrase_options(facts)
    if not overview_phrase_options:
        raise LLMError("README composition has no accepted fact phrase eligible for an overview")
    assessment_payload = assessment.model_copy(
        update={"sections": _planning_sections(assessment)}
    ).model_dump(mode="json")
    resolved_client = client or LiveForcedToolClient(
        base_url=env.llm_base_url(),
        api_key=env.llm_api_key(),
        model=env.llm_model_for_job(_JOB),
        timeout=env.llm_timeout_seconds(),
        max_tokens=6000,
    )
    tool_schema = build_readme_composition_tool_schema(
        section_ids=[section["section_id"] for section in assessment_payload["sections"]],
        accepted_fact_ids=sorted(accepted_ids),
        overview_fact_ids=[option["fact_id"] for option in overview_phrase_options],
    )
    repair_request = (
        ReadmeCompositionRepairRequestV1.model_validate(review_repair)
        if review_repair is not None
        else None
    )
    repair_hints_section = (
        "INDEPENDENT REVIEW REPAIR. The prior candidate was rejected. "
        "Address only the bounded findings below, preserve the named content, "
        "and still obey every deterministic section disposition and fact-ID constraint:\n"
        + json.dumps(repair_request.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        if repair_request is not None
        else ""
    )
    last_error: LLMError | None = None
    for attempt in range(1, max_attempts + 1):
        input_payload = {
            "org_repo": org_repo,
            "source_text": source_text,
            "accepted_facts": facts_payload,
            "assessment": assessment_payload,
            "overview_phrase_options": overview_phrase_options,
            "repair_hints_section": repair_hints_section,
        }
        input_json = json.dumps(input_payload, sort_keys=True, separators=(",", ":"))
        messages = build_readme_composition_messages(
            org_repo=org_repo,
            source_text=source_text,
            accepted_facts_json=json.dumps(facts_payload, sort_keys=True),
            assessment_json=json.dumps(assessment_payload, sort_keys=True),
            overview_phrase_options_json=json.dumps(
                overview_phrase_options,
                sort_keys=True,
                ensure_ascii=False,
            ),
            repair_hints_section=repair_hints_section,
        )
        try:
            result = resolved_client.call(messages, tool_schema)
            tool_draft = _AgenticCompositionToolDraftV1.model_validate(result.arguments)
            draft = _materialize_tool_draft(tool_draft, overview_phrase_options, facts)
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
            tool_schema_sha256=_canonical_hash(tool_schema),
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
    exact_overview_phrases = _overview_phrase_options(facts)
    return (
        f"REPAIR ATTEMPT {attempt}. The previous JSON was rejected: {error}\n"
        "Call submit_readme_composition_plan again. Include exactly one "
        "section_decision for each of these IDs:\n"
        + json.dumps([section.section_id for section in _planning_sections(assessment)])
        + "\nFor overview_fact_ids, select fact IDs from these options; deterministic code "
        "will materialize literal phrases:\n"
        + json.dumps(exact_overview_phrases, ensure_ascii=False)
    )
