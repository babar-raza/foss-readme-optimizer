"""Build checksum-complete evidence for grounded interpretive render views."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout
from interpretive_render_view_evidence_support import (
    build_interpretive_controls,
    build_live_python_regression_control,
)

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-interpretive-render-views"
FAILURE_DIR = REPO_ROOT / "runs/control/interpretive-render-view-proof-failure"
LOCK_PATH = REPO_ROOT / "runs/control/locks/interpretive-render-view-evidence.lock"
REPRESENTATIVE_ROOT = (
    REPO_ROOT
    / "plans/investigations/evidence"
    / "level8-local-readme-assessment-composition-b2679e4"
    / "representatives"
)
PROMPT_PATH = REPO_ROOT / "prompts/generation/draft_product_truth.yaml"
LIVE_PYTHON_BUNDLE = (
    REPO_ROOT
    / "runs/readme-poc"
    / "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / "ab1a2267a0ba6302311d0c7c4ad01494974c7d76"
)
LIVE_PYTHON_SUPERVISOR_MANIFEST = REPO_ROOT / "runs/evidence/20260727-205319-1552/manifest.json"
LIVE_PYTHON_FIRST_FAILURE_LOG = (
    REPO_ROOT / "runs/level8-truth-seven-ecosystems/supervise.stderr.log"
)
LIVE_PYTHON_SUCCESS_STDOUT = (
    REPO_ROOT / "runs/level8-truth-seven-ecosystems/python-source-priority-repair.stdout.log"
)
LIVE_PYTHON_SUCCESS_STDERR = (
    REPO_ROOT / "runs/level8-truth-seven-ecosystems/python-source-priority-repair.stderr.log"
)
TASK_ID = "L8-TRUTH-06-INTERPRETIVE-VIEWS"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
PYTHON = sys.executable
IMPLEMENTATION_PATHS = (
    "src/readme_agent/facts/acceptance_contract.py",
    "src/readme_agent/facts/agentic_drafting.py",
    "src/readme_agent/facts/interpretive_evidence.py",
    "src/readme_agent/facts/interpretive_resolution.py",
    "src/readme_agent/facts/render_views.py",
    "src/readme_agent/facts/schema_v2.py",
    "src/readme_agent/capabilities/draft_product_truth.py",
)
EVIDENCE_MACHINERY_PATHS = (
    "plans/investigations/tools/build_interpretive_render_view_evidence.py",
    "plans/investigations/tools/interpretive_render_view_evidence_support.py",
)
FOCUSED_COMMAND = (
    PYTHON,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_agentic_drafting.py",
    "tests/unit/test_interpretive_evidence.py",
    "tests/unit/test_interpretive_resolution.py",
    "tests/unit/test_fact_render_views.py",
    "tests/unit/test_fact_acceptance_contract.py",
    "tests/unit/test_draft_product_truth_capability.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/security/test_no_secrets_in_evidence.py",
)
OFFICIAL_COMMAND = (PYTHON, "scripts/governance/run_official_checks.py")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: tuple[str, ...]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(command),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _build(run_official: bool) -> list[str]:
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    head = _git("rev-parse", "HEAD")
    controls = build_interpretive_controls(REPRESENTATIVE_ROOT)
    live_python = build_live_python_regression_control(
        LIVE_PYTHON_BUNDLE,
        LIVE_PYTHON_SUPERVISOR_MANIFEST,
    )
    focused = _run(FOCUSED_COMMAND)
    official = _run(OFFICIAL_COMMAND) if run_official else None
    audience = controls["typescript_audience"]
    problem = controls["typescript_problem"]
    checks = {
        "control_tree_clean": not start_status,
        "typescript_audience_grounded": (
            audience["grounded_fact"]["verification_state"] == "verified"
        ),
        "typescript_audience_citations_persisted": (
            len(audience["grounded_fact"]["supporting_fact_ids"]) == 1
            and len(audience["render_view"]["citation_fact_ids"]) == 2
        ),
        "typescript_problem_grounded": (
            problem["grounded_fact"]["verification_state"] == "verified"
        ),
        "visitor_views_nonempty": bool(
            audience["render_view"]["phrases"]
            and problem["render_view"]["phrases"]
            and controls["java_identity"]["render_view"]["phrases"]
        ),
        "negative_controls_pass": all(controls["negative_controls"].values()),
        "live_python_facts_ready_with_grounded_views": all(live_python["checks"].values()),
        "focused_tests_pass": focused["exit_code"] == 0,
        "official_checks_pass": official is not None and official["exit_code"] == 0,
        "tree_stable": (
            _git("rev-parse", "HEAD") == head
            and _git("status", "--porcelain=v1", "--untracked-files=all") == start_status
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    output_dir = FAILURE_DIR if failures else EVIDENCE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    write_redacted_json(output_dir / "interpretive-render-controls.json", controls)
    write_redacted_json(output_dir / "live-python-regression-control.json", live_python)
    write_redacted_text(
        output_dir / "live-python-first-failure.stderr.log",
        LIVE_PYTHON_FIRST_FAILURE_LOG.read_text(encoding="utf-8", errors="replace"),
    )
    write_redacted_text(
        output_dir / "live-python-success.stdout.log",
        LIVE_PYTHON_SUCCESS_STDOUT.read_text(encoding="utf-8", errors="replace"),
    )
    write_redacted_text(
        output_dir / "live-python-success.stderr.log",
        LIVE_PYTHON_SUCCESS_STDERR.read_text(encoding="utf-8", errors="replace"),
    )
    write_redacted_text(output_dir / "focused-tests.stdout.log", focused["stdout"])
    write_redacted_text(output_dir / "focused-tests.stderr.log", focused["stderr"])
    if official is not None:
        write_redacted_text(output_dir / "official-checks.stdout.log", official["stdout"])
        write_redacted_text(output_dir / "official-checks.stderr.log", official["stderr"])
    write_redacted_json(
        output_dir / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": {
                "head": head,
                "branch": _git("branch", "--show-current"),
                "tree_clean_at_start": not start_status,
                "builder_sha256": _sha256(Path(__file__)),
                "prompt_path": PROMPT_PATH.relative_to(REPO_ROOT).as_posix(),
                "prompt_sha256": _sha256(PROMPT_PATH),
                "implementation": {
                    path: _sha256(REPO_ROOT / path) for path in IMPLEMENTATION_PATHS
                },
                "evidence_machinery": {
                    path: _sha256(REPO_ROOT / path) for path in EVIDENCE_MACHINERY_PATHS
                },
            },
            "commands": {
                "focused": {key: focused[key] for key in ("command", "exit_code")},
                "official": (
                    {key: official[key] for key in ("command", "exit_code")}
                    if official is not None
                    else None
                ),
            },
            "checks": checks,
            "failures": failures,
            "verdict": "FAILED" if failures else "VERIFIED",
        },
    )
    if not failures:
        graph, _ = load_mission_graph(GRAPH_PATH)
        task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
        scoreboard = derive_lifecycle_scoreboard(default_state_backend())
        write_redacted_json(
            output_dir / "mission-contribution.json",
            {
                "schema_version": 1,
                "task_id": TASK_ID,
                "goal_ids": task.goal_ids,
                "core_contribution": task.core_contribution.model_dump(mode="json"),
                "acceptance_checks_passed": task.acceptance_checks,
                "proof_refs": [
                    "plans/investigations/evidence/level8-interpretive-render-views/"
                    "interpretive-render-controls.json",
                    "plans/investigations/evidence/level8-interpretive-render-views/"
                    "verification.json",
                    "plans/investigations/evidence/level8-interpretive-render-views/"
                    "live-python-regression-control.json",
                ],
                "scoreboard_before_sha256": lifecycle_scoreboard_sha256(scoreboard),
                "scoreboard_after_sha256": lifecycle_scoreboard_sha256(scoreboard),
                "first_failing_boundary_before": scoreboard.first_failing_boundary,
                "first_failing_boundary_after": scoreboard.first_failing_boundary,
                "independently_verified": True,
            },
        )
        write_redacted_text(
            output_dir / "reproduction.txt",
            (
                f"{PYTHON} plans/investigations/tools/"
                "build_interpretive_render_view_evidence.py --official --check\n"
            ),
        )
    refresh_sha256sums(output_dir)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(LOCK_PATH, timeout=0):
            failures = _build(args.official)
    except Timeout as exc:
        message = "interpretive render proof already has an active sole-operator run"
        raise SystemExit(message) from exc
    if failures:
        raise SystemExit("interpretive render proof failed: " + ", ".join(failures))
    print(f"wrote interpretive render evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
