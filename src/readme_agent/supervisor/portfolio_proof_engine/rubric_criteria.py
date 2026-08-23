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
from readme_agent.supervisor.portfolio_proof_engine.rubric_evidence import (
    accepted_fact,
    accepted_facts,
    api_truth,
    checks_complete,
    claim_map_complete,
    current_check,
    deterministic_accepts,
    exact_byte_binding,
    example_truth,
    reconciliation_complete,
    reconciliation_integrity,
    repeatable_acceptance,
    review_accepts,
    review_supports,
    sealed_inputs,
)

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
    return deterministic_accepts(bundle)


def _rule_check(bundle: EvidenceBundleV1, rule_name: str) -> bool | None:
    return current_check(bundle, rule_name)


def _review_result(record: dict | None) -> dict | None:
    """`RoleReviewRecordV1`-shaped records may nest the typed verdict under `result` (the
    reducer's own wrapping) or carry it at the top level -- both are checked defensively."""

    if not record:
        return None
    nested = record.get("result")
    return nested if isinstance(nested, dict) else record


def _review_accepts(record: dict | None) -> bool | None:
    return review_accepts(record)


def _first_present(source: dict, *keys: str) -> object | None:
    """First key that actually exists, distinguishing a valid `0`/`False` value from an absent
    key -- `dict.get(a) or dict.get(b)` incorrectly treats a genuine `0` count as "try the next
    key," silently losing a clean (zero-count) signal."""

    for key in keys:
        if key in source:
            return source[key]
    return None


def _reconciliation_clean(bundle: EvidenceBundleV1) -> bool | None:
    return reconciliation_integrity(bundle)


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


def _all_known(*outcomes: bool | None) -> bool | None:
    if any(outcome is None for outcome in outcomes):
        return None
    return all(outcomes)


_CRITERIA: tuple[_CriterionSpec, ...] = (
    (
        1,
        "A",
        "source_claim_accountability",
        _CLAIM_MAP,
        "all candidate claims bind to accepted selected facts and exact candidate spans",
        claim_map_complete,
    ),
    (
        2,
        "A",
        "package_dependency_example_verification",
        "facts/product-facts.json",
        "accepted installation coordinates and verified acquisition receipt",
        lambda b: accepted_facts(
            b, ("installation.coordinates", "installation.verified_acquisition")
        ),
    ),
    (
        3,
        "A",
        "package_dependency_example_verification",
        "facts/product-facts.json",
        "accepted dependency snapshot",
        lambda b: accepted_fact(b, "aspose.dependency_snapshot"),
    ),
    (
        4,
        "A",
        "deterministic_check",
        _DET,
        "accepted API inventory + implementation-evidence and accountability checks",
        api_truth,
    ),
    (
        5,
        "A",
        "package_dependency_example_verification",
        "candidate/check-coverage.json",
        "verified example fact + example assurance checks",
        example_truth,
    ),
    (
        6,
        "A",
        "deterministic_check",
        _DET,
        "accepted API inventory + factual API-reference review",
        lambda b: _all_known(
            api_truth(b), review_supports(b.factual_review, sections=("api-reference",))
        ),
    ),
    (
        7,
        "A",
        "deterministic_check",
        _DET,
        "accepted limitations fact + visible limitations + factual review",
        lambda b: _all_known(
            accepted_fact(b, "product.limitations"),
            current_check(b, "verified_limitations_present"),
            review_supports(b.factual_review, sections=("scope-and-limitations",)),
        ),
    ),
    (
        8,
        "A",
        "link_format_structure",
        _DET,
        "accepted links/formats/license + contextual-link and presentation checks",
        lambda b: _all_known(
            accepted_facts(b, ("documentation.links", "product.formats", "product.license")),
            current_check(b, "contextual_links"),
            current_check(b, "presentation_lint"),
        ),
    ),
    (
        9,
        "B",
        "reconciliation",
        _RECON,
        "complete byte-bound content-unit reconciliation",
        lambda b: reconciliation_complete(b, "content"),
    ),
    (
        10,
        "B",
        "reconciliation",
        _RECON,
        "complete byte-bound structural-unit reconciliation",
        lambda b: reconciliation_complete(b, "structure"),
    ),
    (
        11,
        "B",
        "reconciliation",
        _RECON,
        "complete byte-bound code-fence reconciliation",
        lambda b: reconciliation_complete(b, "code"),
    ),
    (
        12,
        "B",
        "reconciliation",
        _RECON,
        "complete byte-bound badge/media reconciliation",
        lambda b: reconciliation_complete(b, "media"),
    ),
    (
        13,
        "B",
        "reconciliation",
        _RECON,
        "complete source partition + destinations/evidence for every disposition",
        reconciliation_integrity,
    ),
    (
        14,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "visitor ACCEPT with opening-span support",
        lambda b: review_supports(b.visitor_review, sections=("front-matter",)),
    ),
    (
        15,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "visitor ACCEPT with at-a-glance support",
        lambda b: review_supports(b.visitor_review, sections=("at-a-glance",)),
    ),
    (
        16,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "visitor ACCEPT with key-capabilities support",
        lambda b: review_supports(b.visitor_review, sections=("key-capabilities",)),
    ),
    (
        17,
        "C",
        "deterministic_check",
        _DET,
        "installation truth + visitor installation support",
        lambda b: _all_known(
            accepted_facts(b, ("installation.coordinates", "installation.verified_acquisition")),
            review_supports(b.visitor_review, sections=("installation",)),
        ),
    ),
    (
        18,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "verified example + visitor quick-start support",
        lambda b: _all_known(
            example_truth(b), review_supports(b.visitor_review, sections=("quick-start",))
        ),
    ),
    (
        19,
        "C",
        "visitor_quality_review",
        _VISITOR,
        "visitor ACCEPT with additional-example support",
        lambda b: review_supports(b.visitor_review, sections=("additional-examples",)),
    ),
    (
        20,
        "C",
        "deterministic_check",
        _DET,
        "visitor support across navigation, API, resources, development, and license",
        lambda b: review_supports(
            b.visitor_review,
            sections=(
                "navigation",
                "api-reference",
                "documentation-resources",
                "development-and-testing",
                "license",
            ),
        ),
    ),
    (
        21,
        "D",
        "visitor_quality_review",
        _VISITOR,
        "visitor ACCEPT with navigation and section hierarchy support",
        lambda b: review_supports(b.visitor_review, sections=("navigation", "front-matter")),
    ),
    (
        22,
        "D",
        "deterministic_check",
        _DET,
        "no comments + presentation/public-quality checks + visitor prose support",
        lambda b: _all_known(
            current_check(b, "candidate_has_no_comments"),
            current_check(b, "presentation_lint"),
            current_check(b, "public_candidate_quality"),
            review_supports(b.visitor_review, sections=("front-matter",)),
        ),
    ),
    (
        23,
        "D",
        "deterministic_check",
        _DET,
        "accepted license + verified header visuals + visitor license support",
        lambda b: _all_known(
            accepted_fact(b, "product.license"),
            current_check(b, "header_visuals"),
            review_supports(b.visitor_review, sections=("license",)),
        ),
    ),
    (
        24,
        "D",
        "link_format_structure",
        _DET,
        "official Mermaid/render result + link/presentation checks + visitor integrity support",
        lambda b: _all_known(
            current_check(b, "header_visuals"),
            current_check(b, "contextual_links"),
            current_check(b, "presentation_lint"),
            review_supports(b.visitor_review, sections=("at-a-glance",)),
        ),
    ),
    (
        25,
        "D",
        "deterministic_check",
        _DET,
        "visitor ACCEPT with product-specific coverage across the reader path",
        lambda b: review_supports(
            b.visitor_review,
            sections=(
                "front-matter",
                "key-capabilities",
                "installation",
                "quick-start",
                "api-reference",
                "documentation-resources",
                "scope-and-limitations",
            ),
        ),
    ),
    (
        26,
        "E",
        "noop_reproducibility",
        "manifest.json",
        "snapshot, README, facts, prompts, and component contract hashes agree",
        sealed_inputs,
    ),
    (
        27,
        "E",
        "noop_reproducibility",
        "manifest.json / candidate hash",
        "candidate bytes equal manifest, claim-map, and both review hashes",
        exact_byte_binding,
    ),
    (
        28,
        "E",
        "deterministic_check",
        _DET,
        "deterministic accept + every classified blocking check ran and passed",
        lambda b: _all_known(deterministic_accepts(b), checks_complete(b)),
    ),
    (
        29,
        "E",
        "factual_review",
        f"{_FACTUAL} + {_VISITOR}",
        "both verdicts == ACCEPT",
        lambda b: _all_known(_both_reviews_accept(b), claim_map_complete(b)),
    ),
    (
        30,
        "E",
        "noop_reproducibility",
        "review/no-op-proof.json",
        "full no-op proof with exact zero-provider accounting and acceptance binding",
        repeatable_acceptance,
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
    if validation is not None and not deterministic_accepts(bundle):
        disqualifiers.append("deterministic validation did not accept the candidate")
    if bundle.check_coverage is not None and checks_complete(bundle) is not True:
        disqualifiers.append("a classified blocking check failed, skipped, or errored")
    if bundle.manifest is not None and bundle.candidate_hash:
        manifest_candidate_hash = bundle.manifest.get("candidate_hash")
        if manifest_candidate_hash and manifest_candidate_hash != bundle.candidate_hash:
            disqualifiers.append(
                "candidate bytes do not match the reviewed SHA "
                "(manifest.json candidate_hash mismatch)"
            )
    if bundle.candidate_readme is not None and exact_byte_binding(bundle) is not True:
        disqualifiers.append("candidate bytes do not match all candidate-bound review artifacts")
    if bundle.reconciliation is not None and reconciliation_integrity(bundle) is not True:
        disqualifiers.append("source README reconciliation is incomplete or lacks evidence")
    if knowledge_application_final(bundle) is False:
        disqualifiers.append("K3 knowledge-application report is not yet final for this candidate")
    if _review_accepts(bundle.factual_review) is False:
        disqualifiers.append("factual review did not accept the candidate")
    if _review_accepts(bundle.visitor_review) is False:
        disqualifiers.append("visitor-quality review did not accept the candidate")
    return tuple(disqualifiers)
