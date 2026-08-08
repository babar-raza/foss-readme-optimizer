"""Typed durable contracts that bind mission work to portfolio outcomes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MissionGoalId = Literal[
    "GOAL-CORE-PRESENTABLE-PORTFOLIO",
    "GOAL-TRUTH",
    "GOAL-README",
    "GOAL-PROFILE",
    "GOAL-AUTONOMY",
    "GOAL-DELIVERY",
    "GOAL-MATURITY",
]
StageGoalId = Literal[
    "GOAL-P0-PLAN-FREEZE",
    "GOAL-V0A-FIRST-VERIFIED-README",
    "GOAL-T0-TRUSTED-QUALIFICATION",
    "GOAL-V0-VERIFIED-PYTHON-POC",
    "GOAL-TP-TRUSTED-COHORT-POC",
    "GOAL-T0R-TRUSTED-ADVERSARIAL-QUALIFICATION",
    "GOAL-V0B-POST-PYTHON-SLICES",
    "GOAL-C0-AUTHORIZED-PORTFOLIO",
    "GOAL-T1-TRUSTED-PORTFOLIO",
    "GOAL-T2-WORKFLOW-STAGING",
    "GOAL-T3-HOSTED-TRUSTED-DELIVERY",
    "GOAL-V1-VERIFIED-TRUTH",
    "GOAL-V2-VERIFIED-GATE-A",
    "GOAL-V3-HUMAN-AND-JAVA-PROOF",
    "GOAL-L5-PRESENTATION-PILOT",
    "GOAL-L6-AUTONOMOUS-PORTFOLIO",
    "GOAL-L7-HETEROGENEOUS-30D",
    "GOAL-L8-SELF-MAINTAINING-90D",
]
ExecutionCampaignId = Literal[
    "CAMP-PLAN-FREEZE",
    "CAMP-SHARED-ACCELERATION",
    "CAMP-FIRST-PYTHON-SLICE",
    "CAMP-THREE-SLICES",
    "CAMP-PYTHON-PORTFOLIO",
    "CAMP-GATE-A-PORTFOLIO",
    "CAMP-GATE-B-AND-LATER",
]
SubordinateGoalId = Literal[
    "GOAL-TRUTH",
    "GOAL-README",
    "GOAL-PROFILE",
    "GOAL-AUTONOMY",
    "GOAL-DELIVERY",
    "GOAL-MATURITY",
]
CoreContributionKind = Literal[
    "visible_deliverable",
    "first_boundary_removal",
    "indispensable_safety",
    "acceptance_proof",
]
MissionLifecycleBoundary = Literal[
    "FACTS_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
    "HUMAN_ACCEPTED",
    "MISSION_CLOSED",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MissionGoalDefinitionV1(_StrictModel):
    """One governed goal in the immutable mission hierarchy."""

    goal_id: MissionGoalId
    role: Literal["core", "subordinate"]
    summary: str = Field(min_length=20)
    acceptance_boundary: str = Field(min_length=10)


class StageGoalDefinitionV1(_StrictModel):
    """One ordered, evidence-derived operating goal."""

    goal_id: StageGoalId
    order: int = Field(ge=0)
    summary: str = Field(min_length=20)
    acceptance_boundary: str = Field(min_length=10)
    execution_required: bool = True
    concurrent_when_earlier_primary: bool = False
    product_effects_allowed: bool = False
    reserved_trusted_lanes: int = Field(default=0, ge=0, le=4)
    max_concurrent_verified_lanes: int = Field(default=0, ge=0, le=4)


class MissionGoalTransitionV1(_StrictModel):
    """Append-only primary/concurrent goal-set transition."""

    from_primary_goal_id: StageGoalId | None = None
    to_primary_goal_id: StageGoalId | None = None
    from_concurrent_goal_ids: list[StageGoalId] = Field(default_factory=list)
    to_concurrent_goal_ids: list[StageGoalId] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    occurred_at: str


class CoreContributionV1(_StrictModel):
    """Concrete way a task advances the core visitor-facing deliverable."""

    kind: CoreContributionKind
    summary: str = Field(min_length=30)


class MissionLifecycleScoreboardV1(_StrictModel):
    """Dynamic-denominator progress derived from durable repository lifecycles."""

    schema_version: Literal[1] = 1
    registry_path: str
    registry_sha256: str
    denominator: int = Field(ge=0)
    trusted_facts_extracted: int = Field(default=0, ge=0)
    trusted_candidate_generated: int = Field(default=0, ge=0)
    trusted_transform_approved: int = Field(default=0, ge=0)
    trusted_no_op_proven: int = Field(default=0, ge=0)
    trusted_pr_open: int = Field(default=0, ge=0)
    facts_ready: int = Field(ge=0)
    candidate_generated: int = Field(ge=0)
    deterministic_validated: int = Field(ge=0)
    agent_approved: int = Field(ge=0)
    no_op_proven: int = Field(ge=0)
    human_accepted: int = Field(ge=0)
    raw_facts_ready: int = Field(default=0, ge=0)
    raw_candidate_generated: int = Field(default=0, ge=0)
    raw_deterministic_validated: int = Field(default=0, ge=0)
    raw_agent_approved: int = Field(default=0, ge=0)
    raw_no_op_proven: int = Field(default=0, ge=0)
    raw_human_accepted: int = Field(default=0, ge=0)
    stale_fact_contract_repositories: dict[str, list[str]] = Field(default_factory=dict)
    stale_acceptance_repositories: dict[str, list[str]] = Field(default_factory=dict)
    missing_lifecycle_repositories: list[str] = Field(default_factory=list)
    lifecycle_status_counts: dict[str, int] = Field(default_factory=dict)
    first_failing_boundary: MissionLifecycleBoundary
    derived_at: str


class MissionNextTaskV1(_StrictModel):
    """Exact durable continuation selected from graph state."""

    task_id: str
    # Optional only while loading pre-TRP-00 durable state. Every refreshed
    # mission decision writes the governed stage.
    stage_goal_id: StageGoalId | None = None
    campaign_id: ExecutionCampaignId | None = None
    goal_ids: list[SubordinateGoalId] = Field(min_length=1)
    core_contribution: CoreContributionV1
    immediate_goal_id: str | None = None
    immediate_outcome: str | None = None
    repository_scope: list[str] = Field(default_factory=list)


class MissionContributionEvidenceV1(_StrictModel):
    """Machine-checkable proof that one task made its declared contribution."""

    schema_version: Literal[1] = 1
    task_id: str
    # Historical evidence remains readable; the close guard requires this for
    # every post-migration transition.
    stage_goal_id: StageGoalId | None = None
    campaign_id: ExecutionCampaignId | None = None
    goal_ids: list[SubordinateGoalId] = Field(min_length=1)
    core_contribution: CoreContributionV1
    acceptance_checks_passed: list[str] = Field(min_length=1)
    proof_refs: list[str] = Field(min_length=1)
    scoreboard_before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scoreboard_after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_failing_boundary_before: MissionLifecycleBoundary
    first_failing_boundary_after: MissionLifecycleBoundary
    # Control and safety tasks can remove a non-portfolio boundary while the
    # repository lifecycle scoreboard truthfully remains unchanged.
    contribution_boundary_before: str | None = None
    contribution_boundary_after: str | None = None
    independently_verified: bool
