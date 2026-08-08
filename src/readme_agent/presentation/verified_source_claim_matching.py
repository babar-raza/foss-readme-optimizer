"""Match presentation-equivalent inherited and candidate claims."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.presentation_similarity import (
    capability_discriminators,
    semantically_repeats,
)
from readme_agent.readme.source_claim_assurance import accepted_source_claim_fact_ids
from readme_agent.readme.source_claim_fact_binding import (
    complete_source_claim_fact_binding,
    python_claim_has_comments,
    verified_comment_free_python_example,
    verified_repository_example_code,
)

_PRESENTATION_MARKS = re.compile(r"[*_~]+")
_LEADING_LIST_MARK = re.compile(r"^(?:[-+*]|\d+[.)])\s+")
_SINGLE_COMMAND_FENCE = re.compile(
    r"(?s)^\s*```(?:bash|console|powershell|ps1|shell|sh|zsh)?\s*\n([^\n]+)\n```\s*$",
    re.IGNORECASE,
)
_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_KEY_CAPABILITY_PROVENANCE = "template.section.key_capabilities.claim:"


def _complete_claim_fact_ids(source_claim_text: str, facts: ProductFactsV2) -> set[str]:
    """Return every literal and structured fact required by one isolated claim."""

    fact_ids = set(accepted_source_claim_fact_ids(source_claim_text, facts))
    source_claims = assess_material_claims(source_claim_text)
    if len(source_claims) == 1:
        binding = complete_source_claim_fact_binding(source_claim_text, source_claims[0], facts)
        if binding is not None:
            fact_ids.update(binding.fact_ids)
    return fact_ids


def presentation_equivalence_key(value: str) -> str:
    """Normalize presentation-only decoration without weakening factual comparison."""

    without_decorations = strip_emoji_decorations(value)
    normalized = " ".join(_PRESENTATION_MARKS.sub("", without_decorations).split())
    if "\n" not in without_decorations.strip():
        normalized = _LEADING_LIST_MARK.sub("", normalized).rstrip(" .:;")
    return normalized.casefold()


def index_equivalent_candidate_claims(
    candidate_bytes: bytes,
    candidate_claims: list[ReadmeMaterialClaimAssessmentV1],
) -> dict[str, list[ReadmeMaterialClaimAssessmentV1]]:
    """Index candidate claims by their presentation-equivalence key."""

    candidates: dict[str, list[ReadmeMaterialClaimAssessmentV1]] = {}
    for claim in candidate_claims:
        text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        candidates.setdefault(presentation_equivalence_key(text), []).append(claim)
    return candidates


def fact_bound_capability_candidate_claims(
    source_claim_text: str,
    candidate_bytes: bytes,
    candidate_claims: list[ReadmeMaterialClaimAssessmentV1],
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
) -> list[ReadmeMaterialClaimAssessmentV1]:
    """Find one fact-identical canonical capability that subsumes inherited wording."""

    capability_fact_id = facts.selected_fact_ids.get("product.capabilities")
    source_fact_ids = _complete_claim_fact_ids(source_claim_text, facts)
    if capability_fact_id is None or capability_fact_id not in source_fact_ids:
        return []
    matches: list[ReadmeMaterialClaimAssessmentV1] = []
    source_discriminators = capability_discriminators(source_claim_text)
    for claim in candidate_claims:
        candidate_text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode(
            "utf-8"
        )
        if not source_discriminators.issubset(capability_discriminators(candidate_text)):
            continue
        if not semantically_repeats(source_claim_text, candidate_text, threshold=0.6):
            continue
        exact_bindings = [
            binding
            for binding in provenance
            if binding.provenance_id.startswith(_KEY_CAPABILITY_PROVENANCE)
            and binding.candidate_byte_start == claim.source_byte_start
            and binding.candidate_byte_end == claim.source_byte_end
            and capability_fact_id in binding.fact_ids
            and source_fact_ids.issubset(binding.fact_ids)
        ]
        if len(exact_bindings) == 1:
            matches.append(claim)
    return matches


def equivalent_source_claim_resolution(
    source_claim: ReadmeMaterialClaimAssessmentV1,
    source_claim_text: str,
    candidate_bytes: bytes,
    candidates: dict[str, list[ReadmeMaterialClaimAssessmentV1]],
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
) -> SourceClaimResolutionV1 | None:
    """Resolve one exact presentation-only rewrite when both claims share accepted facts."""

    equivalent = candidates.get(presentation_equivalence_key(source_claim_text), [])
    comment_free_example = False
    command_reformatted = False
    capability_reformatted = False
    source_fact_ids = _complete_claim_fact_ids(source_claim_text, facts)
    repository_example = verified_repository_example_code(source_claim_text, facts)
    command_match = _SINGLE_COMMAND_FENCE.fullmatch(source_claim_text)
    if not equivalent and command_match is not None:
        command = command_match.group(1).strip()
        candidate_pool = [claim for group in candidates.values() for claim in group]
        equivalent = [
            claim
            for claim in candidate_pool
            if command
            in {
                match.group(1).strip()
                for match in _INLINE_CODE.finditer(
                    candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
                )
            }
        ]
        command_reformatted = bool(equivalent)
    if not equivalent and repository_example and python_claim_has_comments(source_claim_text):
        verified_code = repository_example[1]
        candidate_pool = [claim for group in candidates.values() for claim in group]
        equivalent = []
        for claim in candidate_pool:
            text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
            transformed = verified_comment_free_python_example(text, verified_code)
            if (
                transformed is not None
                and transformed.strip() == text.strip()
                and not python_claim_has_comments(text)
            ):
                equivalent.append(claim)
        comment_free_example = bool(equivalent)
    if not equivalent and candidate_content_provenance:
        candidate_pool = [claim for group in candidates.values() for claim in group]
        equivalent = fact_bound_capability_candidate_claims(
            source_claim_text,
            candidate_bytes,
            candidate_pool,
            facts,
            candidate_content_provenance,
        )
        capability_reformatted = bool(equivalent)
    if len(equivalent) != 1:
        return None
    candidate_claim = equivalent[0]
    candidate_text = candidate_bytes[
        candidate_claim.source_byte_start : candidate_claim.source_byte_end
    ].decode("utf-8")
    candidate_fact_ids = set(accepted_source_claim_fact_ids(candidate_text, facts))
    provenance_ids: list[str] = []
    covered = bytearray(candidate_claim.source_byte_end - candidate_claim.source_byte_start)
    for binding in candidate_content_provenance or []:
        if (
            binding.authority_scope != "lineage_only"
            and binding.fact_ids
            and binding.candidate_byte_start < candidate_claim.source_byte_end
            and candidate_claim.source_byte_start < binding.candidate_byte_end
        ):
            candidate_fact_ids.update(binding.fact_ids)
            provenance_ids.append(binding.provenance_id)
            start = max(candidate_claim.source_byte_start, binding.candidate_byte_start)
            end = min(candidate_claim.source_byte_end, binding.candidate_byte_end)
            covered[
                start - candidate_claim.source_byte_start : end - candidate_claim.source_byte_start
            ] = b"\x01" * (end - start)
    uncovered = bytes(
        byte
        for index, byte in enumerate(
            candidate_bytes[candidate_claim.source_byte_start : candidate_claim.source_byte_end]
        )
        if not covered[index]
    )
    if provenance_ids and uncovered.strip():
        return None
    if candidate_claim.content_sha256 == source_claim.content_sha256 and not provenance_ids:
        return None
    if not candidate_fact_ids or (
        source_fact_ids and not source_fact_ids.issubset(candidate_fact_ids)
    ):
        return None
    fact_ids = sorted(candidate_fact_ids)
    return SourceClaimResolutionV1(
        claim_id=source_claim.claim_id,
        source_byte_start=source_claim.source_byte_start,
        source_byte_end=source_claim.source_byte_end,
        content_sha256=source_claim.content_sha256,
        resolution="verified_equivalence",
        fact_ids=fact_ids,
        candidate_claim_id=candidate_claim.claim_id,
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        candidate_content_sha256=candidate_claim.content_sha256,
        evidence=[
            f"source-content-sha256:{source_claim.content_sha256}",
            f"candidate-content-sha256:{candidate_claim.content_sha256}",
            *(f"candidate-provenance:{provenance_id}" for provenance_id in sorted(provenance_ids)),
            *(f"accepted-fact:{fact_id}" for fact_id in fact_ids),
        ],
        rationale=(
            "Bind this inherited capability to one canonical, fact-identical visitor statement "
            "instead of repeating the same feature in a second list."
            if capability_reformatted
            else (
                "Bind this exact comment-only Python example cleanup to the same statically "
                "verified repository example and complete candidate provenance."
            )
            if comment_free_example
            else "Bind this exact single-line command reformatted from a fenced block to one "
            "fact-bound inline command in the candidate."
            if command_reformatted
            else "Bind this exact presentation-only rewrite to one exact candidate claim with "
            "the same accepted fact set."
        ),
    )
