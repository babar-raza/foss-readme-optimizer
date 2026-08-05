"""Typed policy state for agile mission admission, verification, and replanning."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskExecutionKind = Literal[
    "auto",
    "visible_delivery",
    "infrastructure",
    "shared_repair",
    "acceptance",
]
InfrastructureTrigger = Literal[
    "current_repository_blocker",
    "next_cohort_exercised",
    "demonstrated_safety_defect",
    "measured_current_cohort_benefit",
    "speculative",
]
ChangeClass = Literal[
    "governance",
    "mission_state",
    "shared_code",
    "repository_runtime",
    "factuality",
    "presentation",
    "safety",
    "workflow",
    "effect",
]
UserInputClassification = Literal[
    "goal",
    "constraint",
    "preference",
    "hypothesis",
    "tactic",
    "authorization",
]
RouteChangeAssessment = Literal[
    "reuse",
    "invalidation",
    "critical_path",
    "infrastructure_timing",
    "factuality",
    "safety",
    "smaller_alternatives",
]
VerificationTier = Literal[
    "touched_static",
    "focused",
    "impacted_integration",
    "safety_regression",
    "complete_non_live",
    "repository_acceptance",
    "cohort_reconstruction",
    "live_like",
]
EvidencePromotionBoundary = Literal[
    "runtime_only",
    "shared_code",
    "repository",
    "cohort",
    "stage",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InfrastructureAdmissionSpecV1(_StrictModel):
    """Why an infrastructure task belongs on the current delivery path."""

    trigger: InfrastructureTrigger
    evidence_refs: list[str] = Field(default_factory=list)
    measured_net_benefit: float | None = None


class InfrastructureAdmissionDecisionV1(_StrictModel):
    task_id: str
    admitted: bool
    reason: str
    trigger: InfrastructureTrigger
    infrastructure_tasks_since_visible_delivery: int = Field(ge=0)
    python_platform_complete: bool


class VerificationPlanV1(_StrictModel):
    task_id: str
    change_classes: list[ChangeClass] = Field(min_length=1)
    required_tiers: list[VerificationTier] = Field(min_length=1)
    promotion_boundary: EvidencePromotionBoundary
    canonical_promotion_allowed: bool
    reason: str


class TaskCloseoutControlEvidenceV1(_StrictModel):
    """Policy receipt required alongside contribution evidence at task closeout."""

    schema_version: Literal[1] = 1
    task_id: str
    verification_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_tiers: list[VerificationTier] = Field(min_length=1)
    promotion_boundary: EvidencePromotionBoundary
    canonical_evidence_promoted: bool
    transaction_isolation_proven: bool = False
    proof_refs: list[str] = Field(min_length=1)
    independently_verified: bool
    multi_agent_execution_plan_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    multi_agent_admission_decision_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )


class ParallelismObservationV1(_StrictModel):
    lane_count: int = Field(ge=2, le=3)
    serial_seconds: float = Field(gt=0)
    parallel_seconds: float = Field(gt=0)
    coordination_seconds: float = Field(ge=0)
    isolation_proven: bool
    disjoint_lease_ids: list[str] = Field(min_length=2, max_length=3)
    duplicate_work_detected: bool = False
    observed_at: str

    @model_validator(mode="after")
    def _leases_match_lanes(self) -> ParallelismObservationV1:
        if len(self.disjoint_lease_ids) != self.lane_count:
            raise ValueError("parallel observation requires exactly one lease per lane")
        if len(set(self.disjoint_lease_ids)) != len(self.disjoint_lease_ids):
            raise ValueError("parallel observation lease IDs must be disjoint")
        return self

    @property
    def speedup(self) -> float:
        return self.serial_seconds / self.parallel_seconds

    @property
    def coordination_overhead_ratio(self) -> float:
        return self.coordination_seconds / self.parallel_seconds


class ParallelismControlStateV1(_StrictModel):
    transaction_isolation_proven: bool = False
    calibration_active: bool = True
    shared_repair_active: bool = False
    observations: list[ParallelismObservationV1] = Field(default_factory=list)


class ParallelismDecisionV1(_StrictModel):
    max_repository_lanes: int = Field(ge=1, le=3)
    reason: str
    latest_speedup: float | None = None
    latest_coordination_overhead_ratio: float | None = None


class ApproachAttemptV1(_StrictModel):
    task_id: str
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    started_at: str
    last_material_narrowing_at: str | None = None
    outcome: Literal["in_progress", "ineffective", "effective"] = "in_progress"
    evidence_refs: list[str] = Field(default_factory=list)


class FirstPrinciplesReplanV1(_StrictModel):
    task_id: str
    prior_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_classification: UserInputClassification
    route_change_assessments: list[RouteChangeAssessment] = Field(min_length=7)
    rationale: str = Field(min_length=20)
    causal_owner_changed: bool = False
    pipeline_boundary_changed: bool = False
    mechanism_changed: bool = False
    dependency_sequence_changed: bool = False
    evidence_refs: list[str] = Field(min_length=1)
    created_at: str

    @model_validator(mode="after")
    def _requires_material_change(self) -> FirstPrinciplesReplanV1:
        if self.prior_fingerprint == self.new_fingerprint:
            raise ValueError("first-principles replan must change the approach fingerprint")
        if not any(
            (
                self.causal_owner_changed,
                self.pipeline_boundary_changed,
                self.mechanism_changed,
                self.dependency_sequence_changed,
            )
        ):
            raise ValueError("first-principles replan must change a causal execution dimension")
        required_assessments = {
            "reuse",
            "invalidation",
            "critical_path",
            "infrastructure_timing",
            "factuality",
            "safety",
            "smaller_alternatives",
        }
        if set(self.route_change_assessments) != required_assessments:
            raise ValueError(
                "first-principles replan must assess reuse, invalidation, critical path, "
                "infrastructure timing, factuality, safety, and smaller alternatives"
            )
        return self


class ApproachControlStateV1(_StrictModel):
    attempts: list[ApproachAttemptV1] = Field(default_factory=list)
    replans: list[FirstPrinciplesReplanV1] = Field(default_factory=list)
    proposed_fingerprints: dict[str, str] = Field(default_factory=dict)


class ApproachAdmissionDecisionV1(_StrictModel):
    task_id: str
    admitted: bool
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str
    equivalent_ineffective_attempts: int = Field(ge=0)
    requires_first_principles_replan: bool


class SafeCommandAuthorityRequestV1(_StrictModel):
    plan_bound: bool
    local_only: bool
    destructive: bool = False
    external_effect: bool = False
    credentials_required: bool = False
    manual_ui_required: bool = False


class SafeCommandAuthorityDecisionV1(_StrictModel):
    disposition: Literal["AUTO_PROCEED", "HUMAN_AUTHORITY_REQUIRED", "REJECT_NOT_PLAN_BOUND"]
    reason: str
