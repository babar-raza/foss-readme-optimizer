"""The single official verification suite this project's own governance requires before any wave
is declared closed (`plans/GOVERNANCE.md` rule 10 / `GOV-018`'s live-proof standard, `GOV-022`'s
wave-reconciliation gate). Runs, in order: ruff check, ruff format --check, mypy, the full non-live
pytest suite, `validate_plan_structure.py`, `check_verifiers_are_wired.py` (PRODSYS-P2-T1, warn-only
-- a `verify_*` function with no call site in `src/` gets flagged, never fails the build), and a
workflow-syntax check (`actionlint`, falling back to `act --list` as a best-effort secondary signal
since this environment has no Docker daemon for a real `act` dry-run).

This replaces manually re-typing the same five commands at every wave boundary -- exactly what
Wave 9.1 of the 2026-07-22 convergence-sprint plan calls for, so a wave never starts (or is
declared closed) against an unverified suite.

**Tree-precondition recording** (`DD-RECORD-EVIDENCE-PRECONDITIONS`, `plans/codex/production-
system-redesign.md`): every run records `git status --porcelain` at both start and end and labels
itself TREE CLEAN / TREE DIRTY / TREE MODIFIED DURING RUN accordingly. This closes a real, PROVEN
incident: 4 historical runs once produced 4 different results and were cited as "against the same
unchanged, already-committed tree" -- re-examination showed the tree was never actually frozen (the
ruff-format file count climbed mid-sequence, and the commit later cited as "the unchanged tree" was
made 68 seconds *after* the last attempt finished, not before the first). A dirty-tree or
modified-during-run label makes that class of mislabeling impossible to miss in the log again.

Usage: `.venv/Scripts/python.exe scripts/governance/run_official_checks.py`
Exit code 0 = every check passed. Exit code 1 = at least one check failed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON_CANDIDATES = (
    REPO_ROOT / ".venv" / "Scripts" / "python.exe",
    REPO_ROOT / ".venv" / "bin" / "python",
)


def _python() -> str:
    for candidate in VENV_PYTHON_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _git_status_porcelain() -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def _print_tree_precondition(label: str, status: str) -> None:
    print(f"\n=== Tree precondition ({label}) ===")
    if not status.strip():
        print("TREE CLEAN")
    else:
        print("TREE DIRTY -- this run's evidence is NOT proof about any specific committed state:")
        for line in status.splitlines():
            print(f"  {line}")


def _run(label: str, command: list[str], *, required: bool = True) -> bool:
    print(f"\n=== {label} ===")
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=REPO_ROOT)
    ok = completed.returncode == 0
    if not ok:
        severity = "FAILED" if required else "FAILED (best-effort, not blocking)"
        print(f"--- {label}: {severity} (exit {completed.returncode})")
    else:
        print(f"--- {label}: OK")
    return ok or not required


def main() -> int:
    python = _python()
    all_ok = True

    status_at_start = _git_status_porcelain()
    _print_tree_precondition("start", status_at_start)

    all_ok &= _run("ruff check", [python, "-m", "ruff", "check", "."])
    all_ok &= _run("ruff format --check", [python, "-m", "ruff", "format", "--check", "."])
    all_ok &= _run("mypy src", [python, "-m", "mypy", "src"])
    all_ok &= _run("pytest -q (full non-live suite)", [python, "-m", "pytest", "-q"])
    all_ok &= _run(
        "validate_plan_structure.py",
        [python, str(REPO_ROOT / "scripts" / "governance" / "validate_plan_structure.py")],
    )
    _run(
        "check_verifiers_are_wired.py (PRODSYS-P2-T1, warn-only)",
        [python, str(REPO_ROOT / "scripts" / "governance" / "check_verifiers_are_wired.py")],
        required=False,
    )

    workflows = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    actionlint = shutil.which("actionlint")
    if actionlint:
        all_ok &= _run(
            "actionlint (workflow syntax)",
            [actionlint, *[str(w) for w in workflows]],
        )
    else:
        print("\n=== actionlint (workflow syntax) ===")
        print("--- actionlint not found on PATH -- skipped (install it for a real syntax check)")
        act = shutil.which("act")
        if act:
            _run(
                "act --list (best-effort, no Docker daemon assumed)",
                [act, "--list"],
                required=False,
            )

    status_at_end = _git_status_porcelain()
    _print_tree_precondition("end", status_at_end)
    tree_modified_during_run = status_at_start != status_at_end
    if tree_modified_during_run:
        print(
            "TREE MODIFIED DURING THIS RUN -- the start and end git status differ. This run's "
            "results must not be cited as evidence about any single, specific commit; the tree "
            "changed while the checks were executing."
        )

    print("\n" + ("=" * 60))
    tree_label = (
        "TREE MODIFIED DURING RUN"
        if tree_modified_during_run
        else ("TREE DIRTY" if status_at_start.strip() else "TREE CLEAN")
    )
    print(f"Tree state: {tree_label}")
    if all_ok:
        print("All official checks passed.")
        return 0
    print("At least one required official check failed -- see output above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
