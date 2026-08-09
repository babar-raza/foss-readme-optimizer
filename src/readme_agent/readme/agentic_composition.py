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
from readme_agent.readme.agentic_composition_assessment import (
    planning_assessment_payload,
    planning_sections,
)
from readme_agent.readme.agentic_composition_grounding import (
    accepted_composition_fact_ids,
    materialize_tool_draft,
    overview_phrase_options,
)
from readme_agent.readme.agentic_composition_inputs import (
    composition_fact_payloads,
    composition_input_payload,
    composition_input_sha256,
    independent_repair_hints,
)
from readme_agent.readme.agentic_composition_models import (
    MAX_AUTHORING_ATTEMPTS,
    AgenticCompositionToolDraftV1,
    ReadmeAgenticCompositionPlanV1,
    ReadmeCompositionRepairRequestV1,
)
from readme_agent.readme.agentic_composition_validation import (
    bind_source_dispositions,
    validate_composition_draft,
    validate_readme_composition_plan,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.diagram_role_semantics import (
    diagram_role_phrase_guidance,
    evidence_scaled_role_minimums,
    normalize_diagram_role_nodes,
)
from readme_agent.readme.opening_summary_fallback import (
    should_use_verified_format_opening,
    verified_format_opening_summary,
    verified_identity_opening_summary,
)
from readme_agent.readme.presentation_contract import (
    PRESENTATION_MERMAID_MIN_CAPABILITIES,
    PRESENTATION_MERMAID_MIN_INPUTS,
    PRESENTATION_MERMAID_MIN_OUTPUTS,
    PRESENTATION_MERMAID_TARGET_CAPABILITIES,
    PRESENTATION_MERMAID_TARGET_INPUTS,
    PRESENTATION_MERMAID_TARGET_OUTPUTS,
)

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
        + "\nFor opening_summary, use the complete product identity, cite that identity plus "
        "the accepted audience fact and at least one accepted purpose/capability/format fact, "
        "and omit promotion, Enterprise Edition comparisons, commercial terminology, and hashes."
        + "\nFor diagram.nodes, use only labels from the role-compatible vocabulary below. "
        "Do not fill a count, reclassify a capability as an output, or invent a missing role; "
        "deterministic evidence owns role assignment. Every proposed label must "
        "retain at least one literal product term from the supplied vocabulary; "
        "do not use action phrases as inputs, and do not use runtime, source-code, package, "
        "installation, API, license, or support nouns "
        "unless they literally occur in this vocabulary:\n"
        + json.dumps(diagram_role_phrase_guidance(facts), ensure_ascii=False, sort_keys=True)
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
    facts_payload = composition_fact_payloads(facts, accepted_ids)
    phrase_options = overview_phrase_options(facts)
    if not phrase_options:
        raise LLMError("README composition has no accepted fact phrase eligible for an overview")
    assessment_payload = planning_assessment_payload(assessment)
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
    independent_hints = independent_repair_hints(repair_request)
    role_guidance = (
        "AUTHORITATIVE DIAGRAM ROLE VOCABULARY. You may omit or reorder exact labels, but "
        "must not relabel or reclassify them:\n"
        + json.dumps(diagram_role_phrase_guidance(facts), ensure_ascii=False, sort_keys=True)
    )
    repair_hints_section = "\n".join(
        section for section in (independent_hints, role_guidance) if section
    )
    last_error: LLMError | None = None
    for attempt in range(1, max_attempts + 1):
        input_payload = composition_input_payload(
            org_repo=org_repo,
            source_text=source_text,
            facts_payload=facts_payload,
            assessment_payload=assessment_payload,
            phrase_options=phrase_options,
            authoring_hints=repair_hints_section,
        )
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
            if should_use_verified_format_opening(facts):
                format_opening = verified_format_opening_summary(facts)
                if format_opening is not None:
                    draft = draft.model_copy(update={"opening_summary": format_opening})
            normalized_nodes = normalize_diagram_role_nodes(
                draft.diagram.nodes,
                facts,
                evidence_scaled_role_minimums(
                    facts,
                    {
                        "input": PRESENTATION_MERMAID_MIN_INPUTS,
                        "capability": PRESENTATION_MERMAID_MIN_CAPABILITIES,
                        "output": PRESENTATION_MERMAID_MIN_OUTPUTS,
                    },
                ),
                target_counts={
                    "input": PRESENTATION_MERMAID_TARGET_INPUTS,
                    "capability": PRESENTATION_MERMAID_TARGET_CAPABILITIES,
                    "output": PRESENTATION_MERMAID_TARGET_OUTPUTS,
                },
            )
            draft = draft.model_copy(
                update={"diagram": draft.diagram.model_copy(update={"nodes": normalized_nodes})}
            )
            validate_composition_draft(draft, assessment, facts)
        except (LLMError, ValidationError) as exc:
            last_error = (
                exc
                if isinstance(exc, LLMError)
                else LLMError(f"README composition response failed schema validation: {exc}")
            )
            if attempt == max_attempts:
                fallback = (
                    verified_format_opening_summary(facts)
                    or verified_identity_opening_summary(facts)
                    if str(last_error).startswith("composition opening summary")
                    else None
                )
                if fallback is None:
                    raise last_error from exc
                draft = draft.model_copy(update={"opening_summary": fallback})
                validate_composition_draft(draft, assessment, facts)
            else:
                deterministic_repair_hints = _repair_hints(
                    last_error,
                    assessment,
                    facts,
                    attempt=attempt + 1,
                )
                repair_hints_section = "\n\n".join(
                    hint for hint in (independent_hints, deterministic_repair_hints) if hint
                )
                continue
        return ReadmeAgenticCompositionPlanV1(
            org_repo=org_repo,
            source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            facts_hash=facts.canonical_hash(),
            assessment_hash=assessment.canonical_hash(),
            prompt_sha256=prompt_hash(_JOB),
            tool_schema_sha256=_canonical_hash(tool_schema),
            input_sha256=composition_input_sha256(input_payload),
            model=result.meta.model or env.llm_model_for_job(_JOB),
            attempt_count=attempt,
            authoring_hints=repair_hints_section,
            review_repair=repair_request,
            **draft.model_dump(),
        )
    assert last_error is not None
    raise last_error
