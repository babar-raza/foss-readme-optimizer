"""Executable evidence-to-score mapping for
`plans/investigations/owner_audit/aspose_candidate_rubric/RUBRIC_30.md` -- the 30-point rubric
itself is never edited or reinterpreted here, only implemented.

Every criterion (`rubric_criteria.py`) reads `EvidenceBundleV1` (raw JSON already written by the
real pipeline -- `evidence_bundle.py`) and returns 0 unless its named evidence key is present and
shows the required condition; a missing artifact or missing key is "not proven," never a guessed
pass. No criterion ever asks an LLM to judge its own prose -- criteria 14-25 (reader utility,
presentation quality) source their subjective half exclusively from `visitor_review` (the
independent "blind-quality" review role, `specialists/readme_review_roles.py
::BlindQualityReviewResultV1`), which is itself an LLM verdict but one produced by a role
explicitly walled off from composition (a different actor, a different prompt, grounded findings
only) -- never the composing/authoring model scoring itself.

Ten of the deterministic `checks` keys `rubric_criteria.py` reads (`word_count`,
`prohibited_terms`, `link_whitelist`, `change_boundary`, `talking_points`,
`referential_integrity`, `idempotency`, `prominence`, `product_first_opening`,
`commercial_mention_discipline`) are the real, confirmed rule names from
`validation/registry.py::RULES` -- `DocumentCandidateValidationV1.checks` is populated from this
same registry. Criteria that cannot yet be grounded in one specific confirmed field instead check
the coarser `valid`/`errors` deterministic-gate signal and record exactly that in `evidence_key`,
so a later calibration pass against one real generated bundle can sharpen them without redesigning
this module -- see `evidence_bundle.py`'s own docstring for the same caveat.

A candidate is `ACCEPTED` only at exactly 30/30 with zero hard disqualifiers
(`acceptance_verdict()`) -- a 30/30 numeric total with any disqualifier present is still rejected,
and missing evidence never defaults to a point (`rubric_criteria.py::_criterion`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import (
    EvidenceBundleV1,
    load_evidence_bundle,
)
from readme_agent.supervisor.portfolio_proof_engine.rubric_criteria import (
    RubricCriterionResultV1,
    evaluate_all_criteria,
    evaluate_hard_disqualifiers,
)


class RubricScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    criteria: tuple[RubricCriterionResultV1, ...] = Field(min_length=30, max_length=30)
    hard_disqualifiers: tuple[str, ...] = ()

    @property
    def total_score(self) -> int:
        return sum(criterion.awarded_points for criterion in self.criteria)

    @property
    def missing_evidence_criteria(self) -> tuple[int, ...]:
        return tuple(
            criterion.criterion_id for criterion in self.criteria if criterion.awarded_points == 0
        )


def score_candidate(bundle: EvidenceBundleV1) -> RubricScoreV1:
    return RubricScoreV1(
        org_repo=bundle.org_repo,
        criteria=evaluate_all_criteria(bundle),
        hard_disqualifiers=evaluate_hard_disqualifiers(bundle),
    )


def acceptance_verdict(score: RubricScoreV1) -> bool:
    return score.total_score == 30 and not score.hard_disqualifiers


def evaluate_repository(org_repo: str, backend: StateBackend) -> RubricAcceptanceOutcome:
    """The `mode_shared.RubricEvaluator` default: resolve the current candidate identity from
    durable lifecycle state, load its evidence bundle, and score it."""

    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    source_revision = (
        lifecycle.source_revision if isinstance(lifecycle, ReadmePocLifecycleStateV2) else None
    )
    candidate_hash = (
        lifecycle.candidate_hash if isinstance(lifecycle, ReadmePocLifecycleStateV2) else None
    )
    bundle = load_evidence_bundle(org_repo, source_revision, candidate_hash=candidate_hash)
    score = score_candidate(bundle)
    return RubricAcceptanceOutcome(
        org_repo=org_repo,
        accepted=acceptance_verdict(score),
        score=score.total_score,
        hard_disqualifier_count=len(score.hard_disqualifiers),
        missing_evidence_criteria=score.missing_evidence_criteria,
    )
