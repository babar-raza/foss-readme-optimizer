"""Tool schema and message builder for the `claim_disposition_check` job.

Mirrors `verification_prompts.py`'s `PROSE_QUALITY_TOOL_SCHEMA`/
`build_prose_quality_messages` pattern exactly, kept in its own module
(governance's "no monoliths" placement rule) since `verification_prompts.py`
is already large. `CLAIM_DISPOSITION_TOOL_SCHEMA` is a parameter schema, not
prompt content, so it stays a plain dict here rather than YAML content."""

from __future__ import annotations

from string import Template

from readme_agent.llm import prompt_registry

CLAIM_DISPOSITION_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "report_claim_disposition",
        "description": (
            "Classify one source-README claim that a mechanical fact-coverage check could not "
            "bind to a verified fact, and cite exact, checkable evidence for the classification."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "classification": {
                    "type": "string",
                    "enum": [
                        "redundant_with_candidate",
                        "verified_against_source",
                        "narrative_filler",
                        "unverifiable",
                    ],
                    "description": (
                        "redundant_with_candidate: the claim's meaning is already present, "
                        "in different words, in the generated candidate text. "
                        "verified_against_source: the claim is a genuinely new, checkable "
                        "detail confirmed by reading real repository source. "
                        "narrative_filler: the claim carries no independent factual content "
                        "(pure transition/framing prose). "
                        "unverifiable: none of the above apply -- default to this when unsure."
                    ),
                },
                "evidence_type": {
                    "type": "string",
                    "enum": ["candidate_section_reference", "clone_cache_path", "none"],
                    "description": (
                        "candidate_section_reference for redundant_with_candidate, "
                        "clone_cache_path for verified_against_source, none otherwise."
                    ),
                },
                "evidence_ref": {
                    "type": "string",
                    "description": (
                        "For candidate_section_reference: the candidate H2/H3 heading the "
                        "matching text lives under. For clone_cache_path: the exact "
                        "repository-relative file path read. Empty otherwise."
                    ),
                },
                "evidence_quote": {
                    "type": "string",
                    "description": (
                        "A verbatim substring copied character-for-character from the "
                        "evidence location (the candidate text or the named source file) "
                        "that supports the classification. Empty for narrative_filler or "
                        "unverifiable."
                    ),
                },
                "reasoning": {"type": "string"},
            },
            "required": ["classification", "evidence_type", "evidence_ref", "reasoning"],
        },
    },
}


def build_claim_disposition_messages(
    claim_text: str,
    candidate_text: str,
    repository_file_listing: str,
) -> list[dict]:
    manifest = prompt_registry.get("claim_disposition_check")
    assert manifest is not None, "prompts/verification/claim_disposition_check.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            claim_text=claim_text,
            candidate_text=candidate_text,
            repository_file_listing=repository_file_listing,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]
