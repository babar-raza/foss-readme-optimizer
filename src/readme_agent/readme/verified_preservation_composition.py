"""Build zero-provider composition plans for strong repository-verified READMEs."""

from __future__ import annotations

import hashlib
import json
import re

from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import README_DRAFTABLE_PRODUCT_FIELDS, ProductFactsV2
from readme_agent.llm.generation_prompts import build_readme_composition_tool_schema
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.readme.agentic_composition_assessment import (
    planning_assessment_payload,
    planning_sections,
)
from readme_agent.readme.agentic_composition_grounding import (
    accepted_composition_fact_ids,
    materialize_tool_draft,
    overview_phrase_options,
    required_overview_fact_ids,
)
from readme_agent.readme.agentic_composition_inputs import (
    composition_fact_payloads,
    composition_input_payload,
    composition_input_sha256,
)
from readme_agent.readme.agentic_composition_models import (
    AgenticCompositionToolDraftV1,
    AgenticDiagramV1,
    AgenticOverviewSentenceV1,
    AgenticSectionDecisionV1,
    ReadmeAgenticCompositionPlanV1,
)
from readme_agent.readme.agentic_composition_validation import (
    validate_composition_draft,
    validate_readme_composition_plan,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.diagram_role_semantics import normalize_diagram_role_nodes
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.opening_summary_fallback import (
    should_use_verified_format_opening,
    verified_format_opening_summary,
)
from readme_agent.readme.presentation_contract import (
    PRESENTATION_MERMAID_MIN_CAPABILITIES,
    PRESENTATION_MERMAID_MIN_INPUTS,
    PRESENTATION_MERMAID_MIN_OUTPUTS,
    PRESENTATION_MERMAID_TARGET_CAPABILITIES,
    PRESENTATION_MERMAID_TARGET_INPUTS,
    PRESENTATION_MERMAID_TARGET_OUTPUTS,
)
from readme_agent.state.lifecycle_schema import ReadmePocStatusV2

_JOB = "plan_readme_composition"
_MODEL = "deterministic-verified-preservation-v1"
_AUTHORING_HINTS = (
    "Deterministic verified-preservation composition from accepted repository facts; "
    "zero authoring-provider calls."
)
_MINIMUM_SOURCE_BYTES = 512
_MINIMUM_H2_SECTIONS = 3
_MINIMUM_MATERIAL_CLAIMS = 4
_BADGE_LINE = re.compile(r"(?m)^(?:!\[|\[!\[).+$")
_AT_A_GLANCE_MERMAID = re.compile(r"(?msi)^##[ \t]+At a glance[ \t]*\r?\n.*?^```mermaid[ \t]*\r?\n")
_ACTION_BASES = {
    "add": "add",
    "adds": "add",
    "build": "build",
    "builds": "build",
    "convert": "convert",
    "converts": "convert",
    "create": "create",
    "creates": "create",
    "export": "export",
    "exports": "export",
    "extract": "extract",
    "extracts": "extract",
    "generate": "generate",
    "generates": "generate",
    "import": "import",
    "imports": "import",
    "inspect": "inspect",
    "inspects": "inspect",
    "load": "load",
    "loads": "load",
    "manipulate": "manipulate",
    "manipulates": "manipulate",
    "process": "process",
    "processes": "process",
    "read": "read",
    "reads": "read",
    "render": "render",
    "renders": "render",
    "save": "save",
    "saves": "save",
    "write": "write",
    "writes": "write",
}
_PLATFORM_INITIALS = frozenset({".net", "c++", "go", "java", "python", "rust", "typescript"})
_FACTS_READY_OR_LATER: frozenset[ReadmePocStatusV2] = frozenset(
    {
        "FACTS_READY",
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_REVIEW_READY",
        "HUMAN_ACCEPTED",
        "PR_ELIGIBLE",
        "PR_PROOF_COMPLETE",
    }
)


def _has_existing_presentation_shell(source_text: str) -> bool:
    """Keep zero-provider repair only when the source already owns the visual shell."""

    headings = parse_headings(source_text)
    return (
        any(heading.level == 1 for heading in headings)
        and _BADGE_LINE.search(source_text) is not None
        and _AT_A_GLANCE_MERMAID.search(source_text) is not None
    )


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verified_preservation_eligible(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
    *,
    lifecycle_status: ReadmePocStatusV2,
    require_presentation_shell: bool = False,
) -> bool:
    """Return whether preservation can replace authoring without reducing assurance."""

    if lifecycle_status not in _FACTS_READY_OR_LATER:
        return False
    if facts.content_assurance != "repository_verified" or facts.org_repo != org_repo:
        return False
    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if (
        assessment.org_repo != org_repo
        or assessment.source_sha256 != source_sha256
        or assessment.facts_hash != facts.canonical_hash()
    ):
        return False
    if assessment.untrusted_repository_instructions:
        return False
    if len(source_text.encode("utf-8")) < _MINIMUM_SOURCE_BYTES:
        return False
    headings = parse_headings(source_text)
    if not any(heading.level == 1 for heading in headings):
        return False
    if sum(heading.level == 2 for heading in headings) < _MINIMUM_H2_SECTIONS:
        return False
    if len(assessment.material_claims) < _MINIMUM_MATERIAL_CLAIMS:
        return False
    if require_presentation_shell and not _has_existing_presentation_shell(source_text):
        return False
    for field in README_DRAFTABLE_PRODUCT_FIELDS:
        selected = facts.selected_fact(field)
        if (
            selected.verification_state not in {"verified", "policy_approved"}
            or selected.has_unresolved_conflict
        ):
            return False
    return bool(overview_phrase_options(facts))


def _section_decisions(
    assessment: ReadmeAssessmentV1,
    accepted_fact_ids: set[str],
) -> list[AgenticSectionDecisionV1]:
    priorities = {
        "repair": 100,
        "remove_update": 100,
        "replace_generic": 100,
        "add": 90,
        "investigate": 80,
        "rewrite": 70,
        "preserve": 50,
        "not_applicable": 0,
    }
    return [
        AgenticSectionDecisionV1(
            section_id=section.section_id,
            disposition=section.disposition,
            priority=priorities[section.disposition],
            supporting_fact_ids=[
                fact_id for fact_id in section.fact_ids if fact_id in accepted_fact_ids
            ],
            rationale=(
                "Apply the deterministic source-bound assessment while preserving all "
                "content outside its authorized operation."
            ),
        )
        for section in planning_sections(assessment)
    ]


def _natural_fragment(text: str, *, audience: bool = False) -> str:
    fragment = " ".join(text.strip().rstrip(". ").split())
    if not fragment:
        return fragment
    first_match = re.match(r"([^\s]+)", fragment)
    assert first_match is not None
    first = first_match.group(1)
    if audience and first.casefold() not in _PLATFORM_INITIALS and first[:1].isupper():
        fragment = first[:1].lower() + first[1:] + fragment[len(first) :]
    return fragment


def _sentence_internal_action_fragment(text: str) -> str | None:
    """Lower only a known leading action verb for safe sentence-internal prose."""

    fragment = _natural_fragment(text)
    first_match = re.match(r"([A-Za-z]+)", fragment)
    if first_match is None:
        return None
    first = first_match.group(1)
    base = _ACTION_BASES.get(first.casefold())
    if base is None:
        return None
    return base + fragment[first_match.end(1) :]


def _opening_text(title: str, audience: str, purpose: str) -> str:
    first_match = re.match(r"([A-Za-z]+)", purpose)
    if first_match is None:
        return f"{title} provides {purpose} for {audience}."
    first = first_match.group(1)
    base = _ACTION_BASES.get(first.casefold())
    if base is not None:
        infinitive = base + purpose[first_match.end(1) :]
        return f"{title} provides {audience} a way to {infinitive}."
    return f"{title} provides {purpose} for {audience}."


def _verified_opening_summary(facts: ProductFactsV2) -> AgenticOverviewSentenceV1 | None:
    identity = visitor_fact_render_view(facts, "product.identity")
    audience = visitor_fact_render_view(facts, "product.audience")
    purpose = next(
        (
            view
            for field in ("product.problems_solved", "product.capabilities", "product.formats")
            if (view := visitor_fact_render_view(facts, field)) is not None and view.phrases
        ),
        None,
    )
    if identity is None or audience is None or purpose is None:
        return None
    title = identity.phrases[0].strip().rstrip(".")
    audience_text = _natural_fragment(audience.phrases[0], audience=True)
    purpose_text = _natural_fragment(purpose.phrases[0])
    if not title or not audience_text or not purpose_text:
        return None
    text = _opening_text(title, audience_text, purpose_text)
    supporting_fact_ids = [identity.fact_id, audience.fact_id, purpose.fact_id]
    capabilities = visitor_fact_render_view(facts, "product.capabilities")
    if capabilities is not None and any(
        phrase.casefold().rstrip(". ") == purpose.phrases[0].casefold().rstrip(". ")
        for phrase in capabilities.phrases
    ):
        remaining = [
            fragment
            for phrase in capabilities.phrases
            if phrase.casefold().rstrip(". ") != purpose.phrases[0].casefold().rstrip(". ")
            if (fragment := _sentence_internal_action_fragment(phrase)) is not None
        ]
        remaining = remaining[:2]
        if remaining:
            tail = (
                remaining[0]
                if len(remaining) == 1
                else ", ".join(remaining[:-1]) + f", and {remaining[-1]}"
            )
            text += f" Its verified scope also includes {tail}."
            supporting_fact_ids.append(capabilities.fact_id)
    return AgenticOverviewSentenceV1(
        text=text,
        supporting_fact_ids=supporting_fact_ids,
    )


def build_verified_preservation_composition_plan(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
    *,
    lifecycle_status: ReadmePocStatusV2,
    require_presentation_shell: bool = False,
) -> ReadmeAgenticCompositionPlanV1 | None:
    """Return a fully bound deterministic plan, or defer to live composition."""

    if not verified_preservation_eligible(
        org_repo,
        source_text,
        facts,
        assessment,
        lifecycle_status=lifecycle_status,
        require_presentation_shell=require_presentation_shell,
    ):
        return None

    accepted_ids = accepted_composition_fact_ids(facts)
    phrase_options = overview_phrase_options(facts)
    required_ids = required_overview_fact_ids(facts)
    ordered_required_ids = [
        option["fact_id"] for option in phrase_options if option["fact_id"] in required_ids
    ]
    opening_summary = _verified_opening_summary(facts)
    if opening_summary is None or should_use_verified_format_opening(facts):
        opening_summary = verified_format_opening_summary(facts) or opening_summary
    if opening_summary is None:
        return None
    tool_draft = AgenticCompositionToolDraftV1(
        repository_summary=(
            "Preserve the strong existing README and apply only deterministic, fact-bound "
            "presentation operations."
        ),
        section_decisions=_section_decisions(assessment, accepted_ids),
        overview_fact_ids=ordered_required_ids,
        opening_summary=opening_summary,
        diagram=AgenticDiagramV1(),
    )
    draft = materialize_tool_draft(tool_draft, phrase_options, facts)
    normalized_nodes = normalize_diagram_role_nodes(
        draft.diagram.nodes,
        facts,
        {
            "input": PRESENTATION_MERMAID_MIN_INPUTS,
            "capability": PRESENTATION_MERMAID_MIN_CAPABILITIES,
            "output": PRESENTATION_MERMAID_MIN_OUTPUTS,
        },
        target_counts={
            "input": PRESENTATION_MERMAID_TARGET_INPUTS,
            "capability": PRESENTATION_MERMAID_TARGET_CAPABILITIES,
            "output": PRESENTATION_MERMAID_TARGET_OUTPUTS,
        },
    )
    draft = draft.model_copy(
        update={"diagram": draft.diagram.model_copy(update={"nodes": normalized_nodes})}
    )
    try:
        validate_composition_draft(draft, assessment, facts)
    except LLMError:
        return None

    assessment_payload = planning_assessment_payload(assessment)
    tool_schema = build_readme_composition_tool_schema(
        section_ids=[section["section_id"] for section in assessment_payload["sections"]],
        accepted_fact_ids=sorted(accepted_ids),
        overview_fact_ids=[option["fact_id"] for option in phrase_options],
    )
    input_payload = composition_input_payload(
        org_repo=org_repo,
        source_text=source_text,
        facts_payload=composition_fact_payloads(facts, accepted_ids),
        assessment_payload=assessment_payload,
        phrase_options=phrase_options,
        authoring_hints=_AUTHORING_HINTS,
    )
    plan = ReadmeAgenticCompositionPlanV1(
        org_repo=org_repo,
        source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        facts_hash=facts.canonical_hash(),
        assessment_hash=assessment.canonical_hash(),
        prompt_sha256=prompt_hash(_JOB),
        tool_schema_sha256=_canonical_hash(tool_schema),
        input_sha256=composition_input_sha256(input_payload),
        model=_MODEL,
        attempt_count=1,
        authoring_hints=_AUTHORING_HINTS,
        **draft.model_dump(),
    )
    return validate_readme_composition_plan(
        plan.model_dump(mode="json"),
        org_repo=org_repo,
        source_text=source_text,
        facts=facts,
        assessment=assessment,
    )
