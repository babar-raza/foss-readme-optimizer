"""Classify fact-authorized source preservation and correction candidates."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.source_claim_contradiction import contradicted_source_claim_fact_ids
from readme_agent.readme.source_claim_fact_binding import (
    accepted_source_claim_fact_ids,
    complete_source_claim_fact_binding,
    python_claim_has_comments,
    verified_comment_free_python_example,
    verified_example_code,
    verified_repository_example_code,
)


@dataclass(frozen=True)
class SourceClaimAssurance:
    preserve_ranges: list[tuple[int, int]]
    correction_ranges: list[tuple[int, int]]
    fact_authorized_claim_count: int
    correction_candidate_count: int


def build_source_claim_assurance(
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
) -> SourceClaimAssurance:
    """Separate fact-authorized preservation from unsupported correction candidates."""

    source = source_text.encode("utf-8")
    preserve: list[tuple[int, int]] = []
    correction: list[tuple[int, int]] = []
    for claim in assessment.material_claims:
        coordinates = (claim.source_byte_start, claim.source_byte_end)
        if claim.disposition != "preserve":
            continue
        text = source[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        binding = complete_source_claim_fact_binding(source_text, claim, facts)
        verified_example = facts.selected_fact("example.minimal")
        verified_code = verified_example_code(verified_example.value)
        repository_example = verified_repository_example_code(text, facts)
        contradiction_fact_ids = contradicted_source_claim_fact_ids(source_text, claim, facts)
        comment_correction = bool(
            (
                (verified_code and verified_comment_free_python_example(text, verified_code))
                or repository_example
            )
            and python_claim_has_comments(text)
        )
        target = (
            preserve
            if binding is not None and not comment_correction and not contradiction_fact_ids
            else correction
        )
        target.append(coordinates)
    return SourceClaimAssurance(
        preserve_ranges=sorted(preserve),
        correction_ranges=sorted(correction),
        fact_authorized_claim_count=len(preserve),
        correction_candidate_count=len(correction),
    )


__all__ = [
    "SourceClaimAssurance",
    "accepted_source_claim_fact_ids",
    "build_source_claim_assurance",
    "verified_comment_free_python_example",
]
