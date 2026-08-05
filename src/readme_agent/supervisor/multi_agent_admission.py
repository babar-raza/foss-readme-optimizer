"""Validate disjoint multi-agent path leases against measured lane capacity."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.state.agile_execution_schema import (
    ParallelismDecisionV1,
    TaskCloseoutControlEvidenceV1,
)

LaneRole = Literal[
    "coordinator",
    "repository_worker",
    "repair_worker",
    "support_worker",
    "independent_verifier",
]
LaneStatus = Literal["active", "completed"]

_SHARED_WRITE_PATHS = (
    ".git",
    ".github",
    "AGENTS.md",
    "plans",
    "scripts/governance",
    "src/readme_agent/state",
    "src/readme_agent/supervisor/mission_command.py",
    "src/readme_agent/supervisor/mission_control.py",
    "src/readme_agent/supervisor/mission_goal_guard.py",
    "src/readme_agent/supervisor/mission_graph.py",
    "src/readme_agent/supervisor/mission_schema.py",
    "pyproject.toml",
    "uv.lock",
)
_IMPLEMENTATION_ROLES = {"coordinator", "repository_worker", "repair_worker"}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.rstrip("/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ".." in pure.parts:
        raise ValueError("lane paths must be non-empty repository-relative paths")
    return normalized


class MultiAgentLaneLeaseV1(_StrictModel):
    lane_id: str = Field(min_length=1)
    role: LaneRole
    status: LaneStatus
    allowed_paths: list[str] = Field(min_length=1)
    authored_paths: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_destination: str | None = None

    @field_validator("allowed_paths", "authored_paths")
    @classmethod
    def _paths_are_repository_relative(cls, values: list[str]) -> list[str]:
        return [_normalize_path(value) for value in values]

    @field_validator("evidence_destination")
    @classmethod
    def _destination_is_repository_relative(cls, value: str | None) -> str | None:
        return _normalize_path(value) if value is not None else None


class MultiAgentAdmissionRequestV1(_StrictModel):
    task_id: str
    lanes: list[MultiAgentLaneLeaseV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def _lane_ids_are_unique(self) -> MultiAgentAdmissionRequestV1:
        identifiers = [lane.lane_id for lane in self.lanes]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("multi-agent lane IDs must be unique")
        return self


class MultiAgentAdmissionDecisionV1(_StrictModel):
    task_id: str
    admitted: bool
    violations: list[str]
    active_lane_count: int = Field(ge=0)
    active_repository_lane_count: int = Field(ge=0)
    measured_repository_capacity: int = Field(ge=1, le=3)


def _static_prefix(pattern: str) -> str:
    parts: list[str] = []
    for part in pattern.split("/"):
        if any(token in part for token in ("*", "?", "[")):
            break
        parts.append(part)
    return "/".join(parts)


def _is_parent_or_same(parent: str, child: str) -> bool:
    return child == parent or child.startswith(f"{parent}/")


def _paths_overlap(left: str, right: str) -> bool:
    if left == right or fnmatch.fnmatchcase(left, right) or fnmatch.fnmatchcase(right, left):
        return True
    left_prefix = _static_prefix(left)
    right_prefix = _static_prefix(right)
    if not left_prefix or not right_prefix:
        return True
    return _is_parent_or_same(left_prefix, right_prefix) or _is_parent_or_same(
        right_prefix, left_prefix
    )


def _shared_path(path: str) -> str | None:
    for shared in _SHARED_WRITE_PATHS:
        if _paths_overlap(path, shared):
            return shared
    return None


def _evidence_exists(lane: MultiAgentLaneLeaseV1, *, repository_root: Path) -> bool:
    if any((repository_root / reference).exists() for reference in lane.evidence_refs):
        return True
    if lane.evidence_destination is None:
        return False
    destination = repository_root / lane.evidence_destination
    return destination.is_file() or (destination.is_dir() and any(destination.iterdir()))


def decide_multi_agent_admission(
    request: MultiAgentAdmissionRequestV1,
    parallelism: ParallelismDecisionV1,
    *,
    repository_root: Path,
) -> MultiAgentAdmissionDecisionV1:
    """Reject unsafe leases while allowing a genuinely serial zero-role execution."""

    active = [lane for lane in request.lanes if lane.status == "active"]
    violations: list[str] = []
    coordinators = [lane for lane in active if lane.role == "coordinator"]
    if active and len(coordinators) != 1:
        violations.append("active multi-agent execution requires exactly one coordinator")

    for lane in active:
        for index, left in enumerate(lane.allowed_paths):
            for right in lane.allowed_paths[index + 1 :]:
                if _paths_overlap(left, right):
                    violations.append(
                        f"lane {lane.lane_id!r} has duplicate or overlapping paths: "
                        f"{left!r} and {right!r}"
                    )
        if lane.role != "coordinator":
            for path in lane.allowed_paths:
                shared = _shared_path(path)
                if shared is not None:
                    violations.append(
                        f"worker lane {lane.lane_id!r} leases coordinator-owned shared "
                        f"path {path!r} overlapping {shared!r}"
                    )

    for index, left_lane in enumerate(active):
        for right_lane in active[index + 1 :]:
            for left in left_lane.allowed_paths:
                for right in right_lane.allowed_paths:
                    if _paths_overlap(left, right):
                        violations.append(
                            f"active lanes {left_lane.lane_id!r} and {right_lane.lane_id!r} "
                            f"have overlapping paths: {left!r} and {right!r}"
                        )

    implementation_paths = [
        path
        for lane in request.lanes
        if lane.role in _IMPLEMENTATION_ROLES
        for path in [*lane.allowed_paths, *lane.authored_paths]
    ]
    for verifier in (lane for lane in request.lanes if lane.role == "independent_verifier"):
        for authored in verifier.authored_paths:
            if any(_paths_overlap(authored, path) for path in implementation_paths):
                violations.append(
                    f"independent verifier {verifier.lane_id!r} authored implementation "
                    f"path {authored!r}"
                )

    for lane in (lane for lane in request.lanes if lane.status == "completed"):
        if not _evidence_exists(lane, repository_root=repository_root):
            violations.append(f"completed lane {lane.lane_id!r} has no inspectable evidence")

    repository_lanes = [lane for lane in active if lane.role == "repository_worker"]
    repair_lanes = [lane for lane in active if lane.role == "repair_worker"]
    active_implementation_workers = [*repository_lanes, *repair_lanes]
    if repair_lanes and len(active_implementation_workers) > 1:
        violations.append("shared-code repair must run as one serial implementation lane")
    if len(repository_lanes) > parallelism.max_repository_lanes:
        violations.append(
            f"{len(repository_lanes)} active repository lanes exceed measured capacity "
            f"{parallelism.max_repository_lanes}"
        )

    return MultiAgentAdmissionDecisionV1(
        task_id=request.task_id,
        admitted=not violations,
        violations=list(dict.fromkeys(violations)),
        active_lane_count=len(active),
        active_repository_lane_count=len(repository_lanes),
        measured_repository_capacity=parallelism.max_repository_lanes,
    )


def request_from_execution_plan(path: Path) -> MultiAgentAdmissionRequestV1:
    """Adapt the existing execution-plan JSON shape without rewriting the plan file."""

    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    lanes: list[MultiAgentLaneLeaseV1] = []
    for role_name, payload in raw.get("roles", {}).items():
        status = payload.get("status")
        if status not in {"active", "completed"}:
            continue
        sub_lanes = payload.get("sub_lanes") or []
        if sub_lanes:
            for sub_lane in sub_lanes:
                lanes.append(
                    MultiAgentLaneLeaseV1(
                        lane_id=sub_lane["lane_id"],
                        role="repair_worker",
                        status=status,
                        allowed_paths=sub_lane["exclusive_paths"],
                        authored_paths=sub_lane.get("authored_paths", []),
                        evidence_refs=sub_lane.get("evidence_refs", []),
                        evidence_destination=sub_lane.get("evidence_destination"),
                    )
                )
            continue
        role: LaneRole
        if role_name == "coordinator":
            role = "coordinator"
        elif role_name == "independent_verification":
            role = "independent_verifier"
        else:
            role = "support_worker"
        lanes.append(
            MultiAgentLaneLeaseV1(
                lane_id=role_name,
                role=role,
                status=status,
                allowed_paths=payload.get("allowed_paths", []),
                authored_paths=payload.get("authored_paths", []),
                evidence_refs=payload.get("evidence_refs", []),
                evidence_destination=payload.get("evidence_destination"),
            )
        )
    return MultiAgentAdmissionRequestV1(task_id=raw["task_id"], lanes=lanes)


def multi_agent_admission_sha256(decision: MultiAgentAdmissionDecisionV1) -> str:
    """Hash the exact deterministic admission decision bound at closeout."""

    payload = json.dumps(decision.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_multi_agent_closeout_binding(
    task_id: str,
    evidence: TaskCloseoutControlEvidenceV1,
    parallelism: ParallelismDecisionV1,
    *,
    repository_root: Path,
) -> None:
    """Bind task closeout to the current admitted execution-plan transaction."""

    plan_path = repository_root / "runs" / "multi-agent" / task_id / "execution-plan.json"
    if not plan_path.is_file():
        if (
            evidence.multi_agent_execution_plan_sha256 is not None
            or evidence.multi_agent_admission_decision_sha256 is not None
        ):
            raise ValueError("closeout cites a multi-agent plan that does not exist")
        return
    request = request_from_execution_plan(plan_path)
    if request.task_id != task_id:
        raise ValueError("multi-agent execution plan belongs to another task")
    decision = decide_multi_agent_admission(
        request,
        parallelism,
        repository_root=repository_root,
    )
    if not decision.admitted:
        raise ValueError(f"multi-agent execution plan is not admitted: {decision.violations}")
    plan_sha256 = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    decision_sha256 = multi_agent_admission_sha256(decision)
    if evidence.multi_agent_execution_plan_sha256 != plan_sha256:
        raise ValueError("closeout uses a stale or missing multi-agent execution plan hash")
    if evidence.multi_agent_admission_decision_sha256 != decision_sha256:
        raise ValueError("closeout uses a stale or missing multi-agent admission decision hash")
