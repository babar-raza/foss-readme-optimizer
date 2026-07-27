"""Derive portfolio progress and enforce mission-task contribution evidence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from readme_agent.errors import ConfigError
from readme_agent.registry.loader import PRODUCTS_PATH, load_products
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import (
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.mission_goal_schema import (
    MissionContributionEvidenceV1,
    MissionLifecycleBoundary,
    MissionLifecycleScoreboardV1,
)
from readme_agent.supervisor.mission_schema import TaskCardV1

_REACHED_STATUSES: dict[MissionLifecycleBoundary, frozenset[str]] = {
    "FACTS_READY": frozenset(
        {
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATION_FAILED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "REPAIRING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "CANDIDATE_GENERATED": frozenset(
        {
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATION_FAILED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "REPAIRING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "DETERMINISTIC_VALIDATED": frozenset(
        {
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "AGENT_APPROVED": frozenset(
        {
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "NO_OP_PROVEN": frozenset(
        {
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "HUMAN_ACCEPTED": frozenset({"HUMAN_ACCEPTED", "PR_ELIGIBLE", "PR_PROOF_COMPLETE"}),
    "MISSION_CLOSED": frozenset(),
}
_ORDERED_BOUNDARIES: tuple[MissionLifecycleBoundary, ...] = (
    "FACTS_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
    "HUMAN_ACCEPTED",
)


def _canonical_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


def derive_lifecycle_scoreboard(
    backend: StateBackend,
    *,
    products_path: Path = PRODUCTS_PATH,
) -> MissionLifecycleScoreboardV1:
    """Read the dynamic registry and each repository's durable lifecycle."""

    entries = load_products(products_path)
    registry_sha256 = _canonical_text_sha256(products_path)
    counts = {boundary: 0 for boundary in _ORDERED_BOUNDARIES}
    status_counts: dict[str, int] = {}
    missing: list[str] = []
    watermarks: list[str] = []
    org_repos = [entry.org_repo for entry in entries]
    bulk_loader = getattr(backend, "load_many", None)
    states = (
        bulk_loader(org_repos)
        if callable(bulk_loader)
        else {org_repo: backend.load(org_repo) for org_repo in org_repos}
    )

    for entry in entries:
        state = states[entry.org_repo]
        lifecycle = state.readme_poc_lifecycle if state is not None else None
        if not isinstance(lifecycle, (ReadmePocLifecycleStateV1, ReadmePocLifecycleStateV2)):
            missing.append(entry.org_repo)
            status = "DISCOVERED"
        else:
            status = lifecycle.status
            watermarks.append(lifecycle.updated_at)
        status_counts[status] = status_counts.get(status, 0) + 1
        for boundary in _ORDERED_BOUNDARIES:
            if status in _REACHED_STATUSES[boundary]:
                counts[boundary] += 1

    denominator = len(entries)
    first_failing: MissionLifecycleBoundary = "MISSION_CLOSED"
    for boundary in _ORDERED_BOUNDARIES:
        if counts[boundary] < denominator:
            first_failing = boundary
            break
    return MissionLifecycleScoreboardV1(
        registry_path=products_path.as_posix(),
        registry_sha256=registry_sha256,
        denominator=denominator,
        facts_ready=counts["FACTS_READY"],
        candidate_generated=counts["CANDIDATE_GENERATED"],
        deterministic_validated=counts["DETERMINISTIC_VALIDATED"],
        agent_approved=counts["AGENT_APPROVED"],
        no_op_proven=counts["NO_OP_PROVEN"],
        human_accepted=counts["HUMAN_ACCEPTED"],
        missing_lifecycle_repositories=sorted(missing),
        lifecycle_status_counts=dict(sorted(status_counts.items())),
        first_failing_boundary=first_failing,
        derived_at=max(
            watermarks,
            default=f"registry:{registry_sha256}",
        ),
    )


def lifecycle_scoreboard_sha256(scoreboard: MissionLifecycleScoreboardV1) -> str:
    """Stable hash for contribution before/after evidence."""

    payload = scoreboard.model_dump_json(exclude={"derived_at"})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_task_contribution_evidence(
    task: TaskCardV1,
    evidence_refs: list[str],
    scoreboard: MissionLifecycleScoreboardV1,
) -> MissionContributionEvidenceV1:
    """Require one structured, matching, independently verified closeout record."""

    parsed: list[MissionContributionEvidenceV1] = []
    for reference in evidence_refs:
        path = Path(reference)
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            parsed.append(
                MissionContributionEvidenceV1.model_validate_json(path.read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeError, ValidationError):
            continue
    matching = [item for item in parsed if item.task_id == task.task_id]
    if len(matching) != 1:
        raise ConfigError(
            f"closing task {task.task_id!r} requires exactly one valid contribution evidence JSON"
        )
    evidence = matching[0]
    if evidence.goal_ids != task.goal_ids or evidence.core_contribution != task.core_contribution:
        raise ConfigError(f"task {task.task_id!r} contribution evidence disagrees with the graph")
    if set(evidence.acceptance_checks_passed) != set(task.acceptance_checks):
        raise ConfigError(
            f"task {task.task_id!r} contribution evidence does not cover every acceptance check"
        )
    if not evidence.independently_verified:
        raise ConfigError(f"task {task.task_id!r} contribution was not independently verified")
    current_hash = lifecycle_scoreboard_sha256(scoreboard)
    if evidence.scoreboard_after_sha256 != current_hash:
        raise ConfigError(f"task {task.task_id!r} contribution evidence uses a stale scoreboard")
    if (
        task.core_contribution.kind == "first_boundary_removal"
        and evidence.scoreboard_before_sha256 == evidence.scoreboard_after_sha256
        and evidence.first_failing_boundary_before == evidence.first_failing_boundary_after
    ):
        raise ConfigError(
            f"task {task.task_id!r} claims boundary removal without a scoreboard boundary delta"
        )
    if not any(Path(reference).exists() for reference in evidence.proof_refs):
        raise ConfigError(f"task {task.task_id!r} contribution proof refs do not exist")
    return evidence


def utc_now_iso() -> str:
    """Clock seam retained for deterministic test patching."""

    return datetime.now(UTC).isoformat()
