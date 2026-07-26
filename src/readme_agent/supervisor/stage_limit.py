"""Typed lifecycle ceilings for stage-bounded local README proof."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.state.lifecycle_schema import ReadmePocStatusV2

ReadmePocStageLimitV1 = Literal["FACTS_READY"]
README_POC_STAGE_LIMITS: tuple[ReadmePocStageLimitV1, ...] = ("FACTS_READY",)

_FACTS_READY_OR_LATER = frozenset(
    {
        "FACTS_READY",
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_REVIEW_READY",
        "HUMAN_ACCEPTED",
        "PR_ELIGIBLE",
        "PR_PROOF_COMPLETE",
        "DETERMINISTIC_VALIDATION_FAILED",
        "AGENT_REVIEW_REJECTED",
        "REPAIRING",
    }
)


class ReadmePocStageBoundaryV1(BaseModel):
    """Evaluation of one requested ceiling against durable lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_stage: ReadmePocStageLimitV1
    observed_stage: ReadmePocStatusV2
    reached: bool


def lifecycle_stage_reaches_limit(
    requested_stage: ReadmePocStageLimitV1,
    observed_stage: str,
) -> bool:
    """Return false for incomplete, blocked, or non-lifecycle portfolio results."""

    if requested_stage != "FACTS_READY":  # pragma: no cover - Literal exhaustiveness guard
        raise ValueError(f"unsupported README POC stage limit: {requested_stage!r}")
    return observed_stage in _FACTS_READY_OR_LATER


def evaluate_stage_boundary(
    requested_stage: ReadmePocStageLimitV1,
    observed_stage: ReadmePocStatusV2,
) -> ReadmePocStageBoundaryV1:
    """Return whether the requested proof boundary has been reached."""

    return ReadmePocStageBoundaryV1(
        requested_stage=requested_stage,
        observed_stage=observed_stage,
        reached=lifecycle_stage_reaches_limit(requested_stage, observed_stage),
    )
