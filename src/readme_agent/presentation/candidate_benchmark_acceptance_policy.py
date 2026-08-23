"""Deterministic policy inputs for candidate benchmark acceptance."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from readme_agent.validation.public_quality_contracts import PublicQualityCategory

REQUIRED_DETERMINISTIC_CHECK_IDS = frozenset({"numeric_list_consistency"})

_DIMENSION_QUALITY_CATEGORIES: dict[str, frozenset[PublicQualityCategory]] = {
    "information_coverage": frozenset({"claim_grounding", "cross_section_contradiction"}),
    "product_specificity": frozenset({"claim_grounding", "cross_section_contradiction"}),
    "structure_and_navigation": frozenset({"structural_quality", "malformed_prose"}),
    "branding_and_visuals": frozenset({"structural_quality"}),
    "capability_depth": frozenset(
        {"claim_grounding", "cross_section_contradiction", "structural_quality"}
    ),
    "installation_and_dependencies": frozenset({"claim_grounding", "malformed_prose"}),
    "source_derived_examples": frozenset({"claim_grounding", "malformed_prose"}),
    "api_reference_depth": frozenset({"structural_quality", "malformed_prose"}),
    "documentation_and_resources": frozenset({"malformed_prose", "structural_quality"}),
    "limitations": frozenset({"malformed_prose", "claim_grounding"}),
    "development_and_testing": frozenset({"process_leakage", "malformed_prose"}),
    "licensing": frozenset({"claim_grounding"}),
    "inherited_content_accountability": frozenset(
        {"malformed_prose", "cross_section_contradiction"}
    ),
    "public_tone_and_process_hygiene": frozenset({"process_leakage"}),
}

_SIMILARITY_SEQUENCE_THRESHOLD = 0.75
_SIMILARITY_JACCARD_THRESHOLD = 0.6
_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def quality_categories_for_dimension(dimension_id: str) -> frozenset[PublicQualityCategory]:
    """Return deterministic finding categories that can fail one dimension."""

    return _DIMENSION_QUALITY_CATEGORIES.get(dimension_id, frozenset())


def suspicious_benchmark_overlap(
    candidate_markdown: str, reference_excerpts: tuple[str, ...]
) -> tuple[str, ...]:
    """Return copy-risk disqualifiers only when both similarity signals cross threshold."""

    disqualifiers: list[str] = []
    candidate_words = set(_WORD_PATTERN.findall(candidate_markdown.casefold()))
    for index, excerpt in enumerate(reference_excerpts):
        sequence_ratio = SequenceMatcher(None, candidate_markdown, excerpt).ratio()
        excerpt_words = set(_WORD_PATTERN.findall(excerpt.casefold()))
        union = candidate_words | excerpt_words
        jaccard_ratio = len(candidate_words & excerpt_words) / len(union) if union else 0.0
        if (
            sequence_ratio >= _SIMILARITY_SEQUENCE_THRESHOLD
            and jaccard_ratio >= _SIMILARITY_JACCARD_THRESHOLD
        ):
            disqualifiers.append(
                f"suspicious_benchmark_prose_overlap: reference_excerpts[{index}] "
                f"sequence_ratio={sequence_ratio:.2f} jaccard_ratio={jaccard_ratio:.2f}"
            )
    return tuple(disqualifiers)


__all__ = [
    "REQUIRED_DETERMINISTIC_CHECK_IDS",
    "quality_categories_for_dimension",
    "suspicious_benchmark_overlap",
]
