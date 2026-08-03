"""Build the governed prompt and tool contract for one merged README review call."""

import json
from copy import deepcopy
from string import Template

from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import (
    BLIND_QUALITY_REVIEW_TOOL_SCHEMA,
    FACTUAL_PLAN_REVIEW_TOOL_SCHEMA,
)
from readme_agent.specialists.factual_review_projection import compact_candidate_anchor_catalog
from readme_agent.specialists.review_mechanical_observations import (
    render_candidate_mechanical_observations,
)


def _compact_merged_facet(schema: dict) -> dict:
    """Bound merged output without weakening either role's grounding contract."""

    parameters = deepcopy(schema["function"]["parameters"])
    parameters["properties"]["reasoning"]["maxLength"] = 1000
    parameters["properties"]["required_repair"]["maxLength"] = 1500
    parameters["properties"]["findings"]["maxItems"] = 4
    return parameters


MERGED_README_REVIEW_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "report_merged_readme_review",
        "description": (
            "Return one independent review containing separately typed and grounded quality "
            "and factual facets. Each ACCEPT facet requires supporting findings."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "quality": _compact_merged_facet(BLIND_QUALITY_REVIEW_TOOL_SCHEMA),
                "factual": _compact_merged_facet(FACTUAL_PLAN_REVIEW_TOOL_SCHEMA),
            },
            "required": ["quality", "factual"],
        },
    },
}


def build_merged_readme_review_messages(
    org_repo: str,
    candidate_readme_text: str,
    visitor_contract_json: str,
    product_facts_json: str,
    presentation_plan_json: str,
) -> list[dict]:
    """Build one non-duplicative candidate catalog for two typed review facets."""

    manifest = prompt_registry.get("merged_readme_review")
    assert manifest is not None, "merged_readme_review prompt missing"
    assert manifest.user_template is not None
    try:
        visitor_contract = json.loads(visitor_contract_json)
    except json.JSONDecodeError:
        visitor_contract = {}
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            visitor_contract_json=visitor_contract_json,
            candidate_anchor_catalog_json=json.dumps(
                compact_candidate_anchor_catalog(candidate_readme_text),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            candidate_mechanical_observations_json=json.dumps(
                render_candidate_mechanical_observations(
                    candidate_readme_text,
                    visitor_contract,
                ),
                ensure_ascii=False,
                sort_keys=True,
            ),
            product_facts_json=product_facts_json,
            presentation_plan_json=presentation_plan_json,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]
