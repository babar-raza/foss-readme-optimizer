"""Typed contracts for the supervisor's central implementation mission graph."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.state.agile_execution_schema import (
    ChangeClass,
    EvidencePromotionBoundary,
    InfrastructureAdmissionSpecV1,
    TaskExecutionKind,
)
from readme_agent.state.mission_goal_schema import (
    CoreContributionV1,
    ExecutionCampaignId,
    MissionGoalDefinitionV1,
    MissionGoalId,
    StageGoalDefinitionV1,
    StageGoalId,
    SubordinateGoalId,
)
from readme_agent.state.schema import MissionTaskStatus


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AutonomousExecutionContractV1(_StrictModel):
    selected_mechanism: str
    mechanism_type: Literal["autonomous_supervision", "autonomous_cycle"]
    entry_point: str
    invocation: str
    governing_state: str
    task_source: str
    continuation_source: str
    continuation_consumer: str
    stop_evaluator: str
    resume_strategy: str
    rejected_alternative: str
    mechanism_locked: bool
    multi_agent_model: Literal["adaptive_coordinator_led"]
    coordinator_role: str
    independent_verification_required: bool
    serial_calibration_required: bool
    minimum_parallel_speedup: float = Field(gt=1.0)
    maximum_coordination_overhead_ratio: float = Field(ge=0.0, le=1.0)
    max_parallel_workers_beside_coordinator: int = Field(ge=1, le=3)
    task_lane_plan_required_when_delegating: bool
    task_lane_plan_path_template: str
    task_lane_plan_protocol: list[str]


class MissionAuthorityV1(_StrictModel):
    mission_id: str
    mission_summary: str
    governing_plan_path: str
    current_phase: str
    in_scope_outcomes: list[str]
    out_of_scope_items: list[str]
    mandatory_acceptance_criteria: list[str]
    conflicts_found: list[str]
    core_goal_id: MissionGoalId | None = None
    goal_catalog: list[MissionGoalDefinitionV1] = Field(default_factory=list)
    stage_goal_catalog: list[StageGoalDefinitionV1] = Field(default_factory=list)
    mission_locked: bool


class BlockerAttemptV1(_StrictModel):
    blocker_id: str
    attempt_number: int
    hypothesis: str
    first_failing_boundary: str
    evidence_considered: list[str]
    action_taken: str
    verification_run: list[str]
    result: str
    new_information: str
    reason_for_next_attempt: str


class ExecutionCampaignV1(_StrictModel):
    """Scheduling and aggregate-evidence group inside the sole mission graph."""

    campaign_id: ExecutionCampaignId
    order: int = Field(ge=0)
    summary: str = Field(min_length=20)
    acceptance_boundary: str = Field(min_length=20)
    full_suite_policy: str = Field(min_length=20)


class TaskExecutionFocusV1(_StrictModel):
    """One small, visible execution goal inside the umbrella mission."""

    goal_id: str = Field(pattern=r"^DELIVERY-[A-Z0-9-]+$")
    immediate_outcome: str = Field(min_length=20)
    repository_scope: list[str] = Field(min_length=1)
    allowed_change_classes: list[ChangeClass] = Field(min_length=1)
    next_goal_on_success: str = Field(min_length=10)
    defer_nonblocking_findings: bool = True
    show_output_before_broad_regression: bool = True
    max_equivalent_ineffective_attempts: int = Field(default=2, ge=1, le=2)
    max_minutes_without_narrowing: int = Field(default=15, ge=1, le=15)

    @model_validator(mode="after")
    def _scope_is_unique(self) -> TaskExecutionFocusV1:
        if len(self.repository_scope) != len(set(self.repository_scope)):
            raise ValueError("execution focus repository_scope contains duplicates")
        if len(self.allowed_change_classes) != len(set(self.allowed_change_classes)):
            raise ValueError("execution focus allowed_change_classes contains duplicates")
        return self


class TaskCardV1(_StrictModel):
    task_id: str
    mission_id: str
    parent_task_id: str | None
    title: str
    source_audit_finding: str
    audit_classification: Literal[
        "completed_verified",
        "completed_but_weakly_verified",
        "partially_done",
        "not_attempted",
        "claimed_unproven",
        "risk_not_reduced",
        "final_outcome_blocker",
        "future_hardening_work",
    ]
    priority: Literal["P0", "P1", "P2", "P3"]
    lane: str
    owner: str
    status: MissionTaskStatus
    objective: str
    why_it_matters: str
    allowed_paths: list[str]
    forbidden_paths: list[str]
    dependencies: list[str]
    expected_outputs: list[str]
    acceptance_checks: list[str]
    verification: list[str]
    negative_controls: list[str]
    regression_checks: list[str]
    evidence_requirements: list[str]
    rollback_or_recovery: str
    failure_reroute: str
    closeout_rules: list[str]
    stage_goal_id: StageGoalId
    campaign_id: ExecutionCampaignId | None = None
    concurrency_class: Literal["primary_only", "read_only_assurance_isolated"] = "primary_only"
    goal_ids: list[SubordinateGoalId] = Field(min_length=1)
    core_contribution: CoreContributionV1
    requirement_ids: list[str] = Field(default_factory=list)
    blocker_attempts: list[BlockerAttemptV1] = Field(default_factory=list)
    exact_external_action: str | None = None
    exact_resume_condition: str | None = None
    execution_kind: TaskExecutionKind = "auto"
    infrastructure_admission: InfrastructureAdmissionSpecV1 | None = None
    verification_change_classes: list[ChangeClass] = Field(default_factory=list)
    evidence_promotion_boundary: EvidencePromotionBoundary | None = None
    execution_focus: TaskExecutionFocusV1 | None = None

    @model_validator(mode="after")
    def _explicit_infrastructure_requires_admission(self) -> TaskCardV1:
        if (
            self.execution_kind in {"infrastructure", "shared_repair"}
            and self.infrastructure_admission is None
        ):
            raise ValueError(
                "explicit infrastructure/shared-repair tasks require infrastructure_admission"
            )
        return self


class RequirementTaskMappingV1(_StrictModel):
    requirement_id: str
    priority: Literal["P0", "P1", "P2", "P3"]
    requirement_status: Literal[
        "IMPLEMENTED",
        "PARTIAL",
        "PLANNED",
        "RESEARCH-GATED",
        "GOVERNANCE",
        "DEPRECATED",
        "BACKLOG",
    ]
    task_id: str
    disposition: Literal[
        "preserved_verified",
        "reopened_semantic_evidence_gap",
        "active_governance",
        "open_mandatory",
        "excluded_backlog",
        "excluded_deprecated",
    ]
    semantic_findings: list[str] = Field(default_factory=list)


class RequirementCoverageV1(_StrictModel):
    source_path: str
    source_sha256: str
    semantic_matrix_path: str
    total_requirement_rows: int
    mandatory_requirement_rows: int
    excluded_backlog_rows: int
    excluded_deprecated_rows: int
    reopened_implemented_rows: int
    mappings: list[RequirementTaskMappingV1]


class ExternalCatalogReferenceV1(_StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(ge=0)


class RequirementCoverageReferenceV1(ExternalCatalogReferenceV1):
    mandatory_requirement_rows: int = Field(ge=0)
    reopened_implemented_rows: int = Field(ge=0)


class RequirementCatalogRecordV1(_StrictModel):
    schema_version: Literal[1]
    requirement_id: str
    section: str
    legacy_section: str | None = None
    requirement: str
    legacy_requirement: str | None = None
    priority: Literal["P0", "P1", "P2", "P3"]
    legacy_priority: Literal["P0", "P1", "P2", "P3"] | None = None
    status: Literal[
        "IMPLEMENTED",
        "PARTIAL",
        "PLANNED",
        "RESEARCH-GATED",
        "GOVERNANCE",
        "DEPRECATED",
        "BACKLOG",
    ]
    legacy_status: (
        Literal[
            "IMPLEMENTED",
            "PARTIAL",
            "PLANNED",
            "RESEARCH-GATED",
            "GOVERNANCE",
            "DEPRECATED",
            "BACKLOG",
        ]
        | None
    ) = None
    acceptance_evidence: str
    legacy_acceptance_evidence: str | None = None
    traceability: str
    legacy_traceability: str | None = None
    legacy_line: int = Field(gt=0)
    legacy_row_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DecisionCatalogRecordV1(_StrictModel):
    schema_version: Literal[1]
    decision_id: int = Field(gt=0)
    title: str
    markdown: str
    legacy_title: str | None = None
    legacy_markdown: str | None = None
    legacy_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeferredTaskRecordV1(_StrictModel):
    schema_version: Literal[1]
    activation_group: str
    task: TaskCardV1


class DeferredTaskIndexV1(_StrictModel):
    task_id: str
    status: MissionTaskStatus
    stage_goal_id: StageGoalId
    activation_group: str
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MissionTaskGraphV1(_StrictModel):
    schema_version: Literal[3]
    autonomous_execution_contract: AutonomousExecutionContractV1
    mission_authority: MissionAuthorityV1
    verified_baseline: dict
    campaign_catalog: list[ExecutionCampaignV1]
    taskcards: list[TaskCardV1]
    requirement_catalog: ExternalCatalogReferenceV1
    requirement_coverage: RequirementCoverageReferenceV1
    deferred_task_catalog: ExternalCatalogReferenceV1
    deferred_task_index: list[DeferredTaskIndexV1]
    bootstrap_state: dict
