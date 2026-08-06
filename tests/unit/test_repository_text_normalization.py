"""Prove hash-bound repository text has clone-stable line endings."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HASH_BOUND_PATHS = (
    "plans/requirements/catalog.jsonl",
    "plans/decisions/catalog.jsonl",
    "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
    "plans/investigations/evidence/presentation-golden-sample-v1/README.md",
    "src/readme_agent/facts/acceptance_contract.py",
    "templates/readme/repository-presentation-v1.json",
)


def test_hash_bound_text_is_checked_out_with_lf_on_every_platform() -> None:
    completed = subprocess.run(
        ["git", "check-attr", "eol", "--", *HASH_BOUND_PATHS],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    attributes = {
        line.split(": ", 2)[0]: line.split(": ", 2)[2] for line in completed.stdout.splitlines()
    }
    assert attributes == {path: "lf" for path in HASH_BOUND_PATHS}
