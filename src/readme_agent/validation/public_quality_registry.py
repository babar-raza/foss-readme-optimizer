"""Ordered public-quality check registry, evaluator, counts, and version tripwire."""

from __future__ import annotations

import hashlib
import inspect
import sys
from collections.abc import Callable

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_structure import Heading, parse_headings
from readme_agent.validation import (
    public_quality_contradiction_checks,
    public_quality_grounding_checks,
    public_quality_lint_checks,
    public_quality_semantic_common,
    public_quality_structure_checks,
)
from readme_agent.validation.public_quality_contracts import (
    PUBLIC_QUALITY_CHECKS_VERSION,
    PublicQualityCategory,
    PublicQualityCountsV1,
    PublicQualityFindingV1,
    PublicQualityReportV1,
    _content_hash,
)
from readme_agent.validation.public_quality_contradiction_checks import (
    _check_contradiction_capability_phrase,
    _check_contradiction_capability_symbol,
)
from readme_agent.validation.public_quality_grounding_checks import (
    _check_claim_grounding_negative_fact,
)
from readme_agent.validation.public_quality_lint_checks import (
    _check_empty_or_placeholder_section,
    _check_malformed_duplicate_language,
    _check_malformed_low_information_prose,
    _check_process_leakage,
)
from readme_agent.validation.public_quality_structure_checks import (
    _check_structural_detail_density,
    _check_structural_size_outlier,
)

_CHECK_SOURCE_MODULES = (
    public_quality_semantic_common,
    public_quality_grounding_checks,
    public_quality_contradiction_checks,
    public_quality_lint_checks,
    public_quality_structure_checks,
)


# ---------------------------------------------------------------------------------------------
# Check registry and entry point
# ---------------------------------------------------------------------------------------------

_CheckFn = Callable[
    [str, list[Heading], ProductFactsV2 | None, ReadmeClaimAccountabilityMapV1 | None],
    list[PublicQualityFindingV1],
]

# (check_id, category, requires_structured_evidence, function). A check with
# requires_structured_evidence=True is omitted from checks_run entirely (never run-with-zero-
# findings) when neither facts nor claim_accountability is supplied -- an honest "not evaluated",
# not a fabricated pass.
_CHECKS: tuple[tuple[str, PublicQualityCategory, bool, _CheckFn], ...] = (
    (
        "claim_grounding_negative_fact",
        "claim_grounding",
        True,
        _check_claim_grounding_negative_fact,
    ),
    (
        "contradiction_capability_symbol",
        "cross_section_contradiction",
        False,
        _check_contradiction_capability_symbol,
    ),
    (
        "contradiction_capability_phrase",
        "cross_section_contradiction",
        False,
        _check_contradiction_capability_phrase,
    ),
    ("process_leakage", "process_leakage", False, _check_process_leakage),
    (
        "malformed_low_information_prose",
        "malformed_prose",
        False,
        _check_malformed_low_information_prose,
    ),
    ("malformed_duplicate_language", "malformed_prose", False, _check_malformed_duplicate_language),
    ("empty_or_placeholder_section", "malformed_prose", False, _check_empty_or_placeholder_section),
    ("structural_size_outlier", "structural_quality", False, _check_structural_size_outlier),
    ("structural_detail_density", "structural_quality", False, _check_structural_detail_density),
)

# Forget-proofing tripwire (mirrors validation/registry.py's VALIDATION_RULESET_VERSION /
# _RULES_SOURCE_HASH_AT_VERSION convention): test_checks_source_hash_matches_recorded_version
# recomputes the live hash of every check function's source and fails loudly if it no longer
# matches this recorded value, forcing a conscious "does PUBLIC_QUALITY_CHECKS_VERSION need to
# move" decision on every detection-logic edit instead of a silent, unreviewed drift.
_CHECKS_SOURCE_HASH_AT_VERSION = "a6aa53f6810388f11e0d5f7607c8ca25ed40a4c8901ea153bd25910c32dd5d09"


def compute_checks_source_hash() -> str:
    """Hash normalized source for every registered check module and ordered registry."""

    chunks: list[str] = []
    for module in (*_CHECK_SOURCE_MODULES, sys.modules[__name__]):
        source = inspect.getsource(module).replace("\r\n", "\n").replace("\r", "\n")
        kept = [
            line for line in source.splitlines() if "_CHECKS_SOURCE_HASH_AT_VERSION" not in line
        ]
        chunks.append(f"{module.__name__}\n" + "\n".join(kept))
    return hashlib.sha256("\n---\n".join(chunks).encode("utf-8")).hexdigest()


_COUNT_FIELDS = (
    "cross_section_contradiction",
    "process_leakage",
    "malformed_prose",
    "claim_grounding",
    "structural_quality",
    "critical",
    "warning",
    "blocking",
    "advisory",
)


def _build_counts(findings: list[PublicQualityFindingV1]) -> PublicQualityCountsV1:
    tally: dict[str, int] = dict.fromkeys(_COUNT_FIELDS, 0)
    for finding in findings:
        tally[finding.category] += 1
        tally[finding.severity] += 1
        tally["blocking" if finding.blocking else "advisory"] += 1
    return PublicQualityCountsV1(**tally)


def evaluate_public_candidate_quality(
    candidate_text: str,
    *,
    facts: ProductFactsV2 | None = None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None = None,
) -> PublicQualityReportV1:
    """Deterministically evaluate public README candidate prose for known defect classes.

    Pure function: identical ``candidate_text``/``facts``/``claim_accountability`` inputs always
    produce a byte-identical serialized report, including ``report_hash``.
    """

    candidate_sha256 = sha256_hex(candidate_text)
    headings = parse_headings(candidate_text)
    checks_run: list[str] = []
    findings: list[PublicQualityFindingV1] = []
    has_structured_evidence = facts is not None or claim_accountability is not None
    for check_id, _category, requires_structured_evidence, check_fn in _CHECKS:
        if requires_structured_evidence and not has_structured_evidence:
            continue
        checks_run.append(check_id)
        findings.extend(check_fn(candidate_text, headings, facts, claim_accountability))
    findings.sort(
        key=lambda finding: (
            finding.locations[0].section_path,
            finding.locations[0].span.start,
            finding.locations[0].span.end,
            finding.check_id,
        )
    )
    counts = _build_counts(findings)
    checks_run_sorted = tuple(sorted(checks_run))
    findings_tuple = tuple(findings)

    draft = PublicQualityReportV1.model_construct(
        schema_version=1,
        checks_version=PUBLIC_QUALITY_CHECKS_VERSION,
        candidate_sha256=candidate_sha256,
        checks_run=checks_run_sorted,
        findings=findings_tuple,
        counts=counts,
        report_hash="0" * 64,
    )
    report_hash = _content_hash(draft.model_dump(mode="json", exclude={"report_hash"}))
    return PublicQualityReportV1(
        schema_version=1,
        checks_version=PUBLIC_QUALITY_CHECKS_VERSION,
        candidate_sha256=candidate_sha256,
        checks_run=checks_run_sorted,
        findings=findings_tuple,
        counts=counts,
        report_hash=report_hash,
    )
