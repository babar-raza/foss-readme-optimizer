"""Match presentation-equivalent inherited and candidate claims."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
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
_CAPABILITY_COORDINATE_FIELDS = {
    "api.public_surface",
    "installation.capability_dependencies",
    "installation.optional_extras",
    "product.capabilities",
    "product.compatibility",
    "product.formats",
    "product.limitations",
    "product.problems_solved",
    "repository.implementation_components",
}


def _capability_equivalence_fact_ids(
    fact_ids: set[str],
    facts: ProductFactsV2,
) -> set[str]:
    """Keep the accepted fields that carry capability meaning across rewrites."""

    return {
        fact_id for fact_id in fact_ids if facts.fact_by_id(fact_id).field != "product.identity"
    }


def _complete_claim_fact_binding(
    source_claim_text: str,
    facts: ProductFactsV2,
) -> tuple[set[str], set[StructuredFactCoordinateV1]]:
    """Return every accepted fact and exact coordinate for one isolated claim."""

    fact_ids = set(accepted_source_claim_fact_ids(source_claim_text, facts))
    coordinates: set[StructuredFactCoordinateV1] = set()
    source_claims = assess_material_claims(source_claim_text)
    if len(source_claims) == 1:
        binding = complete_source_claim_fact_binding(source_claim_text, source_claims[0], facts)
        if binding is not None:
            fact_ids.update(binding.fact_ids)
            coordinates.update(binding.fact_coordinates)
    fact_ids.update(coordinate.fact_id for coordinate in coordinates)
    return fact_ids, coordinates


def _coordinate_keys(
    coordinates: set[StructuredFactCoordinateV1],
) -> set[tuple[str, str, str]]:
    return {(item.fact_id, item.path, item.value_sha256) for item in coordinates}


def _coordinates_cover(
    required: set[StructuredFactCoordinateV1],
    provided: set[StructuredFactCoordinateV1],
) -> bool:
    """Require exact coordinate identity, not only a shared aggregate fact ID."""

    return _coordinate_keys(required).issubset(_coordinate_keys(provided))


def _coordinates_complete_for_required_facts(
    fact_ids: set[str],
    coordinates: set[StructuredFactCoordinateV1],
    facts: ProductFactsV2,
) -> bool:
    coordinate_fact_ids = {coordinate.fact_id for coordinate in coordinates}
    return all(
        facts.fact_by_id(fact_id).field not in _CAPABILITY_COORDINATE_FIELDS
        or fact_id in coordinate_fact_ids
        for fact_id in fact_ids
    )


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
    implementation_fact_id = facts.selected_fact_ids.get("repository.implementation_components")
    source_fact_ids, source_coordinates = _complete_claim_fact_binding(source_claim_text, facts)
    if not ({capability_fact_id, implementation_fact_id} - {None}).intersection(source_fact_ids):
        return []
    required_source_fact_ids = _capability_equivalence_fact_ids(source_fact_ids, facts)
    source_coordinate_fact_ids = {coordinate.fact_id for coordinate in source_coordinates}
    required_source_fact_ids = {
        fact_id
        for fact_id in required_source_fact_ids
        if facts.fact_by_id(fact_id).field not in _CAPABILITY_COORDINATE_FIELDS
        or fact_id in source_coordinate_fact_ids
    }
    required_source_coordinates = {
        coordinate
        for coordinate in source_coordinates
        if coordinate.fact_id in required_source_fact_ids
    }
    if not _coordinates_complete_for_required_facts(
        required_source_fact_ids,
        required_source_coordinates,
        facts,
    ):
        return []
    matches: list[ReadmeMaterialClaimAssessmentV1] = []
    source_discriminators = capability_discriminators(source_claim_text)
    capability_bindings_by_range: dict[
        tuple[int, int],
        list[CandidateContentProvenanceV1],
    ] = {}
    for binding in provenance:
        if binding.provenance_id.startswith(_KEY_CAPABILITY_PROVENANCE) and (
            capability_fact_id in binding.fact_ids or implementation_fact_id in binding.fact_ids
        ):
            capability_bindings_by_range.setdefault(
                (binding.candidate_byte_start, binding.candidate_byte_end),
                [],
            ).append(binding)
    for claim in candidate_claims:
        range_bindings = capability_bindings_by_range.get(
            (claim.source_byte_start, claim.source_byte_end),
            [],
        )
        if not range_bindings:
            continue
        candidate_text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode(
            "utf-8"
        )
        candidate_fact_ids, candidate_coordinates = _complete_claim_fact_binding(
            candidate_text,
            facts,
        )
        structured_match = bool(required_source_coordinates) and _coordinates_cover(
            required_source_coordinates,
            candidate_coordinates,
        )
        if not structured_match and not source_discriminators.issubset(
            capability_discriminators(candidate_text)
        ):
            continue
        if not structured_match and not semantically_repeats(
            source_claim_text,
            candidate_text,
            threshold=0.6,
        ):
            continue
        exact_bindings = [
            binding
            for binding in range_bindings
            if required_source_fact_ids.issubset(set(binding.fact_ids) | candidate_fact_ids)
            and _coordinates_cover(
                required_source_coordinates,
                set(binding.fact_coordinates) | candidate_coordinates,
            )
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
    source_fact_ids, source_coordinates = _complete_claim_fact_binding(source_claim_text, facts)
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
    candidate_fact_ids, direct_candidate_coordinates = _complete_claim_fact_binding(
        candidate_text,
        facts,
    )
    candidate_coordinates: set[StructuredFactCoordinateV1] = (
        set(direct_candidate_coordinates) if not candidate_content_provenance else set()
    )
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
            candidate_coordinates.update(binding.fact_coordinates)
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
    required_source_fact_ids = (
        _capability_equivalence_fact_ids(source_fact_ids, facts)
        if capability_reformatted
        else source_fact_ids
    )
    required_source_coordinates = (
        {
            coordinate
            for coordinate in source_coordinates
            if coordinate.fact_id in required_source_fact_ids
        }
        if capability_reformatted
        else source_coordinates
    )
    if not candidate_fact_ids or (
        required_source_fact_ids and not required_source_fact_ids.issubset(candidate_fact_ids)
    ):
        return None
    if not _coordinates_complete_for_required_facts(
        required_source_fact_ids,
        required_source_coordinates,
        facts,
    ) or not _coordinates_cover(required_source_coordinates, candidate_coordinates):
        return None
    # An equivalence replaces the inherited claim, so its fact set must be the
    # exact accepted subset expressed by that source claim. The canonical row
    # may carry additional independently accountable API or audience facts;
    # attributing those extras back to the narrower source claim makes a valid
    # merge fail its own source-subset check.
    fact_ids = sorted(required_source_fact_ids if capability_reformatted else candidate_fact_ids)
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
            *(
                f"accepted-coordinate:{coordinate.fact_id}:{coordinate.path}:"
                f"{coordinate.value_sha256}"
                for coordinate in sorted(
                    candidate_coordinates,
                    key=lambda item: (item.fact_id, item.path, item.value_sha256),
                )
            ),
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
