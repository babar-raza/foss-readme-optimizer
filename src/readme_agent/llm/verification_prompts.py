"""The one place `verification/prose_quality.py`'s and `specialists/
independent_readme_review.py`'s prompt content is read from `prompts/`
(Wave 8.6, `VER-006` reversal; RPOC-022 extends it) -- per `prompts/README.md`
rule 2 ("only `src/readme_agent/llm/` may read `prompts/`"), mirroring how
`llm/prompts.py`/`supervisor/dossier.py` are the sanctioned readers for
their own jobs. Neither `verification/prose_quality.py` nor `specialists/
independent_readme_review.py` reads `prompts/` itself; each only calls its
own `build_*_messages()` helper below.

`PROSE_QUALITY_TOOL_SCHEMA` is a parameter schema, not prompt content --
mirrors `capabilities/schema.py::CapabilityManifest.to_tool_schema()`'s own
code-not-content treatment, so it stays here as a plain dict rather than
becoming YAML content."""

import hashlib
from string import Template

from readme_agent.llm import prompt_registry

PROSE_QUALITY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "report_prose_quality_finding",
        "description": (
            "Report whether the given paragraph reads as generic, repetitive, or "
            "mechanically-inserted prose rather than genuine, specific writing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "flagged": {"type": "boolean"},
                "quoted_span": {
                    "type": "string",
                    "description": (
                        "A verbatim substring of the reviewed paragraph that supports the "
                        "finding. Must be empty if flagged is false."
                    ),
                },
                "reason": {"type": "string"},
            },
            "required": ["flagged", "reason"],
        },
    },
}

INDEPENDENT_README_REVIEW_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "report_independent_readme_review",
        "description": (
            "Return the independent, evidence-grounded quality verdict for one README candidate."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "verdict": {
                    "type": "string",
                    "description": (
                        "Apply this precedence: a direct contradiction is "
                        "BLOCKED_FACT_CONFLICT; otherwise any concrete, externally checkable "
                        "candidate product claim absent from the supplied facts is "
                        "BLOCKED_MISSING_EVIDENCE, even when deleting it would be a bounded "
                        "repair. REJECT_REPAIRABLE is only for quality, completeness, "
                        "structure, specificity, or presentation defects when every concrete "
                        "product claim is fact-supported. Statements about the candidate "
                        "document's own omissions or malformed markup are directly observable "
                        "presentation defects, not missing product evidence."
                    ),
                    "enum": [
                        "ACCEPT",
                        "REJECT_REPAIRABLE",
                        "BLOCKED_FACT_CONFLICT",
                        "BLOCKED_MISSING_EVIDENCE",
                        "SYSTEM_FAILURE",
                    ],
                },
                "reasoning": {"type": "string"},
                "failed_criteria": {"type": "array", "items": {"type": "string"}},
                "sections_affected": {"type": "array", "items": {"type": "string"}},
                "required_repair": {"type": "string"},
                "preserve": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "verdict",
                "reasoning",
                "failed_criteria",
                "sections_affected",
                "required_repair",
                "preserve",
            ],
        },
    },
}


def _role_review_tool_schema(name: str, verdicts: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "Return one evidence-bound README review-role verdict.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "verdict": {"type": "string", "enum": verdicts},
                    "reasoning": {"type": "string"},
                    "failed_criteria": {"type": "array", "items": {"type": "string"}},
                    "sections_affected": {"type": "array", "items": {"type": "string"}},
                    "required_repair": {"type": "string"},
                },
                "required": [
                    "verdict",
                    "reasoning",
                    "failed_criteria",
                    "sections_affected",
                    "required_repair",
                ],
            },
        },
    }


BLIND_QUALITY_REVIEW_TOOL_SCHEMA = _role_review_tool_schema(
    "report_blind_readme_quality_review",
    ["ACCEPT", "REJECT_REPAIRABLE", "SYSTEM_FAILURE"],
)
FACTUAL_PLAN_REVIEW_TOOL_SCHEMA = _role_review_tool_schema(
    "report_factual_readme_plan_review",
    [
        "ACCEPT",
        "REJECT_REPAIRABLE",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "SYSTEM_FAILURE",
    ],
)


def separated_reviewer_standard_hash() -> str:
    """Bind lifecycle reuse to both role prompts and the V1 reducer contract."""

    components = [
        "separated-readme-review-v1",
        prompt_registry.prompt_hash("blind_readme_quality_review"),
        prompt_registry.prompt_hash("factual_readme_plan_review"),
        "SYSTEM_FAILURE>BLOCKED_FACT_CONFLICT>BLOCKED_MISSING_EVIDENCE>REJECT_REPAIRABLE>ACCEPT",
    ]
    return hashlib.sha256("\x00".join(components).encode("utf-8")).hexdigest()


def build_prose_quality_messages(paragraph_text: str) -> list[dict]:
    manifest = prompt_registry.get("prose_quality_check")
    assert manifest is not None, "prompts/verification/prose_quality_check.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template).substitute(paragraph_text=paragraph_text).strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]


def build_independent_readme_review_messages(
    org_repo: str,
    original_readme_text: str,
    candidate_readme_text: str,
    product_facts_json: str,
    presentation_plan_json: str,
    deterministic_validation_result_json: str,
) -> list[dict]:
    """RPOC-021/RPOC-022: fills `prompts/verification/independent_readme_
    review.yaml`'s `user_template` -- the five JSON-serializable inputs
    `specialists/independent_readme_review.py` independently assembles
    (never a pass-through of `_verify_node`'s own in-memory objects)."""
    manifest = prompt_registry.get("independent_readme_review")
    assert manifest is not None, "prompts/verification/independent_readme_review.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            original_readme_text=original_readme_text,
            candidate_readme_text=candidate_readme_text,
            product_facts_json=product_facts_json,
            presentation_plan_json=presentation_plan_json,
            deterministic_validation_result_json=deterministic_validation_result_json,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]


def build_independent_readme_review_retry_message(accepted_fact_refs_json: str) -> dict:
    """Build the governed semantic-retry turn for a contradicted missing-evidence verdict."""

    manifest = prompt_registry.get("independent_readme_review")
    assert manifest is not None, "prompts/verification/independent_readme_review.yaml missing"
    assert manifest.turn_context_template is not None
    content = (
        Template(manifest.turn_context_template)
        .substitute(accepted_fact_refs_json=accepted_fact_refs_json)
        .strip()
    )
    return {"role": "user", "content": content}


def build_blind_quality_review_messages(
    org_repo: str,
    original_readme_text: str,
    candidate_readme_text: str,
) -> list[dict]:
    """Build the visitor-quality context without producer or factual-plan conclusions."""

    manifest = prompt_registry.get("blind_readme_quality_review")
    assert manifest is not None, "blind_readme_quality_review prompt missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            original_readme_text=original_readme_text,
            candidate_readme_text=candidate_readme_text,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]


def build_factual_plan_review_messages(
    org_repo: str,
    candidate_readme_text: str,
    product_facts_json: str,
    presentation_plan_json: str,
) -> list[dict]:
    """Build fact-and-plan context without producer or deterministic acceptance wording."""

    manifest = prompt_registry.get("factual_readme_plan_review")
    assert manifest is not None, "factual_readme_plan_review prompt missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            candidate_readme_text=candidate_readme_text,
            product_facts_json=product_facts_json,
            presentation_plan_json=presentation_plan_json,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]
