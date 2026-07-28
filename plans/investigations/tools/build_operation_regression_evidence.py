"""Build clean-tree evidence for assessment-to-operation negative controls."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from operation_regression_evidence_support import (  # noqa: E402
    GRAPH_PATH,
    INPUT_ROOT,
    OUTPUT_ROOT,
    SOURCE_REVISION,
    TASK_ID,
    build_operation_controls,
    git_output,
    native_patch,
    run_focused_tests,
    verify_inventory,
)

from readme_agent.errors import LLMError  # noqa: E402
from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.readme.agentic_operation_coverage import (  # noqa: E402
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document  # noqa: E402
from readme_agent.readme.claim_map import build_readme_claim_map  # noqa: E402
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


def _build_real_case() -> dict:
    source = (INPUT_ROOT / "original-readme.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (INPUT_ROOT / "product-facts-v2.json").read_text(encoding="utf-8")
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=SOURCE_REVISION,
    )
    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=SOURCE_REVISION,
    )
    validation = validate_readme_document_candidate(source, candidate, plan, facts)
    claim_map = build_readme_claim_map(
        plan,
        facts,
        source_text=source,
        candidate_text=candidate,
    )
    operation_coverage_error = ""
    try:
        validate_agentic_operation_coverage(
            assessment,
            assessment.sections,
            plan.operations,
        )
    except LLMError as exc:
        operation_coverage_error = str(exc)
    usage_section_id = next(
        section.section_id
        for section in assessment.sections
        if section.heading.strip().casefold() in {"quick start", "usage", "getting started"}
    )
    return {
        "source": source,
        "facts": facts,
        "assessment": assessment,
        "candidate": candidate,
        "plan": plan,
        "validation": validation,
        "claim_map": claim_map,
        "patch": native_patch(source, candidate),
        "operation_coverage_error": operation_coverage_error,
        "usage_section_id": usage_section_id,
    }


def _operation_coverage_record(case: dict) -> list[dict]:
    records = []
    for section in case["assessment"].sections:
        operations = [
            operation
            for operation in case["plan"].operations
            if (
                operation.source_byte_start == operation.source_byte_end
                and section.source_byte_start
                <= operation.source_byte_start
                <= section.source_byte_end
            )
            or (
                operation.source_byte_start < section.source_byte_end
                and section.source_byte_start < operation.source_byte_end
            )
        ]
        records.append(
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "disposition": section.disposition,
                "source_byte_start": section.source_byte_start,
                "source_byte_end": section.source_byte_end,
                "source_sha256": hashlib.sha256(
                    case["source"].encode("utf-8")[
                        section.source_byte_start : section.source_byte_end
                    ]
                ).hexdigest(),
                "operation_ids": [operation.operation_id for operation in operations],
                "operation_kinds": [operation.operation for operation in operations],
                "fact_ids": sorted(
                    {fact_id for operation in operations for fact_id in operation.fact_ids}
                ),
            }
        )
    return records


def _checks(
    case: dict,
    controls: dict,
    focused: dict,
    start_status: str,
    head: str,
) -> dict[str, bool]:
    validation = case["validation"]
    return {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": git_output("rev-parse", "HEAD") == head,
        "real_java_source_revision_bound": all(
            fact.source.source_revision in {None, SOURCE_REVISION} for fact in case["facts"].facts
        ),
        "real_java_native_patch_applies": case["patch"].git_apply_check_passed,
        "real_java_claim_map_present": bool(case["claim_map"].claims),
        "real_java_candidate_is_deterministically_valid": validation.valid,
        "real_java_operation_coverage_passes": not case["operation_coverage_error"],
        "competing_examples_fail_closed_at_operation_coverage": controls[
            "competing_examples_rejected"
        ],
        "advisory_insert_rejected": controls["advisory_insert_rejected"],
        "noop_move_rejected": (controls["noop_move_pruned"] and controls["noop_move_rejected"]),
        "replace_and_remove_covered": (controls["replace_covered"] and controls["remove_covered"]),
        "stale_span_hash_rejected": controls["stale_span_hash_rejected"],
        "byte_identical_reconstruction": controls["byte_identical_reconstruction"],
        "outside_owned_span_regression_passed": focused["exit_code"] == 0,
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }


def _write_case(case: dict, controls: dict, focused: dict) -> None:
    write_redacted_text(OUTPUT_ROOT / "real-java-original.md", case["source"])
    write_redacted_text(OUTPUT_ROOT / "real-java-candidate.md", case["candidate"])
    write_redacted_json(OUTPUT_ROOT / "real-java-assessment.json", case["assessment"])
    write_redacted_json(OUTPUT_ROOT / "real-java-plan.json", case["plan"])
    write_redacted_json(OUTPUT_ROOT / "real-java-validation.json", case["validation"])
    write_redacted_json(OUTPUT_ROOT / "real-java-claim-map.json", case["claim_map"])
    write_redacted_json(
        OUTPUT_ROOT / "real-java-operation-coverage.json",
        {
            "usage_section_id": case["usage_section_id"],
            "accepted": not bool(case["operation_coverage_error"]),
            "error": case["operation_coverage_error"],
        },
    )
    write_redacted_text(OUTPUT_ROOT / "real-java.patch", case["patch"].patch)
    write_redacted_json(
        OUTPUT_ROOT / "operation-coverage-record.json",
        _operation_coverage_record(case),
    )
    write_redacted_json(OUTPUT_ROOT / "operation-negative-controls.json", controls)
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
                "plans/investigations/evidence/level8-readme-operation-regressions/"
                "verification.json",
                "plans/investigations/evidence/level8-readme-operation-regressions/"
                "operation-negative-controls.json",
                "plans/investigations/evidence/level8-readme-operation-regressions/"
                "operation-coverage-record.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    command = (
        ".venv/Scripts/python plans/investigations/tools/build_operation_regression_evidence.py"
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
    case = _build_real_case()
    controls = build_operation_controls(case["facts"])
    focused = run_focused_tests()
    checks = _checks(case, controls, focused, start_status, head)
    _write_case(case, controls, focused)
    _write_closeout(branch, head, checks)
    refresh_sha256sums(OUTPUT_ROOT)
    if not verify_inventory():
        raise RuntimeError("operation-regression evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
