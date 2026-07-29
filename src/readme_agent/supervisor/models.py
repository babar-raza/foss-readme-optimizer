"""Typed public results emitted by repository supervision."""

from dataclasses import dataclass, field
from pathlib import Path

from readme_agent.state.lifecycle_schema import AssuranceReadmePocStatusV1
from readme_agent.supervisor.stage_limit import ReadmePocStageLimitV1
from readme_agent.supervisor.task import TaskGraph


@dataclass
class DecisionSummary:
    """A concise, evidence-safe record of an autonomous decision."""

    turn: int
    kind: str
    detail: str


@dataclass
class SuperviseResult:
    """Terminal result of one canonical repository-supervision run."""

    status: str
    org_repo: str
    task_graph: TaskGraph
    decisions: list[DecisionSummary] = field(default_factory=list)
    blocked_reason: str | None = None
    blocked_category: str | None = None
    evidence_dir: Path | None = None
    requested_readme_stage: ReadmePocStageLimitV1 | None = None
    readme_lifecycle_status: AssuranceReadmePocStatusV1 | None = None
