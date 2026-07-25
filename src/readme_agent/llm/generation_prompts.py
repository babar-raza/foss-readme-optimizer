"""The one place `facts/agentic_drafting.py`'s prompt content is read from
`prompts/` (RPOC-033) -- per `prompts/README.md` rule 2 ("only
`src/readme_agent/llm/` may read `prompts/`"), mirroring `llm/verification_
prompts.py`'s/`llm/analysis_prompts.py`'s own sanctioned-reader pattern."""

from string import Template

from readme_agent.llm import prompt_registry

_ASSESSMENT_DISPOSITIONS = [
    "preserve",
    "rewrite",
    "investigate",
    "repair",
    "remove_update",
    "replace_generic",
    "add",
    "not_applicable",
]


def build_draft_product_truth_messages(
    org_repo: str,
    ecosystem: str,
    objective_facts_json: str,
    repository_context: str,
    repair_hints_section: str = "",
) -> list[dict]:
    """RPOC-033: fills `prompts/generation/draft_product_truth.yaml`'s
    `user_template`. `repair_hints_section` is pre-formatted by the caller
    (`facts/agentic_drafting.py::_format_repair_hints()`) -- empty string on
    a first attempt, a labeled block of specific gate-failure reasons on a
    repair attempt -- since `string.Template` substitution has no
    conditional-block syntax of its own."""
    manifest = prompt_registry.get("draft_product_truth")
    assert manifest is not None, "prompts/generation/draft_product_truth.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            ecosystem=ecosystem,
            objective_facts_json=objective_facts_json,
            repository_context=repository_context,
            repair_hints_section=repair_hints_section,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]


def build_readme_composition_messages(
    org_repo: str,
    source_text: str,
    accepted_facts_json: str,
    assessment_json: str,
    overview_phrase_options_json: str,
    repair_hints_section: str = "",
) -> list[dict]:
    """Build the source-bound README authoring turn from its registered prompt."""

    manifest = prompt_registry.get("plan_readme_composition")
    assert manifest is not None, "prompts/generation/plan_readme_composition.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            source_text=source_text,
            accepted_facts_json=accepted_facts_json,
            assessment_json=assessment_json,
            overview_phrase_options_json=overview_phrase_options_json,
            repair_hints_section=repair_hints_section,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]


def build_readme_composition_tool_schema(
    *,
    section_ids: list[str],
    accepted_fact_ids: list[str],
    overview_fact_ids: list[str],
) -> dict:
    """Build the one forced authoring tool from snapshot-bound identifiers."""

    return {
        "type": "function",
        "function": {
            "name": "submit_readme_composition_plan",
            "description": (
                "Submit one repository-specific README composition strategy using only the "
                "provided source-bound section and accepted fact identifiers."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "repository_summary",
                    "section_decisions",
                    "overview_fact_ids",
                ],
                "properties": {
                    "repository_summary": {"type": "string", "minLength": 1},
                    "section_decisions": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "section_id",
                                "disposition",
                                "priority",
                                "supporting_fact_ids",
                                "rationale",
                            ],
                            "properties": {
                                "section_id": {"type": "string", "enum": section_ids},
                                "disposition": {
                                    "type": "string",
                                    "enum": _ASSESSMENT_DISPOSITIONS,
                                },
                                "priority": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 100,
                                },
                                "supporting_fact_ids": {
                                    "type": "array",
                                    "uniqueItems": True,
                                    "items": {
                                        "type": "string",
                                        "enum": accepted_fact_ids,
                                    },
                                },
                                "rationale": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                    "overview_fact_ids": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {"type": "string", "enum": overview_fact_ids},
                    },
                },
            },
        },
    }
