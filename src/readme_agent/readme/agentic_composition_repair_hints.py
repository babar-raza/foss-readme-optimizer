"""Build deterministic repair-hint text for a rejected composition draft."""

from __future__ import annotations

import json

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_assessment import planning_sections
from readme_agent.readme.agentic_composition_grounding import overview_phrase_options
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.diagram_role_semantics import diagram_role_phrase_guidance


def deterministic_repair_hints(
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


__all__ = ["deterministic_repair_hints"]
