"""The one place `facts/agentic_drafting.py`'s prompt content is read from
`prompts/` (RPOC-033) -- per `prompts/README.md` rule 2 ("only
`src/readme_agent/llm/` may read `prompts/`"), mirroring `llm/verification_
prompts.py`'s/`llm/analysis_prompts.py`'s own sanctioned-reader pattern."""

from string import Template

from readme_agent.llm import prompt_registry


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
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]
