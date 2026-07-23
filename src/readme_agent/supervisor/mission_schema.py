"""Typed contracts for the supervisor's central implementation mission graph."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class MissionAuthorityV1(_StrictModel):
    mission_id: str
    mission_summary: str
    governing_plan_path: str
    current_phase: str
    in_scope_outcomes: list[str]
    out_of_scope_items: list[str]
    mandatory_acceptance_criteria: list[str]
    conflicts_found: list[str]
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
    requirement_ids: list[str] = Field(default_factory=list)
    blocker_attempts: list[BlockerAttemptV1] = Field(default_factory=list)
    exact_external_action: str | None = None
    exact_resume_condition: str | None = None


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


class MissionTaskGraphV1(_StrictModel):
    schema_version: Literal[1]
    autonomous_execution_contract: AutonomousExecutionContractV1
    mission_authority: MissionAuthorityV1
    verified_baseline: dict
    taskcards: list[TaskCardV1]
    requirement_coverage: RequirementCoverageV1 | None = None
    continuation_state: dict
