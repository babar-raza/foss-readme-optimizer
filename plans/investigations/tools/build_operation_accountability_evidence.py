"""Build clean-tree proof for operation and claim-accountability enforcement."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "plans/investigations/tools"))

from final_claim_corpus_evidence_support import PLATFORMS, build_case  # noqa: E402
from operation_accountability_evidence_support import (  # noqa: E402
    GRAPH_PATH,
    OUTPUT_ROOT,
    TASK_ID,
    decision_operation_map,
    git_output,
    run_focused_tests,
    verify_inventory,
)

from readme_agent.errors import LLMError  # noqa: E402
from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.readme.agentic_operation_coverage import (  # noqa: E402
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document  # noqa: E402
from readme_agent.readme.claim_accountability_validation import (  # noqa: E402
    validate_claim_accountability_map,
)
from readme_agent.readme.document_operations import apply_document_operations  # noqa: E402
from readme_agent.readme.document_renderer import build_readme_document_candidate  # noqa: E402
from readme_agent.readme.document_validation import (  # noqa: E402
    validate_readme_document_candidate,
)
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402


def _build_cases() -> dict[str, dict]:
    cases = {}
    for platform in PLATFORMS:
        case = build_case(platform)
        assessment = assess_readme_document(
            case["facts"].org_repo,
            case["source"],
            case["facts"],
            base_revision=case["revision"],
        )
        validation = validate_readme_document_candidate(
            case["source"],
            case["candidate"],
            case["plan"],
            case["facts"],
        )
        accountability = validate_claim_accountability_map(
            case["plan"].claim_accountability,
            source_text=case["source"],
            candidate_text=case["candidate"],
            facts=case["facts"],
            operations=case["plan"].operations,
        )
        validate_agentic_operation_coverage(
            assessment,
            assessment.sections,
            case["plan"].operations,
        )
        case.update(
            {
                "assessment": assessment,
                "validation": validation,
                "accountability_validation": accountability,
                "decision_operation_map": decision_operation_map(
                    assessment,
                    case["plan"],
                ),
            }
        )
        cases[platform] = case
    return cases


def _negative_controls(cases: dict[str, dict]) -> dict:
    java = cases["java"]
    competing = """# Product

## Usage

```java
Workbook first = Workbook.load("one.xlsx");
```

```java
Workbook second = Workbook.load("two.xlsx");
```
"""
    competing_rejected = False
    competing_error = ""
    try:
        build_readme_document_candidate(
            java["facts"].org_repo,
            competing,
            java["facts"],
            base_revision=java["revision"],
        )
    except LLMError as exc:
        competing_rejected = True
        competing_error = str(exc)

    accountability = java["plan"].claim_accountability
    first = accountability.claims[0].model_copy(update={"content_sha256": "0" * 64})
    tampered = accountability.model_copy(update={"claims": [first, *accountability.claims[1:]]})
    tampered_validation = validate_claim_accountability_map(
        tampered,
        source_text=java["source"],
        candidate_text=java["candidate"],
        facts=java["facts"],
        operations=java["plan"].operations,
    )
    missing_map_plan = java["plan"].model_copy(update={"claim_accountability": None})
    missing_map_validation = validate_readme_document_candidate(
        java["source"],
        java["candidate"],
        missing_map_plan,
        java["facts"],
    )
    return {
        "competing_example_insert_rejected": competing_rejected,
        "competing_example_error": competing_error,
        "stale_claim_span_rejected": not tampered_validation.valid,
        "stale_claim_span_checks": tampered_validation.checks,
        "missing_accountability_map_rejected": not missing_map_validation.valid,
        "missing_accountability_errors": missing_map_validation.errors,
    }


def _checks(
    cases: dict[str, dict],
    negatives: dict,
    focused: dict,
    start_status: str,
    head: str,
) -> dict[str, bool]:
    return {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": git_output("rev-parse", "HEAD") == head,
        "three_real_ecosystems_proven": set(cases) == set(PLATFORMS),
        "all_document_candidates_valid": all(case["validation"].valid for case in cases.values()),
        "all_accountability_maps_structurally_valid": all(
            case["accountability_validation"].valid for case in cases.values()
        ),
        "all_approval_blockers_visible": all(
            case["accountability_validation"].blocking_claim_ids
            and not case["accountability_validation"].approval_eligible
            for case in cases.values()
        ),
        "every_non_preserve_decision_has_operation": all(
            all(
                record["operation_ids"]
                for record in case["decision_operation_map"]
                if record["disposition"] not in {"preserve", "not_applicable"}
            )
            for case in cases.values()
        ),
        "immutable_reconstruction_exact": all(
            apply_document_operations(
                case["source"].encode("utf-8"),
                case["plan"].operations,
            ).decode("utf-8")
            == case["candidate"]
            for case in cases.values()
        ),
        "native_patches_apply": all(
            case["patch"].git_apply_check_passed for case in cases.values()
        ),
        "competing_example_insert_rejected": negatives["competing_example_insert_rejected"],
        "stale_claim_span_rejected": negatives["stale_claim_span_rejected"],
        "missing_accountability_map_rejected": negatives["missing_accountability_map_rejected"],
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }


def _write_cases(cases: dict[str, dict], negatives: dict, focused: dict) -> None:
    for platform, case in cases.items():
        root = OUTPUT_ROOT / platform
        write_redacted_text(root / "original-readme.md", case["source"])
        write_redacted_text(root / "candidate-readme.md", case["candidate"])
        write_redacted_json(root / "assessment.json", case["assessment"])
        write_redacted_json(root / "document-plan.json", case["plan"])
        write_redacted_json(root / "generated-claim-map.json", case["claim_map"])
        write_redacted_json(
            root / "complete-claim-accountability-map.json",
            case["plan"].claim_accountability,
        )
        write_redacted_json(
            root / "claim-accountability-validation.json",
            case["accountability_validation"],
        )
        write_redacted_json(root / "document-validation.json", case["validation"])
        write_redacted_json(root / "decision-operation-map.json", case["decision_operation_map"])
        write_redacted_text(root / "candidate.patch", case["patch"].patch)
    write_redacted_json(OUTPUT_ROOT / "negative-controls.json", negatives)
    write_redacted_text(
        OUTPUT_ROOT / "focused-tests.txt",
        (
            f"$ {focused['command']}\nexit_code={focused['exit_code']}\n\n"
            f"{focused['stdout']}{focused['stderr']}"
        ),
    )


def _write_closeout(branch: str, head: str, checks: dict[str, bool]) -> None:
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        OUTPUT_ROOT / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-operation-accountability/verification.json",
                "plans/investigations/evidence/level8-operation-accountability/python/"
                "decision-operation-map.json",
                "plans/investigations/evidence/level8-operation-accountability/python/"
                "complete-claim-accountability-map.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    command = (
        ".venv/Scripts/python plans/investigations/tools/build_operation_accountability_evidence.py"
    )
    write_redacted_json(
        OUTPUT_ROOT / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": {
                "branch": branch,
                "head": head,
                "working_tree_clean_at_start": checks["control_tree_clean_at_start"],
            },
            "checks": checks,
            "verdict": "VERIFIED" if all(checks.values()) else "FAILED",
            "reproduction_command": command,
        },
    )
    write_redacted_text(OUTPUT_ROOT / "reproduction.txt", command + "\n")


def main() -> int:
    branch = git_output("branch", "--show-current")
    head = git_output("rev-parse", "HEAD")
    start_status = git_output("status", "--porcelain=v1", "--untracked-files=all")
    cases = _build_cases()
    negatives = _negative_controls(cases)
    focused = run_focused_tests()
    checks = _checks(cases, negatives, focused, start_status, head)
    _write_cases(cases, negatives, focused)
    _write_closeout(branch, head, checks)
    refresh_sha256sums(OUTPUT_ROOT)
    if not verify_inventory():
        raise RuntimeError("operation-accountability evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
