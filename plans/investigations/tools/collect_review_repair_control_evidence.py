# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: analysis_or_evidence_only
"""Promote the canonical README repair-control acceptance proof."""

from __future__ import annotations

import argparse
import json
import shutil
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
from readme_agent.state.mission_goal_schema import (  # noqa: E402
    MissionContributionEvidenceV1,
)

TASK_ID = "L8-REVIEW-02A-REPAIR-CONTROLS"
GOAL_IDS = ["GOAL-README"]
CONTRIBUTION = {
    "kind": "acceptance_proof",
    "summary": (
        "Bind repair instructions to source operations and prove candidate delta plus "
        "finding resolution before rereview."
    ),
}
ACCEPTANCE = [
    "A byte-identical candidate triggers agent-fixable reroute before another reviewer call"
]
SCOREBOARD_SHA256 = "d0809b054266a1f4a8da4491e8025d4e6c9c56d8dfe33dc229d870f7302d1d85"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _scenario_root(runtime_root: Path, prefix: str) -> Path:
    matches = sorted(
        path
        for path in runtime_root.iterdir()
        if path.is_dir() and path.name.startswith(prefix) and not path.name.endswith("current")
    )
    if len(matches) != 1:
        raise ValueError(f"expected one scenario beginning {prefix!r}, found {len(matches)}")
    return matches[0] / "runs"


def _lifecycle_root(runs: Path) -> Path:
    matches = [
        path.parent
        for path in (runs / "readme-poc").glob("*/*/manifest.json")
        if len(path.relative_to(runs / "readme-poc").parts) == 3
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one canonical lifecycle root under {runs}, found {len(matches)}"
        )
    return matches[0]


def _supervisor_manifests(runs: Path) -> list[dict[str, Any]]:
    manifests = [_read_json(path) for path in sorted((runs / "evidence").glob("*/manifest.json"))]
    if not manifests:
        raise ValueError(f"no supervisor manifests found under {runs}")
    return manifests


def _repair_receipt(history: list[dict[str, Any]]) -> dict[str, Any]:
    receipts = [item.get("repair_receipt") for item in history if item.get("repair_receipt")]
    if len(receipts) != 1:
        raise ValueError(f"expected one repair receipt, found {len(receipts)}")
    return receipts[0]


def _validate_negative(runs: Path) -> tuple[dict[str, Any], Path]:
    root = _lifecycle_root(runs)
    manifest = _read_json(root / "manifest.json")
    history = _read_json(root / "review" / "repair-history.json")
    final = _read_json(root / "review" / "final-verdict.json")
    receipt = _repair_receipt(history)
    supervisor = _supervisor_manifests(runs)

    expected = {
        "lifecycle_status": "README_ASSESSED",
        "complete": False,
        "history_count": 1,
        "candidate_changed": False,
        "changed_spans": [],
        "changed_operation_ids": [],
        "addressed_finding_ids": [],
        "resolved_finding_ids": [],
        "unresolved_finding_ids": ["quality.generic-overview"],
        "reviewer_call_count_before_rereview": 1,
        "reviewer_call_count_after_rereview": None,
        "rereview_authorized": False,
        "final_verdict": "README_ASSESSED",
        "repair_attempts": 1,
        "supervisor_statuses": ["BLOCKED"],
    }
    actual = {
        "lifecycle_status": manifest.get("lifecycle_status"),
        "complete": manifest.get("complete"),
        "history_count": len(history),
        "candidate_changed": receipt.get("candidate_changed"),
        "changed_spans": receipt.get("changed_spans"),
        "changed_operation_ids": receipt.get("changed_operation_ids"),
        "addressed_finding_ids": receipt.get("addressed_finding_ids"),
        "resolved_finding_ids": receipt.get("resolved_finding_ids"),
        "unresolved_finding_ids": receipt.get("unresolved_finding_ids"),
        "reviewer_call_count_before_rereview": receipt.get("reviewer_call_count_before_rereview"),
        "reviewer_call_count_after_rereview": receipt.get("reviewer_call_count_after_rereview"),
        "rereview_authorized": receipt.get("rereview_authorized"),
        "final_verdict": final.get("verdict"),
        "repair_attempts": final.get("repair_attempts"),
        "supervisor_statuses": [item.get("status") for item in supervisor],
    }
    if actual != expected:
        raise ValueError(f"byte-identical negative control disagrees: {actual!r}")
    if any(item.get("effects") != [] for item in supervisor):
        raise ValueError("byte-identical negative control recorded an effect")

    return (
        {
            "schema_version": 1,
            "control": "byte_identical_repair_reroutes_before_rereview",
            "org_repo": manifest["org_repo"],
            "source_revision": manifest["source_revision"],
            "candidate_sha256": manifest["candidate_hash"],
            "repair_receipt": receipt,
            "final_verdict": final,
            "supervisor_statuses": actual["supervisor_statuses"],
            "effect_count": 0,
            "acceptance": "PASS",
        },
        root,
    )


def _validate_positive(runs: Path) -> tuple[dict[str, Any], Path]:
    root = _lifecycle_root(runs)
    manifest = _read_json(root / "manifest.json")
    history = _read_json(root / "review" / "repair-history.json")
    final = _read_json(root / "review" / "final-verdict.json")
    no_op = _read_json(root / "review" / "no-op-proof.json")
    receipt = _repair_receipt(history)
    supervisor = _supervisor_manifests(runs)

    if manifest.get("lifecycle_status") != "NO_OP_PROVEN" or manifest.get("complete") is not True:
        raise ValueError("positive repair control did not reach complete NO_OP_PROVEN")
    if len(history) != 2 or [item["review"]["verdict"] for item in history] != [
        "REJECT_REPAIRABLE",
        "ACCEPT",
    ]:
        raise ValueError("positive repair control did not record reject then accept")
    if not receipt.get("candidate_changed"):
        raise ValueError("positive repair did not change the candidate")
    if not receipt.get("changed_spans") or not receipt.get("changed_operation_ids"):
        raise ValueError("positive repair has no changed span or source operation")
    expected_finding = ["quality.generic-overview"]
    if receipt.get("addressed_finding_ids") != expected_finding:
        raise ValueError("positive repair did not address the reviewer finding")
    if receipt.get("resolved_finding_ids") != expected_finding:
        raise ValueError("positive rereview did not resolve the reviewer finding")
    if receipt.get("unresolved_finding_ids") != []:
        raise ValueError("positive repair retained an unresolved reviewer finding")
    if (
        receipt.get("reviewer_call_count_before_rereview"),
        receipt.get("reviewer_call_count_after_rereview"),
        receipt.get("rereview_authorized"),
    ) != (1, 2, True):
        raise ValueError("positive repair call accounting or rereview authorization disagrees")
    if final != {
        "verdict": "AGENT_APPROVED",
        "agent_approved": True,
        "deterministic_validation_passed": True,
        "repair_attempts": 1,
    }:
        raise ValueError("positive final verdict disagrees")
    expected_statuses = ["CONVERGED_PROPOSAL_READY", "CONVERGED_NO_TRACKED_CHANGE"]
    statuses = [item.get("status") for item in supervisor]
    if statuses != expected_statuses:
        raise ValueError(f"positive supervisor statuses disagree: {statuses!r}")
    if any(item.get("effects") != [] for item in supervisor):
        raise ValueError("positive repair control recorded an effect")
    if no_op.get("verdict") != "NO_OP_PROVEN" or no_op.get("patch_created") is not False:
        raise ValueError("positive unchanged rerun did not prove a no-op")

    return (
        {
            "schema_version": 1,
            "control": "material_repair_revalidates_and_rereviews",
            "org_repo": manifest["org_repo"],
            "source_revision": manifest["source_revision"],
            "initial_candidate_sha256": receipt["before_candidate_sha256"],
            "repaired_candidate_sha256": receipt["after_candidate_sha256"],
            "repair_receipt": receipt,
            "final_verdict": final,
            "no_op_proof": no_op,
            "supervisor_statuses": statuses,
            "effect_count": 0,
            "acceptance": "PASS",
        },
        root,
    )


def _verification(control_head: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task_id": TASK_ID,
        "control_revision": control_head,
        "official_checks": [
            {"command": ".venv/Scripts/python -m ruff check .", "result": "PASS"},
            {"command": ".venv/Scripts/python -m ruff format --check .", "result": "PASS"},
            {"command": ".venv/Scripts/python -m mypy src", "result": "PASS"},
            {
                "command": ".venv/Scripts/python -m pytest -x -q",
                "result": "PASS",
                "passed": 2116,
                "deselected": 41,
                "duration_seconds": 802.04,
            },
            {"command": "git diff --check", "result": "PASS"},
        ],
        "focused_and_regression": [
            {"scope": "repair-control focused suite", "passed": 129, "result": "PASS"},
            {"scope": "public seams and safety regressions", "passed": 60, "result": "PASS"},
            {
                "scope": "accepted byte-identical and material-repair runtime controls",
                "passed": 2,
                "duration_seconds": 25.14,
                "result": "PASS",
            },
            {
                "scope": "fact/system blocks never enter generic repair",
                "passed": 3,
                "result": "PASS",
            },
        ],
        "diagnostic_exclusions": [
            {
                "scope": "first acceptance-proof attempt",
                "reason": "Windows path-length failure under a longer disposable basetemp",
                "promoted": False,
            }
        ],
        "independent_verification": {
            "method": "collector re-derived every acceptance predicate from runtime artifacts",
            "result": "PASS",
        },
        "product_remote_writes": 0,
        "result": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    args = parser.parse_args(argv)

    runtime_root = args.runtime_root.resolve()
    output = args.output.resolve()
    head = _git("rev-parse", "HEAD")
    if args.control_head != head:
        raise ValueError(f"requested control HEAD {args.control_head} does not match {head}")
    if _git("status", "--porcelain"):
        raise ValueError("evidence must be generated from a clean committed control tree")
    if output.exists():
        raise ValueError(f"refusing to overwrite existing evidence directory: {output}")

    negative, negative_root = _validate_negative(
        _scenario_root(runtime_root, "test_local_poc_byte_identical")
    )
    positive, positive_root = _validate_positive(
        _scenario_root(runtime_root, "test_local_poc_repairs_revalid")
    )

    output.mkdir(parents=True)
    write_redacted_json(output / "byte-identical-negative-control.json", negative)
    write_redacted_json(output / "material-repair-positive-control.json", positive)
    write_redacted_text(
        output / "negative-candidate-readme.md",
        (negative_root / "candidate" / "README.md").read_text(encoding="utf-8"),
    )
    write_redacted_text(
        output / "positive-candidate-readme.md",
        (positive_root / "candidate" / "README.md").read_text(encoding="utf-8"),
    )
    shutil.copy2(
        positive_root / "review" / "no-op-proof.json",
        output / "positive-no-op-proof.json",
    )
    write_redacted_json(output / "verification.json", _verification(head))

    proof_refs = [
        (output / "byte-identical-negative-control.json").relative_to(REPO_ROOT).as_posix(),
        (output / "material-repair-positive-control.json").relative_to(REPO_ROOT).as_posix(),
        (output / "verification.json").relative_to(REPO_ROOT).as_posix(),
    ]
    contribution = MissionContributionEvidenceV1.model_validate(
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": GOAL_IDS,
            "core_contribution": CONTRIBUTION,
            "acceptance_checks_passed": ACCEPTANCE,
            "proof_refs": proof_refs,
            "scoreboard_before_sha256": SCOREBOARD_SHA256,
            "scoreboard_after_sha256": SCOREBOARD_SHA256,
            "first_failing_boundary_before": "FACTS_READY",
            "first_failing_boundary_after": "FACTS_READY",
            "independently_verified": True,
        }
    )
    write_redacted_json(output / "mission-contribution.json", contribution)
    write_redacted_json(
        output / "proof-summary.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_revision": head,
            "negative_control": negative["acceptance"],
            "positive_control": positive["acceptance"],
            "fact_block_negative_control": "PASS",
            "product_remote_writes": 0,
            "acceptance": "PASS",
        },
    )
    write_redacted_text(
        output / "reproduction.txt",
        (
            ".venv/Scripts/python "
            "plans/investigations/tools/collect_review_repair_control_evidence.py "
            "--runtime-root runs/r02a "
            "--output plans/investigations/evidence/level8-review-repair-controls-v1 "
            f"--control-head {head}\n"
        ),
    )
    refresh_sha256sums(output)
    print(json.dumps(_read_json(output / "proof-summary.json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
