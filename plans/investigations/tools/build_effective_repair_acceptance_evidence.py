# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: analysis_or_evidence_only
"""Build the task-specific proof that rereview follows only effective repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.state.mission_goal_schema import (  # noqa: E402
    MissionContributionEvidenceV1,
)
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)

TASK_ID = "L8-REVIEW-03-EFFECTIVE-REPAIR"
ACCEPTANCE = [
    "A repairable rejection changes the responsible bytes and resolves or narrows every "
    "cited finding"
]
FOCUSED_TESTS = [
    "tests/unit/test_readme_repair_validation.py",
    (
        "tests/unit/test_supervisor_loop.py::TestBasicLoop::"
        "test_local_poc_repairs_revalidates_and_rereviews_before_accepting"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestBasicLoop::"
        "test_local_poc_byte_identical_repair_reroutes_before_rereview"
    ),
    "tests/unit/test_independent_readme_review.py::TestBlockedVerdictNeverEntersRepairLoop",
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _validate_inventory(root: Path) -> str:
    inventory = root / "sha256sums.txt"
    expected: dict[str, str] = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        expected[relative] = digest
    actual = {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        ).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and path.name != "sha256sums.txt"
    }
    if actual != expected:
        raise ValueError("source repair-control evidence inventory is invalid")
    return _sha256(inventory)


def _run_focused_tests() -> dict[str, Any]:
    command = [
        str(REPO_ROOT / ".venv" / "Scripts" / "python"),
        "-m",
        "pytest",
        "-q",
        *FOCUSED_TESTS,
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"effective-repair focused proof failed:\n{result.stdout}\n{result.stderr}"
        )
    return {
        "command": ".venv/Scripts/python -m pytest -q " + " ".join(FOCUSED_TESTS),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "result": "PASS",
    }


def _derive_proof(source: Path) -> dict[str, Any]:
    negative = _read_json(source / "byte-identical-negative-control.json")
    positive = _read_json(source / "material-repair-positive-control.json")
    negative_receipt = negative["repair_receipt"]
    positive_receipt = positive["repair_receipt"]

    if (
        negative_receipt["candidate_changed"] is not False
        or negative_receipt["rereview_authorized"] is not False
        or negative_receipt["reviewer_call_count_before_rereview"] != 1
        or negative_receipt["reviewer_call_count_after_rereview"] is not None
    ):
        raise ValueError("byte-identical control does not prove review-call suppression")
    if (
        positive_receipt["candidate_changed"] is not True
        or not positive_receipt["changed_spans"]
        or not positive_receipt["changed_operation_ids"]
        or positive_receipt["resolved_finding_ids"] != ["quality.generic-overview"]
        or positive_receipt["unresolved_finding_ids"] != []
        or positive_receipt["reviewer_call_count_before_rereview"] != 1
        or positive_receipt["reviewer_call_count_after_rereview"] != 2
        or positive_receipt["rereview_authorized"] is not True
    ):
        raise ValueError("material repair control does not prove effective rereview")

    return {
        "schema_version": 1,
        "task_id": TASK_ID,
        "source_acceptance_bundle": source.relative_to(REPO_ROOT).as_posix(),
        "source_inventory_sha256": _validate_inventory(source),
        "byte_identical_control": {
            "candidate_changed": negative_receipt["candidate_changed"],
            "unresolved_finding_ids": negative_receipt["unresolved_finding_ids"],
            "reviewer_call_count_before_rereview": 1,
            "reviewer_call_count_after_rereview": None,
            "rereview_authorized": False,
        },
        "material_repair_control": {
            "before_candidate_sha256": positive_receipt["before_candidate_sha256"],
            "after_candidate_sha256": positive_receipt["after_candidate_sha256"],
            "changed_spans": positive_receipt["changed_spans"],
            "changed_operation_ids": positive_receipt["changed_operation_ids"],
            "addressed_finding_ids": positive_receipt["addressed_finding_ids"],
            "resolved_finding_ids": positive_receipt["resolved_finding_ids"],
            "unresolved_finding_ids": positive_receipt["unresolved_finding_ids"],
            "reviewer_call_count_before_rereview": 1,
            "reviewer_call_count_after_rereview": 2,
            "rereview_authorized": True,
        },
        "multi_finding_control": {
            "contract": "rereview remains denied until every cited finding has a responsible delta",
            "test": (
                "tests/unit/test_readme_repair_validation.py::"
                "test_every_cited_finding_must_have_a_responsible_delta_before_rereview"
            ),
            "result": "PASS",
        },
        "fact_block_control": {
            "contract": "fact and system blocks never enter generic README repair",
            "test": (
                "tests/unit/test_independent_readme_review.py::"
                "TestBlockedVerdictNeverEntersRepairLoop"
            ),
            "result": "PASS",
        },
        "product_remote_writes": 0,
        "acceptance": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    args = parser.parse_args(argv)

    source = args.source.resolve()
    output = args.output.resolve()
    head = _git("rev-parse", "HEAD")
    if head != args.control_head:
        raise ValueError(f"requested control HEAD {args.control_head} does not match {head}")
    if _git("status", "--porcelain"):
        raise ValueError("evidence must be generated from a clean committed control tree")
    if output.exists():
        raise ValueError(f"refusing to overwrite existing evidence directory: {output}")

    proof = _derive_proof(source)
    focused = _run_focused_tests()
    output.mkdir(parents=True)
    write_redacted_json(output / "effective-repair-proof.json", proof)
    write_redacted_json(
        output / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_revision": head,
            "focused_proof": focused,
            "prior_full_regression": {
                "source": (
                    "plans/investigations/evidence/level8-review-repair-controls-v1/"
                    "verification.json"
                ),
                "result": "PASS",
                "passed": 2116,
                "deselected": 41,
            },
            "independent_verification": {
                "method": "re-derived source bundle checksums and every repair-call predicate",
                "result": "PASS",
            },
            "product_remote_writes": 0,
            "result": "PASS",
        },
    )

    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    proof_refs = [
        (output / "effective-repair-proof.json").relative_to(REPO_ROOT).as_posix(),
        (output / "verification.json").relative_to(REPO_ROOT).as_posix(),
    ]
    contribution = MissionContributionEvidenceV1.model_validate(
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": ["GOAL-README"],
            "core_contribution": {
                "kind": "acceptance_proof",
                "summary": (
                    "Check candidate and operation deltas plus cited-finding resolution "
                    "before spending another independent review call."
                ),
            },
            "acceptance_checks_passed": ACCEPTANCE,
            "proof_refs": proof_refs,
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": True,
        }
    )
    write_redacted_json(output / "mission-contribution.json", contribution)
    write_redacted_text(
        output / "reproduction.txt",
        (
            ".venv/Scripts/python "
            "plans/investigations/tools/build_effective_repair_acceptance_evidence.py "
            "--source plans/investigations/evidence/level8-review-repair-controls-v1 "
            "--output plans/investigations/evidence/level8-review-effective-repair-v1 "
            f"--control-head {head}\n"
        ),
    )
    refresh_sha256sums(output)
    print(json.dumps(proof, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
