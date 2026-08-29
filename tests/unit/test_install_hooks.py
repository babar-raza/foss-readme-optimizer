"""The pre-commit hook template wires in all five steps in the right order, and
installs to a given repo root without touching this repo's own real hooks."""

from __future__ import annotations

from pathlib import Path

from scripts.governance.install_hooks import (
    PRE_COMMIT_HOOK_SCRIPT,
    install_pre_commit_hook,
)


def test_pre_commit_template_runs_all_five_steps_in_order() -> None:
    steps = [
        "validate_plan_structure.py",
        "ruff check",
        "ruff format --check",
        "mypy src",
        "validate_pinned_hash_dedicated_tests.py",
        "validate_governance_write_lock.py",
    ]
    positions = [PRE_COMMIT_HOOK_SCRIPT.index(step) for step in steps]
    assert positions == sorted(positions)


def test_dedicated_test_gate_is_blocking_and_governance_lock_is_not() -> None:
    dedicated_line = next(
        line
        for line in PRE_COMMIT_HOOK_SCRIPT.splitlines()
        if "validate_pinned_hash_dedicated_tests.py" in line and not line.startswith("#")
    )
    lock_line = next(
        line
        for line in PRE_COMMIT_HOOK_SCRIPT.splitlines()
        if "validate_governance_write_lock.py" in line and not line.startswith("#")
    )
    assert "|| exit 1" in dedicated_line
    assert "|| exit 1" not in lock_line


def test_install_pre_commit_hook_writes_the_template(tmp_path: Path) -> None:
    hook_path = install_pre_commit_hook(repo_root=tmp_path)
    assert hook_path == tmp_path / ".git" / "hooks" / "pre-commit"
    assert hook_path.read_text(encoding="utf-8") == PRE_COMMIT_HOOK_SCRIPT
