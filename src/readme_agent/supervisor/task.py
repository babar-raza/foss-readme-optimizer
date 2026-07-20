"""Task graph (`ORC-001`) -- Wave 5 is "the first wave with a 'run'"
(`capabilities/schema.py::CapabilityGap`'s own docstring). `TaskState`'s
literal set is exactly `ORC-001`'s wording, nothing invented beyond it.

Mirrors `CapabilityManifest`/`CapabilityGap`'s pydantic style, not
`DispatchResult`'s plain-dataclass style -- a `Task` is serialized into
evidence and into `RunStateV1.supervisor_state.task_graph_snapshot`, not an
internal-only return value.
"""

import json
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr

from readme_agent.capabilities.schema import CapabilityGap
from readme_agent.errors import ConfigError

TaskState = Literal[
    "DISCOVERED", "PLANNED", "EXECUTING", "PASSED", "FAILED", "BLOCKED", "STALE", "SUPERSEDED"
]
TERMINAL_STATES: frozenset[TaskState] = frozenset(
    {"PASSED", "FAILED", "BLOCKED", "STALE", "SUPERSEDED"}
)


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid4().hex)
    capability_id: str | None = None
    arguments: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    state: TaskState = "DISCOVERED"
    result: dict | None = None
    gap: CapabilityGap | None = None
    blocked_reason: str | None = None
    supersedes: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    terminal_at: str | None = None


def _canonical_key(capability_id: str | None, arguments: dict) -> str:
    return f"{capability_id}:{json.dumps(arguments, sort_keys=True, separators=(',', ':'))}"


class TaskGraph(BaseModel):
    """A DAG over `Task.depends_on`. `add_task()` rejects a cycle *and* a
    dangling `depends_on` reference immediately (referential integrity,
    mirroring decision #6's precedent). `validate_acyclic()` is a second,
    independent pre-execution gate -- `ORC-001`: "MUST reject cycles
    **before execution**", a real gate on the whole graph, not just add-time
    hygiene on one edge at a time."""

    tasks: dict[str, Task] = Field(default_factory=dict)
    # (capability_id, canonicalized arguments) -> task_id of the PASSED task
    # that answered it -- what makes SUPERSEDED dedup, and therefore
    # convergence, decidable. See add_task()'s dedup check below.
    _passed_index: dict[str, str] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context) -> None:
        self._rebuild_passed_index()

    def _rebuild_passed_index(self) -> None:
        self._passed_index = {
            _canonical_key(t.capability_id, t.arguments): t.task_id
            for t in self.tasks.values()
            if t.state == "PASSED"
        }

    def add_task(self, task: Task) -> Task:
        """Returns the task actually recorded -- either `task` itself, or a
        new `SUPERSEDED` task short-circuited against an already-`PASSED`
        `(capability_id, arguments)` pair, with `task.result` mirroring the
        prior `PASSED` task's result and no re-dispatch. This is what Wave
        1's spike didn't have: its duplicate-call rejection was explicitly
        "a minimal, spike-scoped stand-in for `ORC-001`'s cycle rejection"
        -- cycle rejection (below) and repeat-proposal rejection (here) are
        two different mechanisms."""
        if task.task_id in self.tasks:
            raise ConfigError(f"duplicate task_id {task.task_id!r}")

        missing = [d for d in task.depends_on if d not in self.tasks]
        if missing:
            raise ConfigError(
                f"task {task.task_id!r} depends_on unknown task_id(s) {missing} -- "
                "referential integrity violated"
            )

        if self._creates_cycle(task):
            raise ConfigError(f"adding task {task.task_id!r} would create a dependency cycle")

        dedup_key = _canonical_key(task.capability_id, task.arguments)
        prior_task_id = self._passed_index.get(dedup_key)
        if prior_task_id is not None and task.state == "DISCOVERED":
            prior = self.tasks[prior_task_id]
            task = task.model_copy(
                update={
                    "state": "SUPERSEDED",
                    "supersedes": prior_task_id,
                    "result": prior.result,
                    "terminal_at": datetime.now(UTC).isoformat(),
                }
            )

        self.tasks[task.task_id] = task
        if task.state == "PASSED":
            self._passed_index[dedup_key] = task.task_id
        return task

    def _creates_cycle(self, new_task: Task) -> bool:
        """DFS from each of `new_task.depends_on`, following existing edges
        backward -- if `new_task.task_id` were already reachable (it isn't,
        since it doesn't exist in the graph yet), or if any two existing
        nodes form a cycle among themselves, this catches it. Kept as a
        real, general check rather than an argument that the API makes
        cycles structurally impossible -- `ORC-001` asks for the gate, not
        for a proof it's unreachable."""
        visited: set[str] = set()
        stack = list(new_task.depends_on)
        while stack:
            node_id = stack.pop()
            if node_id == new_task.task_id:
                return True
            if node_id in visited:
                continue
            visited.add(node_id)
            node = self.tasks.get(node_id)
            if node is not None:
                stack.extend(node.depends_on)
        return False

    def validate_acyclic(self) -> None:
        """Independent, whole-graph pre-execution gate (`ORC-001`). Raises
        `ConfigError` on the first cycle found via a standard three-color
        DFS, rather than trusting that every task currently in the graph
        arrived through `add_task()`'s own per-edge check."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(self.tasks, WHITE)

        def visit(task_id: str) -> None:
            color[task_id] = GRAY
            for dep in self.tasks[task_id].depends_on:
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    raise ConfigError(f"cycle detected in task graph at {task_id!r} -> {dep!r}")
                if color[dep] == WHITE:
                    visit(dep)
            color[task_id] = BLACK

        for task_id in list(self.tasks):
            if color[task_id] == WHITE:
                visit(task_id)

    def ready_tasks(self) -> list[Task]:
        """`DISCOVERED` tasks whose every `depends_on` entry is *terminal*
        (any of `TERMINAL_STATES`, not specifically `PASSED`). A repair
        task's `depends_on` names the `FAILED` task it repairs -- requiring
        that dependency to reach `PASSED` would make it permanently
        unreachable, since the task it depends on is terminal-but-failed by
        construction. `depends_on` means "wait until resolved, however it
        resolves," not "wait until it specifically succeeds"."""
        return [
            t
            for t in self.tasks.values()
            if t.state == "DISCOVERED"
            and all(self.tasks[d].state in TERMINAL_STATES for d in t.depends_on)
        ]

    def mark(self, task_id: str, state: TaskState, **updates) -> Task:
        task = self.tasks[task_id]
        payload = {"state": state, **updates}
        if state in TERMINAL_STATES:
            payload["terminal_at"] = datetime.now(UTC).isoformat()
        updated = task.model_copy(update=payload)
        self.tasks[task_id] = updated
        if state == "PASSED":
            self._passed_index[_canonical_key(updated.capability_id, updated.arguments)] = task_id
        return updated

    def is_converged(self) -> bool:
        """Every task terminal and no `DISCOVERED`/`PLANNED`/`EXECUTING`
        work remains -- decidable today because the dedup rule above stops
        the planner from proposing fresh nodes for an already-answered
        question indefinitely (see `supervisor/convergence.py` for the
        fuller reasoning and its documented limit)."""
        return all(t.state in TERMINAL_STATES for t in self.tasks.values())

    def snapshot(self) -> dict:
        """Terminal-run-end snapshot for `RunStateV1.supervisor_state.task_graph_snapshot`
        (`MEM-001`) -- not designed for mid-run resume (`SCL-003`, out of scope)."""
        return {"tasks": [t.model_dump(mode="json") for t in self.tasks.values()]}
