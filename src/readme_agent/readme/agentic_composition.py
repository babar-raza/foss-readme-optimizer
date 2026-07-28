"""Orchestrate fact-bound agentic README composition."""

from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.generation_prompts import (
    build_readme_composition_messages,
    build_readme_composition_tool_schema,
)
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.verifier_client import ForcedToolClient, LiveForcedToolClient
from readme_agent.readme.agentic_composition_grounding import (
    accepted_composition_fact_ids,
    materialize_tool_draft,
    overview_phrase_options,
)
from readme_agent.readme.agentic_composition_models import (
    MAX_AUTHORING_ATTEMPTS,
    AgenticCompositionToolDraftV1,
    ReadmeAgenticCompositionPlanV1,
    ReadmeCompositionRepairRequestV1,
)
from readme_agent.readme.agentic_composition_validation import (
    bind_source_dispositions,
    planning_sections,
    validate_composition_draft,
    validate_readme_composition_plan,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1

_JOB = "plan_readme_composition"

__all__ = [
    "ReadmeAgenticCompositionPlanV1",
    "ReadmeCompositionRepairRequestV1",
    "plan_readme_composition",
    "validate_readme_composition_plan",
]


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _repair_hints(
    error: LLMError,
    assessment: ReadmeAssessmentV1,
    facts: ProductFactsV2,
    *,
    attempt: int,
) -> str:
    return (
        f"REPAIR ATTEMPT {attempt}. The previous JSON was rejected: {error}\n"
        "Call submit_readme_composition_plan again. Include exactly one "
        "section_decision for each source-bound ID and copy its paired disposition exactly:\n"
        + json.dumps(
            [
                {
                    "section_id": section.section_id,
                    "disposition": section.disposition,
                }
                for section in planning_sections(assessment)
            ],
            sort_keys=True,
        )
        + "\nFor overview_fact_ids, select fact IDs from these options; deterministic code "
        "will materialize literal phrases:\n"
        + json.dumps(overview_phrase_options(facts), ensure_ascii=False)
    )


def plan_readme_composition(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
    *,
    client: ForcedToolClient | None = None,
    max_attempts: int = MAX_AUTHORING_ATTEMPTS,
    review_repair: ReadmeCompositionRepairRequestV1 | dict | None = None,
) -> ReadmeAgenticCompositionPlanV1:
    """Call the authoring model and fail closed on unbound editorial output."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    accepted_ids = accepted_composition_fact_ids(facts)
    facts_payload = [
        fact.model_dump(mode="json") for fact in facts.facts if fact.fact_id in accepted_ids
    ]
    phrase_options = overview_phrase_options(facts)
    if not phrase_options:
        raise LLMError("README composition has no accepted fact phrase eligible for an overview")
    assessment_payload = assessment.model_copy(
        update={"sections": planning_sections(assessment)}
    ).model_dump(mode="json")
    resolved_client = client or LiveForcedToolClient(
        base_url=env.llm_base_url(),
        api_key=env.llm_api_key(),
        model=env.llm_model_for_job(_JOB),
        timeout=env.llm_timeout_seconds(),
        max_tokens=6000,
        job=_JOB,
        prompt_id=_JOB,
    )
    tool_schema = build_readme_composition_tool_schema(
        section_ids=[section["section_id"] for section in assessment_payload["sections"]],
        accepted_fact_ids=sorted(accepted_ids),
        overview_fact_ids=[option["fact_id"] for option in phrase_options],
    )
    repair_request = (
        ReadmeCompositionRepairRequestV1.model_validate(review_repair)
        if review_repair is not None
        else None
    )
    independent_repair_hints = (
        "INDEPENDENT REVIEW REPAIR. The prior candidate was rejected. "
        "Address only the bounded findings below, preserve the named content, "
        "and still obey every deterministic section disposition and fact-ID constraint:\n"
        + json.dumps(repair_request.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        if repair_request is not None
        else ""
    )
    repair_hints_section = independent_repair_hints
    last_error: LLMError | None = None
    for attempt in range(1, max_attempts + 1):
        input_payload = {
            "org_repo": org_repo,
            "source_text": source_text,
            "accepted_facts": facts_payload,
            "assessment": assessment_payload,
            "overview_phrase_options": phrase_options,
            "repair_hints_section": repair_hints_section,
        }
        input_json = json.dumps(input_payload, sort_keys=True, separators=(",", ":"))
        messages = build_readme_composition_messages(
            org_repo=org_repo,
            source_text=source_text,
            accepted_facts_json=json.dumps(facts_payload, sort_keys=True),
            assessment_json=json.dumps(assessment_payload, sort_keys=True),
            overview_phrase_options_json=json.dumps(
                phrase_options,
                sort_keys=True,
                ensure_ascii=False,
            ),
            repair_hints_section=repair_hints_section,
        )
        try:
            result = resolved_client.call(messages, tool_schema)
            tool_draft = AgenticCompositionToolDraftV1.model_validate(result.arguments)
            draft = materialize_tool_draft(tool_draft, phrase_options, facts)
            draft = bind_source_dispositions(draft, assessment)
            validate_composition_draft(draft, assessment, facts)
        except (LLMError, ValidationError) as exc:
            last_error = (
                exc
                if isinstance(exc, LLMError)
                else LLMError(f"README composition response failed schema validation: {exc}")
            )
            if attempt == max_attempts:
                raise last_error from exc
            deterministic_repair_hints = _repair_hints(
                last_error,
                assessment,
                facts,
                attempt=attempt + 1,
            )
            repair_hints_section = "\n\n".join(
                hint for hint in (independent_repair_hints, deterministic_repair_hints) if hint
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
