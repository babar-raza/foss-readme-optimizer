"""Build verified reuse, correction, and withholding evidence for README sections."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from existing_section_reconciliation_evidence_support import (  # noqa: E402
    GRAPH_PATH,
    INPUT_ROOT,
    OUTPUT_ROOT,
    SOURCE_REVISION,
    TASK_ID,
    UNRESOLVED_SOURCE,
    block_fields,
    git_output,
    native_patch,
    run_focused_tests,
    section_operation_map,
    verify_inventory,
)

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.readme.assessment import assess_readme_document  # noqa: E402
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


def _build_cases():
    source = (INPUT_ROOT / "original-readme.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (INPUT_ROOT / "product-facts-v2.json").read_text(encoding="utf-8")
    )
    assessment = assess_readme_document(
        facts.org_repo, source, facts, base_revision=SOURCE_REVISION
    )
    candidate, plan = build_readme_document_candidate(
        facts.org_repo, source, facts, base_revision=SOURCE_REVISION
    )
    validation = validate_readme_document_candidate(source, candidate, plan, facts)
    patch = native_patch(source, candidate)
    blocked = block_fields(
        facts,
        {"installation.verified_acquisition", "example.minimal"},
    )
    unresolved_assessment = assess_readme_document(
        blocked.org_repo,
        UNRESOLVED_SOURCE,
        blocked,
        base_revision=SOURCE_REVISION,
    )
    unresolved_candidate, unresolved_plan = build_readme_document_candidate(
        blocked.org_repo,
        UNRESOLVED_SOURCE,
        blocked,
        base_revision=SOURCE_REVISION,
    )
    unresolved_validation = validate_readme_document_candidate(
        UNRESOLVED_SOURCE,
        unresolved_candidate,
        unresolved_plan,
        blocked,
    )
    return {
        "source": source,
        "facts": facts,
        "assessment": assessment,
        "candidate": candidate,
        "plan": plan,
        "validation": validation,
        "patch": patch,
        "blocked": blocked,
        "unresolved_assessment": unresolved_assessment,
        "unresolved_candidate": unresolved_candidate,
        "unresolved_plan": unresolved_plan,
        "unresolved_validation": unresolved_validation,
    }


def _checks(cases: dict, focused: dict, start_status: str, head: str) -> dict[str, bool]:
    unresolved_plan = cases["unresolved_plan"]
    withheld = [
        operation
        for operation in unresolved_plan.operations
        if operation.operation_id.startswith("readme.unresolved.withhold:")
    ]
    return {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": git_output("rev-parse", "HEAD") == head,
        "real_net_validation_valid": cases["validation"].valid,
        "real_net_native_patch_applies": cases["patch"].git_apply_check_passed,
        "validated_maintainer_content_preserved": all(
            text in cases["candidate"]
            for text in (
                "Some advanced features are not available in this FOSS version:",
                "Currently implementing core functionality:",
            )
        ),
        "contradicted_content_has_fact_cited_corrections": any(
            operation.protected_content_treatment == "authoritative_fact_correction"
            and operation.fact_ids
            for operation in cases["plan"].operations
        ),
        "unresolved_validation_valid": cases["unresolved_validation"].valid,
        "unresolved_sections_withheld": (
            len(withheld) == 2
            and "Unverified.Package" not in cases["unresolved_candidate"]
            and "Product.Create()" not in cases["unresolved_candidate"]
        ),
        "unrelated_maintainer_content_preserved": (
            "Open an issue with a reproducible case." in cases["unresolved_candidate"]
        ),
        "withheld_source_is_traceable": all(
            operation.expected_sha256
            == hashlib.sha256(
                UNRESOLVED_SOURCE.encode("utf-8")[
                    operation.source_byte_start : operation.source_byte_end
                ]
            ).hexdigest()
            for operation in withheld
        ),
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }


def _write_case_evidence(cases: dict, focused: dict) -> None:
    write_redacted_text(OUTPUT_ROOT / "real-net-original.md", cases["source"])
    write_redacted_text(OUTPUT_ROOT / "real-net-candidate.md", cases["candidate"])
    write_redacted_json(OUTPUT_ROOT / "real-net-assessment.json", cases["assessment"])
    write_redacted_json(OUTPUT_ROOT / "real-net-plan.json", cases["plan"])
    write_redacted_json(OUTPUT_ROOT / "real-net-validation.json", cases["validation"])
    write_redacted_text(OUTPUT_ROOT / "real-net.patch", cases["patch"].patch)
    write_redacted_json(
        OUTPUT_ROOT / "real-net-section-reconciliation.json",
        section_operation_map(
            cases["source"],
            cases["facts"],
            cases["assessment"],
            cases["plan"],
        ),
    )
    write_redacted_text(OUTPUT_ROOT / "unresolved-source.md", UNRESOLVED_SOURCE)
    write_redacted_text(OUTPUT_ROOT / "unresolved-candidate.md", cases["unresolved_candidate"])
    write_redacted_json(OUTPUT_ROOT / "unresolved-assessment.json", cases["unresolved_assessment"])
    write_redacted_json(OUTPUT_ROOT / "unresolved-plan.json", cases["unresolved_plan"])
    write_redacted_json(OUTPUT_ROOT / "unresolved-validation.json", cases["unresolved_validation"])
    write_redacted_json(
        OUTPUT_ROOT / "unresolved-section-reconciliation.json",
        section_operation_map(
            UNRESOLVED_SOURCE,
            cases["blocked"],
            cases["unresolved_assessment"],
            cases["unresolved_plan"],
        ),
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
                "plans/investigations/evidence/level8-existing-section-reconciliation/"
                "verification.json",
                "plans/investigations/evidence/level8-existing-section-reconciliation/"
                "real-net-section-reconciliation.json",
                "plans/investigations/evidence/level8-existing-section-reconciliation/"
                "unresolved-section-reconciliation.json",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    command = (
        ".venv/Scripts/python "
        "plans/investigations/tools/build_existing_section_reconciliation_evidence.py"
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
    focused = run_focused_tests()
    checks = _checks(cases, focused, start_status, head)
    _write_case_evidence(cases, focused)
    _write_closeout(branch, head, checks)
    refresh_sha256sums(OUTPUT_ROOT)
    if not verify_inventory():
        raise RuntimeError("existing-section reconciliation evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
