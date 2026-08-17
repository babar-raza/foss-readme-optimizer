"""Fix a real self-caused bug in two taskcards' `execution_focus.repository_scope`:
`platform:cross-platform` was written meaning "unrestricted," but `mission_execution_guard.py::
_repository_matches_scope` has no wildcard concept -- a `platform:<name>` token is matched
case-insensitively against a real registry entry's `platform` field (`.NET`, `Python`, `Java`,
`Cpp`, `Go`, `Rust`, `TypeScript` per `data/products.json`'s actual values), and no repository has
`platform="cross-platform"`, so the token could never admit anything. Confirmed live 2026-08-17:
`readme-agent supervise --repo aspose-cells-foss/Aspose.Cells-FOSS-for-.NET --bounded-verified-
canary --mission-task-id L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY` failed with "repository
... is outside immediate goal ...: ['platform:cross-platform']" despite the task's own stated
intent (cross-platform portfolio delivery). Every other real taskcard in this graph already lists
concrete platform tokens (e.g. `platform:.NET`, `platform:Python`) -- this replaces the invented
"cross-platform" token with the same real, explicit list for both affected tasks.
"""

from __future__ import annotations

from pathlib import Path

import yaml

GRAPH_PATH = Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")

_AFFECTED_TASK_IDS = {
    "L8-FRESH-00-FRESHNESS-SERVICE",
    "L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY",
}
_REAL_PLATFORM_TOKENS = [
    "platform:net",
    "platform:python",
    "platform:java",
    "platform:cpp",
    "platform:go",
    "platform:rust",
    "platform:typescript",
]


def main() -> None:
    raw = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))

    fixed = []
    for task in raw["taskcards"]:
        if task["task_id"] not in _AFFECTED_TASK_IDS:
            continue
        focus = task.get("execution_focus")
        if focus is None:
            continue
        if focus.get("repository_scope") == ["platform:cross-platform"]:
            focus["repository_scope"] = list(_REAL_PLATFORM_TOKENS)
            fixed.append(task["task_id"])

    if not fixed:
        raise SystemExit("expected at least one taskcard with the buggy scope; found none")

    GRAPH_PATH.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"fixed repository_scope on: {', '.join(sorted(fixed))}")


if __name__ == "__main__":
    main()
