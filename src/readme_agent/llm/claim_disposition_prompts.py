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
                        "excluded_with_reason",
                        "unverifiable",
                    ],
                    "description": (
                        "redundant_with_candidate: the claim's meaning is already present, "
                        "in different words, in the generated candidate text. "
                        "verified_against_source: the claim is a genuinely new, checkable "
                        "detail confirmed by reading real repository source. "
                        "narrative_filler: the claim carries no independent factual content "
                        "(pure transition/framing prose). "
                        "excluded_with_reason: the claim is deliberately excluded from the "
                        "candidate for exactly one machine-checkable predicate named in "
                        "evidence_ref (see evidence_ref). "
                        "unverifiable: none of the above apply -- default to this when unsure."
                    ),
                },
                "evidence_type": {
                    "type": "string",
                    "enum": [
                        "candidate_section_reference",
                        "clone_cache_path",
                        "checkable_predicate",
                        "api_surface_member",
                        "none",
                    ],
                    "description": (
                        "candidate_section_reference for redundant_with_candidate, "
                        "clone_cache_path for verified_against_source citing real source "
                        "text or a named fixture's existence, api_surface_member for "
                        "verified_against_source citing a real API member's confirmed "
                        "existence (see evidence_ref), checkable_predicate for "
                        "excluded_with_reason, none otherwise."
                    ),
                },
                "evidence_ref": {
                    "type": "string",
                    "maxLength": 512,
                    "description": (
                        "For candidate_section_reference: the candidate H2/H3 heading the "
                        "matching text lives under. For clone_cache_path: the exact "
                        "repository-relative file path read. For api_surface_member: the "
                        "bare member name (e.g. 'generate'), copied verbatim from the "
                        "inline code already in the claim text -- never a name the claim "
                        "does not already mention. For checkable_predicate, "
                        "exactly one of: 'unverifiable_fixture_dependency:<path>' (the "
                        "claim references a repository fixture path, copied verbatim from "
                        "the claim text, that an isolated verifier cannot assume), "
                        "'superseded_by_verified_slot:<slot_id>' (a verified candidate "
                        "section supersedes the claim; quote that section), or "
                        "'stale_version_string:<version>' (the claim pins a version, copied "
                        "verbatim from the claim text, that the candidate no longer "
                        "mentions anywhere). Empty otherwise."
                    ),
                },
                "evidence_quote": {
                    "type": "string",
                    "maxLength": 800,
                    "description": (
                        "A verbatim substring copied character-for-character from the "
                        "evidence location (the candidate text or the named source file) "
                        "that supports the classification. For "
                        "superseded_by_verified_slot: at least 40 characters copied "
                        "verbatim from the superseding candidate section. For "
                        "verified_against_source citing a real, non-text repository fixture "
                        "the claim already names verbatim (e.g. a binary test document like "
                        "'testfiles/SimpleTable.one') where no readable quote inside the "
                        "file is possible: leave this EMPTY -- existence of the named file "
                        "is verified separately. For verified_against_source with "
                        "evidence_type api_surface_member -- the claim paraphrases a real "
                        "API member's behavior rather than quoting text -- also leave this "
                        "EMPTY: name a real member already inline-coded in the claim via "
                        "evidence_ref instead, confirmed to exist rather than quoted. Empty "
                        "for narrative_filler, unverifiable, and the other "
                        "excluded_with_reason predicates."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "maxLength": 500,
                    "description": (
                        "A concise explanation of the classification. Do not repeat the claim, "
                        "candidate, file listing, or evidence quote."
                    ),
                },
            },
            "required": ["classification", "evidence_type", "evidence_ref", "reasoning"],
            "additionalProperties": False,
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
