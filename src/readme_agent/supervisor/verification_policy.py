"""Derive proportional verification and evidence-promotion policy for mission tasks."""

from __future__ import annotations

import hashlib
import json

from readme_agent.state.agile_execution_schema import (
    ChangeClass,
    EvidencePromotionBoundary,
    TaskCloseoutControlEvidenceV1,
    VerificationPlanV1,
    VerificationTier,
)
from readme_agent.supervisor.infrastructure_admission import task_execution_kind
from readme_agent.supervisor.mission_schema import TaskCardV1


def _unique(items: list[VerificationTier]) -> list[VerificationTier]:
    return list(dict.fromkeys(items))


def infer_change_classes(task: TaskCardV1) -> list[ChangeClass]:
    """Infer a conservative typed impact set when the graph omits an explicit set."""

    if task.verification_change_classes:
        return task.verification_change_classes
    paths = " ".join(task.allowed_paths).lower()
    classes: list[ChangeClass] = []
    if any(token in paths for token in ("agents.md", "plans/", "logs/")):
        classes.append("governance")
    if "src/readme_agent/state/" in paths or "src/readme_agent/supervisor/" in paths:
        classes.append("mission_state")
    if any(token in paths for token in ("src/", "scripts/", "tests/")):
        classes.append("shared_code")
    if any(token in paths for token in ("runs/", "templates/", "prompts/", "docs/")):
        classes.append("repository_runtime")
    if not classes:
        classes.append("repository_runtime")
    return list(dict.fromkeys(classes))


def infer_promotion_boundary(task: TaskCardV1) -> EvidencePromotionBoundary:
    if task.evidence_promotion_boundary is not None:
        return task.evidence_promotion_boundary
    kind = task_execution_kind(task)
    if kind in {"infrastructure", "shared_repair"}:
        return "shared_code"
    if kind == "visible_delivery":
        return "repository"
    if task.core_contribution.kind == "acceptance_proof":
        return "cohort"
    return "runtime_only"


def build_verification_plan(task: TaskCardV1) -> VerificationPlanV1:
    """Map task impact to deterministic proof tiers and one promotion boundary."""

    classes = infer_change_classes(task)
    tiers: list[VerificationTier] = ["touched_static", "focused"]
    if any(item in classes for item in ("mission_state", "shared_code", "workflow", "effect")):
        tiers.append("impacted_integration")
    if any(item in classes for item in ("factuality", "safety", "workflow", "effect")):
        tiers.append("safety_regression")
    boundary = infer_promotion_boundary(task)
    if boundary == "shared_code":
        tiers.append("complete_non_live")
    if boundary == "repository":
        tiers.append("repository_acceptance")
    if boundary in {"cohort", "stage"}:
        tiers.append("cohort_reconstruction")
    if any(item in classes for item in ("workflow", "effect")):
        tiers.append("live_like")
    return VerificationPlanV1(
        task_id=task.task_id,
        change_classes=classes,
        required_tiers=_unique(tiers),
        promotion_boundary=boundary,
        canonical_promotion_allowed=boundary != "runtime_only",
        reason="risk tiers derive from touched seams and the declared acceptance boundary",
    )


def verification_plan_sha256(plan: VerificationPlanV1) -> str:
    payload = json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_closeout_control_evidence(
    task: TaskCardV1,
    evidence: TaskCloseoutControlEvidenceV1,
) -> TaskCloseoutControlEvidenceV1:
    """Reject incomplete proof tiers and promotion outside a canonical boundary."""

    plan = build_verification_plan(task)
    if evidence.task_id != task.task_id:
        raise ValueError("closeout control evidence belongs to another task")
    if evidence.verification_plan_sha256 != verification_plan_sha256(plan):
        raise ValueError("closeout control evidence uses a stale verification plan")
    missing = set(plan.required_tiers) - set(evidence.completed_tiers)
    if missing:
        raise ValueError(
            f"closeout control evidence is missing verification tiers: {sorted(missing)}"
        )
    if evidence.promotion_boundary != plan.promotion_boundary:
        raise ValueError("closeout control evidence uses the wrong promotion boundary")
    if evidence.canonical_evidence_promoted != plan.canonical_promotion_allowed:
        raise ValueError("canonical evidence promotion does not match the accepted boundary")
    if evidence.transaction_isolation_proven and task_execution_kind(task) != "visible_delivery":
        raise ValueError(
            "transaction isolation can be proven only by a complete visible repository delivery"
        )
    if not evidence.independently_verified:
        raise ValueError("closeout control evidence was not independently verified")
    return evidence
