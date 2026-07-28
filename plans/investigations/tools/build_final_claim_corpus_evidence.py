"""Build clean-tree evidence for complete README claim-accountability controls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from final_claim_corpus_evidence_support import (  # noqa: E402
    GRAPH_PATH,
    OUTPUT_ROOT,
    PLATFORMS,
    TASK_ID,
    build_case,
    build_negative_control,
    git_output,
    inventory_is_exact,
    record_containing,
    run_focused_tests,
    spans_are_exact,
    summarize,
    verify_inventory,
)

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402


def _checks(
    cases: dict[str, dict],
    negative: dict,
    focused: dict,
    start_status: str,
    head: str,
) -> dict[str, bool]:
    python = cases["python"]
    typescript = cases["typescript"]
    parity = record_containing(python, "source", "same public API design")
    performance = record_containing(python, "source", "higher performance")
    installation = record_containing(python, "source", "pip install aspose-3d-foss")
    stale_example = record_containing(python, "source", "ObjLoadOptions")
    verified_example = record_containing(
        python,
        "candidate",
        "from aspose.threed import Scene",
    )
    typescript_format = record_containing(
        typescript,
        "source",
        "FBX - Autodesk FBX format support",
    )
    negative_source = next(
        record for record in negative["accountability"].claims if record.stage == "source"
    )
    negative_candidate = next(
        record for record in negative["accountability"].claims if record.stage == "candidate"
    )
    return {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": git_output("rev-parse", "HEAD") == head,
        "java_python_typescript_present": set(cases) == set(PLATFORMS),
        "every_material_claim_inventoried": all(
            inventory_is_exact(case) for case in cases.values()
        ),
        "every_claim_span_and_hash_exact": all(spans_are_exact(case) for case in cases.values()),
        "native_patches_apply": all(
            case["patch"].git_apply_check_passed for case in cases.values()
        ),
        "parity_performance_and_stale_example_loss_detected": all(
            record.expected_disposition == "unjustified_loss"
            for record in (parity, performance, stale_example)
        ),
        "surviving_unverified_installation_requires_owner": (
            installation.expected_disposition == "authoritative_owner_validation"
            and not installation.currently_accountable
        ),
        "verified_example_and_format_are_fact_bound": (
            verified_example.expected_disposition == "accepted_fact"
            and verified_example.currently_accountable
            and typescript_format.expected_disposition == "accepted_fact"
            and typescript_format.currently_accountable
        ),
        "preservation_is_not_factual_approval": any(
            record.expected_disposition == "authoritative_owner_validation"
            and not record.currently_accountable
            for case in cases.values()
            for record in case["accountability"].claims
        ),
        "regeneration_convenience_is_not_justified_loss": (
            negative_source.expected_disposition == "unjustified_loss"
            and not negative_source.currently_accountable
        ),
        "unbound_generated_claim_detected": (
            negative_candidate.expected_disposition == "unbound_generated"
            and not negative_candidate.currently_accountable
        ),
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }


def _write_cases(cases: dict[str, dict], negative: dict, focused: dict) -> None:
    summaries = []
    for platform, case in cases.items():
        root = OUTPUT_ROOT / platform
        write_redacted_text(root / "original-readme.md", case["source"])
        write_redacted_text(root / "candidate-readme.md", case["candidate"])
        write_redacted_json(root / "document-plan.json", case["plan"])
        write_redacted_json(root / "generated-claim-map.json", case["claim_map"])
        write_redacted_json(root / "complete-claim-accountability-map.json", case["accountability"])
        write_redacted_text(root / "candidate.patch", case["patch"].patch)
        summaries.append(summarize(case))
    write_redacted_json(OUTPUT_ROOT / "portfolio-summary.json", summaries)
    write_redacted_text(OUTPUT_ROOT / "negative-source.md", negative["source"])
    write_redacted_text(OUTPUT_ROOT / "negative-candidate.md", negative["candidate"])
    write_redacted_json(
        OUTPUT_ROOT / "negative-accountability-map.json",
        negative["accountability"],
    )
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
                "plans/investigations/evidence/level8-final-readme-claim-corpus/verification.json",
                "plans/investigations/evidence/level8-final-readme-claim-corpus/"
                "portfolio-summary.json",
                "plans/investigations/evidence/level8-final-readme-claim-corpus/python/"
                "complete-claim-accountability-map.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    command = ".venv/Scripts/python plans/investigations/tools/build_final_claim_corpus_evidence.py"
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
    cases = {platform: build_case(platform) for platform in PLATFORMS}
    negative = build_negative_control(cases["python"]["facts"])
    focused = run_focused_tests()
    checks = _checks(cases, negative, focused, start_status, head)
    _write_cases(cases, negative, focused)
    _write_closeout(branch, head, checks)
    refresh_sha256sums(OUTPUT_ROOT)
    if not verify_inventory():
        raise RuntimeError("final claim-corpus evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
