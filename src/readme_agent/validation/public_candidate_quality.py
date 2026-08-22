"""Deterministic, non-LLM quality gate for public README candidate prose."""

from readme_agent.validation.public_quality_contracts import (
    PUBLIC_QUALITY_CHECKS_VERSION,
    PublicQualityCategory,
    PublicQualityConfidence,
    PublicQualityCountsV1,
    PublicQualityDirection,
    PublicQualityFindingV1,
    PublicQualityLocationV1,
    PublicQualityPolarity,
    PublicQualityReportV1,
    PublicQualitySeverity,
    PublicQualitySpanV1,
)
from readme_agent.validation.public_quality_lint_checks import (
    _REUSED_LEAKAGE_RULE_IDS,
    _REUSED_MALFORMED_RULE_IDS,
)
from readme_agent.validation.public_quality_registry import (
    _CHECKS_SOURCE_HASH_AT_VERSION,
    compute_checks_source_hash,
    evaluate_public_candidate_quality,
)

__all__ = [
    "_CHECKS_SOURCE_HASH_AT_VERSION",
    "_REUSED_LEAKAGE_RULE_IDS",
    "_REUSED_MALFORMED_RULE_IDS",
    "PUBLIC_QUALITY_CHECKS_VERSION",
    "PublicQualityCategory",
    "PublicQualityConfidence",
    "PublicQualityCountsV1",
    "PublicQualityDirection",
    "PublicQualityFindingV1",
    "PublicQualityLocationV1",
    "PublicQualityPolarity",
    "PublicQualityReportV1",
    "PublicQualitySeverity",
    "PublicQualitySpanV1",
    "compute_checks_source_hash",
    "evaluate_public_candidate_quality",
]
