"""Build the governed prompt and tool contract for one section-cluster authoring call.

Section-cluster authoring (2-4 facts/call) is the production shape recommended by
`runs/owner_audit_staging/qwen3-next-editorial-probe-aa9981021/
RECOMMENDED_EDITORIAL_TASK_CONTRACT.json`: one bounded forced-tool call authors 1-4 prose
units for one section cluster from a closed accepted-fact set, the same contract across every
platform and every authoring task family -- only the packet content (target section, objective,
facts) varies per call, never the schema or prompt.
"""

from string import Template
from typing import Literal, get_args

from readme_agent.llm import prompt_registry

SectionAuthoringTaskFamily = Literal[
    "opening_summary",
    "capability_entry_cluster",
    "installation_framing",
    "verified_example_framing",
    "scope_and_limitations",
]

TASK_FAMILIES: tuple[SectionAuthoringTaskFamily, ...] = get_args(SectionAuthoringTaskFamily)

MAX_UNITS = 4
MAX_UNIT_CHARS = 1200
MAX_HEADING_CHARS = 80
MAX_OMITTED_REASON_CHARS = 200


def build_section_cluster_authoring_tool_schema(accepted_fact_ids: list[str]) -> dict:
    """Bind the citable `fact_ids` enum to accepted facts only.

    `do_not_claim` facts are deliberately never eligible values here -- the schema itself, not
    a post-hoc keyword screen, is what makes a negative/conflicting fact structurally unable to
    authorize a positive claim.
    """

    return {
        "type": "function",
        "function": {
            "name": "submit_section_cluster",
            "description": (
                "Report 1-4 authored prose units for one bounded README section cluster, and "
                "the disposition of every accepted fact."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["units", "omitted"],
                "properties": {
                    "units": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_UNITS,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["heading", "text", "fact_ids"],
                            "properties": {
                                "heading": {"type": "string", "maxLength": MAX_HEADING_CHARS},
                                "text": {"type": "string", "maxLength": MAX_UNIT_CHARS},
                                "fact_ids": {
                                    "type": "array",
                                    "minItems": 1,
                                    "items": {"type": "string", "enum": accepted_fact_ids},
                                },
                            },
                        },
                    },
                    "omitted": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["fact_id", "reason"],
                            "properties": {
                                "fact_id": {"type": "string", "enum": accepted_fact_ids},
                                "reason": {
                                    "type": "string",
                                    "maxLength": MAX_OMITTED_REASON_CHARS,
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def build_section_cluster_authoring_messages(
    *,
    org_repo: str,
    public_product_name: str,
    target_section_id: str,
    task_family: str,
    section_objective: str,
    accepted_facts_json: str,
    do_not_claim_json: str,
    seo_vocabulary_json: str,
    current_source_text: str,
    repair_hint: str = "",
) -> list[dict]:
    """Fill `prompts/generation/section_cluster_authoring.yaml`'s `user_template`."""

    manifest = prompt_registry.get("section_cluster_authoring")
    assert manifest is not None, "prompts/generation/section_cluster_authoring.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            public_product_name=public_product_name,
            target_section_id=target_section_id,
            task_family=task_family,
            section_objective=section_objective,
            accepted_facts_json=accepted_facts_json,
            do_not_claim_json=do_not_claim_json,
            seo_vocabulary_json=seo_vocabulary_json,
            current_source_text=current_source_text,
            repair_hint=repair_hint,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]
