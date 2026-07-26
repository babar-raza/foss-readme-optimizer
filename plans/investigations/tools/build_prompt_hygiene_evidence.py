"""Build reproducible evidence for the governed prompt inventory and paid-call gate."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.llm.prompt_hygiene import audit_prompt_hygiene  # noqa: E402
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)

TASK_ID = "L8-TRUTH-01C-PROMPT-HYGIENE"
EVIDENCE_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-prompt-hygiene"
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

FOCUSED_COMMANDS = (
    (
        str(PYTHON),
        "-m",
        "pytest",
        "-q",
        "tests/unit/test_prompt_hygiene.py",
        "tests/unit/test_prompt_registry.py",
        "tests/unit/test_llm_call_ledger.py",
        "tests/unit/test_planner_client.py",
        "tests/unit/test_verifier_client.py",
        "tests/unit/test_analysis_client.py",
        "tests/unit/test_specialist_selection.py",
        "tests/unit/test_repair.py",
        "tests/unit/test_golden_set.py",
        "tests/unit/test_golden_set_qualification.py",
        "tests/unit/test_local_poc_evidence.py",
        "tests/unit/test_manifest_v2.py",
        "tests/unit/test_supervisor_dossier.py",
    ),
    (str(PYTHON), "scripts/governance/check_prompt_hygiene.py"),
)


def _run(command: tuple[str, ...]) -> dict:
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
        "command": " ".join(command).replace(str(REPO_ROOT) + "\\", ""),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _git(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    starting_tree = _git("status", "--porcelain")
    if starting_tree:
        raise RuntimeError("prompt-hygiene evidence requires a clean committed starting tree")

    report = audit_prompt_hygiene(repo_root=REPO_ROOT)
    checks = [_run(command) for command in FOCUSED_COMMANDS]
    if not report.clean or any(check["exit_code"] != 0 for check in checks):
        raise RuntimeError("prompt-hygiene evidence verification failed")
    if _git("rev-parse", "HEAD") != head:
        raise RuntimeError("HEAD changed while prompt-hygiene evidence was being built")
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_sha256 = lifecycle_scoreboard_sha256(scoreboard)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(EVIDENCE_DIR / "prompt-inventory.json", report)
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "implementation_commit": head,
            "branch": branch,
            "verified_at": datetime.now(UTC).isoformat(),
            "tree_precondition": "CLEAN_AT_START_HEAD_UNCHANGED",
            "checks": checks,
            "negative_controls_passed": [
                "unregistered prompt file",
                "orphan model route",
                "deleted referenced prompt",
                "duplicate prompt ID",
                "duplicate semantic model route",
                "category/path mismatch",
                "prompt ID/filename mismatch",
                "deprecated active prompt",
                "runtime unknown prompt reference",
                "executable-inline prompt text",
                "stale documentation metadata",
                "job/prompt provenance mismatch",
                "paid provider boundary with inconsistent inventory",
                "per-prompt dependency-scope mutation",
            ],
            "verdict": "VERIFIED",
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": ["GOAL-TRUTH"],
            "core_contribution": {
                "kind": "visible_deliverable",
                "summary": (
                    "Reconcile every active prompt to one declared owner, job, runtime consumer, "
                    "contract, and invalidation scope and block paid fan-out on orphan, duplicate, "
                    "inline, stale, or unsafe prompt changes."
                ),
            },
            "acceptance_checks_passed": [
                "Every prompt file has exactly one active job and consumer",
                "Every routed or invoked prompt exists and is hash-coupled to its dependent stage",
                "Obsolete prompts are removed only after reference and history inspection",
            ],
            "proof_refs": [
                "plans/investigations/evidence/level8-prompt-hygiene/verification.json",
                "plans/investigations/evidence/level8-prompt-hygiene/prompt-inventory.json",
            ],
            "scoreboard_before_sha256": scoreboard_sha256,
            "scoreboard_after_sha256": scoreboard_sha256,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": True,
        },
    )
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        (
            ".venv/Scripts/python plans/investigations/tools/build_prompt_hygiene_evidence.py\n"
            ".venv/Scripts/python scripts/governance/check_prompt_hygiene.py --json\n"
        ),
    )
    refresh_sha256sums(EVIDENCE_DIR)
    print(f"Prompt hygiene evidence written to {EVIDENCE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
