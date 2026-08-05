"""Admit only just-in-time infrastructure onto the visible-delivery path."""

from __future__ import annotations

from readme_agent.state.agile_execution_schema import (
    InfrastructureAdmissionDecisionV1,
    TaskExecutionKind,
)
from readme_agent.supervisor.mission_schema import TaskCardV1

_ADMISSIBLE_TRIGGERS = {
    "current_repository_blocker",
    "next_cohort_exercised",
    "demonstrated_safety_defect",
    "measured_current_cohort_benefit",
}


def task_execution_kind(task: TaskCardV1) -> TaskExecutionKind:
    """Resolve the explicit task kind or its stable contribution-based default."""

    if task.execution_kind != "auto":
        return task.execution_kind
    if task.core_contribution.kind == "visible_deliverable":
        return "visible_delivery"
    if task.core_contribution.kind == "first_boundary_removal":
        return "infrastructure"
    if task.core_contribution.kind == "indispensable_safety":
        return "shared_repair"
    return "acceptance"


def decide_infrastructure_admission(
    task: TaskCardV1,
    *,
    infrastructure_tasks_since_visible_delivery: int,
    python_platform_complete: bool,
) -> InfrastructureAdmissionDecisionV1:
    """Fail closed on speculation and pre-Python infrastructure stacking."""

    kind = task_execution_kind(task)
    if kind not in {"infrastructure", "shared_repair"}:
        return InfrastructureAdmissionDecisionV1(
            task_id=task.task_id,
            admitted=True,
            reason="task is not infrastructure",
            trigger=(
                task.infrastructure_admission.trigger
                if task.infrastructure_admission is not None
                else "speculative"
            ),
            infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
            python_platform_complete=python_platform_complete,
        )
    spec = task.infrastructure_admission
    if spec is None:
        return InfrastructureAdmissionDecisionV1(
            task_id=task.task_id,
            admitted=False,
            reason="infrastructure task lacks an explicit admission specification",
            trigger="speculative",
            infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
            python_platform_complete=python_platform_complete,
        )
    if spec.trigger not in _ADMISSIBLE_TRIGGERS:
        return InfrastructureAdmissionDecisionV1(
            task_id=task.task_id,
            admitted=False,
            reason="speculative infrastructure has no current delivery admission trigger",
            trigger=spec.trigger,
            infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
            python_platform_complete=python_platform_complete,
        )
    if not spec.evidence_refs:
        return InfrastructureAdmissionDecisionV1(
            task_id=task.task_id,
            admitted=False,
            reason="infrastructure trigger lacks inspectable evidence",
            trigger=spec.trigger,
            infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
            python_platform_complete=python_platform_complete,
        )
    if spec.trigger == "measured_current_cohort_benefit" and (
        spec.measured_net_benefit is None or spec.measured_net_benefit <= 0
    ):
        return InfrastructureAdmissionDecisionV1(
            task_id=task.task_id,
            admitted=False,
            reason="measured-benefit admission requires a positive current-cohort net benefit",
            trigger=spec.trigger,
            infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
            python_platform_complete=python_platform_complete,
        )
    if not python_platform_complete and infrastructure_tasks_since_visible_delivery >= 1:
        return InfrastructureAdmissionDecisionV1(
            task_id=task.task_id,
            admitted=False,
            reason=(
                "only one infrastructure task may occur between visible deliveries "
                "before Python closes"
            ),
            trigger=spec.trigger,
            infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
            python_platform_complete=False,
        )
    return InfrastructureAdmissionDecisionV1(
        task_id=task.task_id,
        admitted=True,
        reason="just-in-time infrastructure trigger is evidenced and within the delivery budget",
        trigger=spec.trigger,
        infrastructure_tasks_since_visible_delivery=infrastructure_tasks_since_visible_delivery,
        python_platform_complete=python_platform_complete,
    )
