"""Validate source, fact, prompt, and schema bindings on composition plans."""

from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.generation_prompts import build_readme_composition_tool_schema
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.readme.agentic_composition_grounding import (
    accepted_composition_fact_ids,
    overview_phrase_options,
    phrases_overlap,
    required_overview_fact_ids,
)
from readme_agent.readme.agentic_composition_models import (
    AgenticCompositionDraftV1,
    ReadmeAgenticCompositionPlanV1,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1

_JOB = "plan_readme_composition"


def planning_sections(assessment: ReadmeAssessmentV1):
    """Bound agentic output to structural or materially actionable sections."""

    return [
        section
        for section in assessment.sections
        if section.level <= 2 or section.disposition != "preserve"
    ]


def bind_source_dispositions(
    draft: AgenticCompositionDraftV1,
    assessment: ReadmeAssessmentV1,
) -> AgenticCompositionDraftV1:
    """Replace copied model dispositions with authoritative deterministic values."""

    dispositions = {
        section.section_id: section.disposition for section in planning_sections(assessment)
    }
    return draft.model_copy(
        update={
            "section_decisions": [
                (
                    decision.model_copy(update={"disposition": dispositions[decision.section_id]})
                    if decision.section_id in dispositions
                    else decision
                )
                for decision in draft.section_decisions
            ]
        }
    )


def validate_composition_draft(
    draft: AgenticCompositionDraftV1,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
) -> None:
    """Fail closed when a materialized composition draft exceeds its bindings."""

    section_ids = {section.section_id for section in planning_sections(assessment)}
    decision_ids = [decision.section_id for decision in draft.section_decisions]
    if len(decision_ids) != len(set(decision_ids)):
        raise LLMError("composition returned duplicate section decisions")
    duplicate_fact_lists = [
        decision.section_id
        for decision in draft.section_decisions
        if len(decision.supporting_fact_ids) != len(set(decision.supporting_fact_ids))
    ]
    if duplicate_fact_lists:
        raise LLMError(
            "composition returned duplicate supporting fact IDs for sections: "
            f"{sorted(duplicate_fact_lists)}"
        )
    accepted_ids = accepted_composition_fact_ids(facts)
    unknown_sections = {
        decision.section_id
        for decision in draft.section_decisions
        if decision.section_id not in section_ids
    }
    if unknown_sections:
        raise LLMError(f"composition cited unknown section IDs: {sorted(unknown_sections)}")
    missing_sections = section_ids - set(decision_ids)
    if missing_sections:
        raise LLMError(
            f"composition omitted source-bound section decisions: {sorted(missing_sections)}"
        )
    dispositions = {
        section.section_id: section.disposition for section in planning_sections(assessment)
    }
    mismatched_dispositions = [
        f"{decision.section_id}:{decision.disposition}!={dispositions[decision.section_id]}"
        for decision in draft.section_decisions
        if decision.section_id in dispositions
        and decision.disposition != dispositions[decision.section_id]
    ]
    if mismatched_dispositions:
        raise LLMError(
            "composition changed deterministic source-bound dispositions: "
            f"{sorted(mismatched_dispositions)}"
        )
    cited_ids = {
        fact_id for decision in draft.section_decisions for fact_id in decision.supporting_fact_ids
    } | {
        fact_id for sentence in draft.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    unknown_facts = cited_ids - accepted_ids
    if unknown_facts:
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
            phrases_overlap(sentence.text, other.text)
            for other in draft.overview_sentences[index + 1 :]
        ):
            raise LLMError("composition returned semantically duplicate overview sentences")
    required_ids = required_overview_fact_ids(facts)
    overview_ids = {
        fact_id for sentence in draft.overview_sentences for fact_id in sentence.supporting_fact_ids
    }
    missing_overview_ids = required_ids - overview_ids
    if missing_overview_ids:
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
    accepted_ids = accepted_composition_fact_ids(facts)
    phrase_options = overview_phrase_options(facts)
    assessment_payload = assessment.model_copy(
        update={"sections": planning_sections(assessment)}
    ).model_dump(mode="json")
    tool_schema = build_readme_composition_tool_schema(
        section_ids=[section["section_id"] for section in assessment_payload["sections"]],
        accepted_fact_ids=sorted(accepted_ids),
        overview_fact_ids=[option["fact_id"] for option in phrase_options],
    )
    schema_hash = hashlib.sha256(
        json.dumps(tool_schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    expected_bindings = {
        "org_repo": org_repo,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "facts_hash": facts.canonical_hash(),
        "assessment_hash": assessment.canonical_hash(),
        "prompt_sha256": prompt_hash(_JOB),
        "tool_schema_sha256": schema_hash,
    }
    mismatches = [
        field for field, expected in expected_bindings.items() if getattr(plan, field) != expected
    ]
    if mismatches:
        raise LLMError(f"README composition plan binding mismatch: {sorted(mismatches)}")
    validate_composition_draft(
        AgenticCompositionDraftV1(
            repository_summary=plan.repository_summary,
            section_decisions=plan.section_decisions,
            overview_sentences=plan.overview_sentences,
        ),
        assessment,
        facts,
    )
    return plan
