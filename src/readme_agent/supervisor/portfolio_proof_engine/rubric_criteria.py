"""The 30-criterion evidence table for
`plans/investigations/owner_audit/aspose_candidate_rubric/RUBRIC_30.md`, plus the six hard
disqualifiers. See `rubric.py`'s module docstring for the full grounding/calibration note --
this module holds only the declarative table and its evidence-interpretation helpers; `rubric.py`
holds the scoring/acceptance orchestration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import EvidenceBundleV1

EvaluatorType = Literal[
    "deterministic_check",
    "source_claim_accountability",
    "disposition_ledger",
    "k3_knowledge_to_byte",
    "package_dependency_example_verification",
    "factual_review",
    "visitor_quality_review",
    "link_format_structure",
    "reconciliation",
    "noop_reproducibility",
]


class RubricCriterionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: int = Field(ge=1, le=30)
    category: Literal["A", "B", "C", "D", "E"]
    max_points: Literal[1] = 1
    awarded_points: Literal[0, 1]
    evaluator_type: EvaluatorType
    evidence_artifact: str
    evidence_key: str
    failure_reason: str | None = None


def _checks(bundle: EvidenceBundleV1) -> dict:
    validation = bundle.deterministic_validation or {}
    return validation.get("checks") or {}


def _deterministic_valid(bundle: EvidenceBundleV1) -> bool:
    validation = bundle.deterministic_validation
    if validation is None:
        return False
    return validation.get("valid") is True and not validation.get("errors")


def _rule_check(bundle: EvidenceBundleV1, rule_name: str) -> bool | None:
    checks = _checks(bundle)
    if rule_name not in checks:
        return None
    return bool(checks[rule_name]) and _deterministic_valid(bundle)


def _review_result(record: dict | None) -> dict | None:
    """`RoleReviewRecordV1`-shaped records may nest the typed verdict under `result` (the
    reducer's own wrapping) or carry it at the top level -- both are checked defensively."""

    if not record:
        return None
    nested = record.get("result")
    return nested if isinstance(nested, dict) else record


def _review_accepts(record: dict | None) -> bool | None:
    result = _review_result(record)
    if result is None or "verdict" not in result:
        return None
    return result.get("verdict") == "ACCEPT"


def _first_present(source: dict, *keys: str) -> object | None:
    """First key that actually exists, distinguishing a valid `0`/`False` value from an absent
    key -- `dict.get(a) or dict.get(b)` incorrectly treats a genuine `0` count as "try the next
    key," silently losing a clean (zero-count) signal."""

    for key in keys:
        if key in source:
            return source[key]
    return None


def _reconciliation_clean(bundle: EvidenceBundleV1) -> bool | None:
    reconciliation = bundle.reconciliation
    if reconciliation is None:
        return None
    unresolved = _first_present(reconciliation, "unresolved", "unresolved_count")
    errors = _first_present(reconciliation, "errors", "error_count")
    if unresolved is None and errors is None:
        return None
    return not unresolved and not errors


def knowledge_application_final(bundle: EvidenceBundleV1) -> bool | None:
    report = bundle.knowledge_application
    if report is None:
        return None
    if report.get("final_dispositions") is None:
        return None
    # A K3 artifact that only ever exists in "provisional" status was written before any
    # candidate rendered -- it cannot ground a post-render byte-accountability criterion.
    return report.get("status") == "final"


def _criterion(
    criterion_id: int,
    category: Literal["A", "B", "C", "D", "E"],
    evaluator_type: EvaluatorType,
    evidence_artifact: str,
    evidence_key: str,
    outcome: bool | None,
) -> RubricCriterionResultV1:
    if outcome is True:
        return RubricCriterionResultV1(
            criterion_id=criterion_id,
            category=category,
            awarded_points=1,
            evaluator_type=evaluator_type,
            evidence_artifact=evidence_artifact,
            evidence_key=evidence_key,
        )
    reason = (
        f"evidence key {evidence_key!r} not found in {evidence_artifact}"
        if outcome is None
        else f"{evidence_key} present but did not satisfy the criterion"
    )
    return RubricCriterionResultV1(
        criterion_id=criterion_id,
        category=category,
        awarded_points=0,
        evaluator_type=evaluator_type,
        evidence_artifact=evidence_artifact,
        evidence_key=evidence_key,
        failure_reason=reason[:500],
    )


# One (criterion_id, category, evaluator_type, evidence_artifact, evidence_key, check) row per
# RUBRIC_30.md criterion -- `check` always takes the bundle and returns True/False/None.
_CriterionSpec = tuple[
    int,
    Literal["A", "B", "C", "D", "E"],
    EvaluatorType,
    str,
    str,
    Callable[[EvidenceBundleV1], bool | None],
]

_CLAIM_MAP = "candidate/claim-map.json"
_DET = "review/deterministic-validation.json"
_RECON = "candidate/readme-reconciliation.json"
_VISITOR = "review/blind-quality-review.json"
_FACTUAL = "review/factual-plan-review.json"


def _both_reviews_accept(bundle: EvidenceBundleV1) -> bool | None:
    factual = _review_accepts(bundle.factual_review)
    visitor = _review_accepts(bundle.visitor_review)
    if factual is None or visitor is None:
        return None
    return factual and visitor


_CRITERIA: tuple[_CriterionSpec, ...] = (
    (
        1,
        "A",
        "source_claim_accountability",
        _CLAIM_MAP,
        "claim_map present + deterministic valid",
        lambda b: (
            (bool(b.claim_map) and _deterministic_valid(b)) if b.claim_map is not None else None
        ),
    ),
    (
        2,
        "A",
        "package_dependency_example_verification",
        "facts/product-facts.json",
        "facts present (installation truth)",
        lambda b: bool(b.facts) if b.facts is not None else None,
    ),
    (
        3,
        "A",
        "package_dependency_example_verification",
        "facts/product-facts.json",
        "facts present (dependency truth)",
        lambda b: bool(b.facts) if b.facts is not None else None,
    ),
    (
        4,
        "A",
        "deterministic_check",
        _DET,
        "checks.referential_integrity (API surface truth)",
        lambda b: _rule_check(b, "referential_integrity"),
    ),
    (
        5,
        "A",
        "package_dependency_example_verification",
        "candidate/check-coverage.json",
        "check_coverage present",
        lambda b: bool(b.check_coverage) if b.check_coverage is not None else None,
    ),
    (
        6,
        "A",
        "deterministic_check",
        _DET,
        "checks.referential_integrity (API-reference integrity)",
        lambda b: _rule_check(b, "referential_integrity"),
    ),
    (
        7,
        "A",
        "deterministic_check",
        _DET,
        "valid + no errors (limitations honesty)",
        lambda b: _deterministic_valid(b) if b.deterministic_validation is not None else None,
    ),
    (
        8,
        "A",
        "link_format_structure",
        _DET,
        "checks.link_whitelist",
        lambda b: _rule_check(b, "link_whitelist"),
    ),
    (
        9,
        "B",
        "reconciliation",
        _RECON,
        "unresolved/errors == 0 (content-unit accounting)",
        _reconciliation_clean,
    ),
    (
        10,
        "B",
        "reconciliation",
        _RECON,
        "unresolved/errors == 0 (structural accounting)",
        _reconciliation_clean,
    ),
    (
        11,
        "B",
        "reconciliation",
        _RECON,
        "unresolved/errors == 0 (code-example accounting)",
        _reconciliation_clean,
    ),
    (
        12,
        "B",
        "reconciliation",
        _RECON,
        "unresolved/errors == 0 (badge/media accounting)",
        _reconciliation_clean,
    ),
    (
        13,
        "B",
        "reconciliation",
        _RECON,
        "unresolved/errors == 0 (reconciliation integrity)",
        _reconciliation_clean,
    ),
    (
        14,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "verdict == ACCEPT (immediate orientation)",
        lambda b: _review_accepts(b.visitor_review),
    ),
    (
        15,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "verdict == ACCEPT (capability overview)",
        lambda b: _review_accepts(b.visitor_review),
    ),
    (
        16,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "verdict == ACCEPT (concrete capabilities)",
        lambda b: _review_accepts(b.visitor_review),
    ),
    (
        17,
        "C",
        "deterministic_check",
        _DET,
        "checks.product_first_opening (actionable installation)",
        lambda b: _rule_check(b, "product_first_opening"),
    ),
    (
        18,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "verdict == ACCEPT (minimal successful start)",
        lambda b: _review_accepts(b.visitor_review),
    ),
    (
        19,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "verdict == ACCEPT (proportionate examples)",
        lambda b: _review_accepts(b.visitor_review),
    ),
    (
        20,
        "C",
        "deterministic_check",
        _DET,
        "valid + no errors (navigable reference/resources)",
        lambda b: _deterministic_valid(b) if b.deterministic_validation is not None else None,
    ),
    (
        21,
        "D",
        "visitor_quality_review",
        _VISITOR,
        "verdict == ACCEPT (information architecture)",
        lambda b: _review_accepts(b.visitor_review),
    ),
    (
        22,
        "D",
        "deterministic_check",
        _DET,
        "checks.prohibited_terms (clear public prose)",
        lambda b: _rule_check(b, "prohibited_terms"),
    ),
    (
        23,
        "D",
        "deterministic_check",
        _DET,
        "checks.commercial_mention_discipline (verified trust signals)",
        lambda b: _rule_check(b, "commercial_mention_discipline"),
    ),
    (
        24,
        "D",
        "link_format_structure",
        _DET,
        "checks.link_whitelist (render/link integrity)",
        lambda b: _rule_check(b, "link_whitelist"),
    ),
    (
        25,
        "D",
        "deterministic_check",
        _DET,
        "checks.word_count (proportionate depth)",
        lambda b: _rule_check(b, "word_count"),
    ),
    (
        26,
        "E",
        "noop_reproducibility",
        "manifest.json",
        "facts_hash + source_revision present (sealed inputs)",
        lambda b: (
            bool(b.manifest and b.manifest.get("facts_hash") and b.source_revision)
            if b.manifest is not None
            else None
        ),
    ),
    (
        27,
        "E",
        "noop_reproducibility",
        "manifest.json / candidate hash",
        "candidate_hash bound and non-empty",
        lambda b: bool(b.candidate_hash) if b.manifest is not None else None,
    ),
    (
        28,
        "E",
        "deterministic_check",
        _DET,
        "valid + no errors (complete fail-closed checks)",
        lambda b: _deterministic_valid(b) if b.deterministic_validation is not None else None,
    ),
    (
        29,
        "E",
        "factual_review",
        f"{_FACTUAL} + {_VISITOR}",
        "both verdicts == ACCEPT",
        _both_reviews_accept,
    ),
    (
        30,
        "E",
        "noop_reproducibility",
        "review/no-op-proof.json",
        "no_op_proof present",
        lambda b: bool(b.no_op_proof) if b.no_op_proof is not None else None,
    ),
)


def evaluate_all_criteria(bundle: EvidenceBundleV1) -> tuple[RubricCriterionResultV1, ...]:
    return tuple(
        _criterion(
            criterion_id, category, evaluator_type, evidence_artifact, evidence_key, check(bundle)
        )
        for criterion_id, category, evaluator_type, evidence_artifact, evidence_key, check in (
            _CRITERIA
        )
    )


def evaluate_hard_disqualifiers(bundle: EvidenceBundleV1) -> tuple[str, ...]:
    """The six RUBRIC_30.md hard disqualifiers, checked independently of the numeric subtotal --
    a 30/30 numeric score with any one of these present is still rejected."""

    disqualifiers: list[str] = []
    validation = bundle.deterministic_validation
    if validation is not None and validation.get("errors"):
        disqualifiers.append(
            "a blocking check failed/errored (deterministic-validation.json carries errors)"
        )
    if validation is not None and validation.get("valid") is not True:
        disqualifiers.append("deterministic validation did not accept the candidate")
    if bundle.manifest is not None and bundle.candidate_hash:
        manifest_candidate_hash = bundle.manifest.get("candidate_hash")
        if manifest_candidate_hash and manifest_candidate_hash != bundle.candidate_hash:
            disqualifiers.append(
                "candidate bytes do not match the reviewed SHA "
                "(manifest.json candidate_hash mismatch)"
            )
    if knowledge_application_final(bundle) is False:
        disqualifiers.append("K3 knowledge-application report is not yet final for this candidate")
    if _review_accepts(bundle.factual_review) is False:
        disqualifiers.append("factual review did not accept the candidate")
    if _review_accepts(bundle.visitor_review) is False:
        disqualifiers.append("visitor-quality review did not accept the candidate")
    return tuple(disqualifiers)
