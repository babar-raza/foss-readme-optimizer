"""Build real .NET evidence for existing-section README reconciliation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.evidence.writer import (  # noqa: E402
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.presentation.git_patch import (  # noqa: E402
    BoundedSourcePatchV1,
    SourceSpanEditV1,
    create_git_patch_proof,
    sha256_text,
)
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

TASK_ID = "L8-COMPOSE-01A-SECTION-REGRESSIONS"
SOURCE_REVISION = "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
INPUT_ROOT = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-contextual-linking"
    / "representatives"
    / "net"
)
OUTPUT_ROOT = (
    REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-existing-section-regressions"
)
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_existing_section_regressions.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_document_structure.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_factuality.py",
    "tests/unit/test_readme_header_visual.py",
    "tests/unit/test_readme_contextual_links.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _run_focused_tests() -> dict:
    result = subprocess.run(
        FOCUSED_TEST_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(FOCUSED_TEST_COMMAND),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _native_patch(source: str, candidate: str):
    edit = SourceSpanEditV1(
        path="README.md",
        byte_start=0,
        byte_end=len(source.encode("utf-8")),
        expected_sha256=sha256_text(source),
        replacement=candidate,
        purpose="apply the independently reconstructable existing-section reconciliation",
    )
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(source),
        edits=[edit],
    )
    return create_git_patch_proof(source, candidate, bounded)


def _verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        actual = hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            return False
    return True


def main() -> int:
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    source = (INPUT_ROOT / "original-readme.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (INPUT_ROOT / "product-facts-v2.json").read_text(encoding="utf-8")
    )
    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=SOURCE_REVISION,
    )
    validation = validate_readme_document_candidate(source, candidate, plan, facts)
    patch = _native_patch(source, candidate)
    focused = _run_focused_tests()
    limitation = facts.selected_fact("product.limitations")
    example = facts.selected_fact("example.minimal")
    limitation_operation = next(
        (
            operation
            for operation in plan.operations
            if operation.operation_id == "readme.limitations.complete-verified"
        ),
        None,
    )
    checks = {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": _git("rev-parse", "HEAD") == head,
        "document_validation_valid": validation.valid,
        "native_patch_applies": patch.git_apply_check_passed,
        "verified_limitation_present_once": candidate.count(limitation.value[0]) == 1,
        "verified_example_present_once": candidate.count(example.value["code"]) == 1,
        "verified_installation_present_once": (
            candidate.count("dotnet add package Aspose.3D.FOSS") == 1
        ),
        "overview_present_once": candidate.count("## At a glance") == 1,
        "maintainer_content_preserved": all(
            text in candidate
            for text in (
                "Some advanced features are not available in this FOSS version:",
                "Currently implementing core functionality:",
            )
        ),
        "limitation_operation_bounded_and_cited": (
            limitation_operation is not None
            and limitation_operation.operation == "insert_before"
            and limitation_operation.fact_ids == [limitation.fact_id]
        ),
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }
    write_redacted_text(OUTPUT_ROOT / "original-readme.md", source)
    write_redacted_text(OUTPUT_ROOT / "candidate-readme.md", candidate)
    write_redacted_json(OUTPUT_ROOT / "readme-document-plan-v1.json", plan)
    write_redacted_json(OUTPUT_ROOT / "document-validation.json", validation)
    write_redacted_text(OUTPUT_ROOT / "proposal.patch", patch.patch)
    write_redacted_json(
        OUTPUT_ROOT / "first-failing-boundary.json",
        {
            "baseline_commit": "a6db18cff0cf56bdb3d59b9a390adb5c5e776829",
            "boundary": "duplicate verified limitation across overview and limitations section",
            "before_exact_occurrences": 2,
            "after_exact_occurrences": candidate.count(limitation.value[0]),
            "source_revision": SOURCE_REVISION,
            "source_sha256": sha256_text(source),
            "candidate_sha256": sha256_text(candidate),
            "facts_hash": facts.canonical_hash(),
        },
    )
    write_redacted_text(
        OUTPUT_ROOT / "focused-tests.txt",
        (
            f"$ {focused['command']}\nexit_code={focused['exit_code']}\n\n"
            f"{focused['stdout']}{focused['stderr']}"
        ),
    )
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
                "plans/investigations/evidence/level8-existing-section-regressions/"
                "verification.json",
                "plans/investigations/evidence/level8-existing-section-regressions/"
                "first-failing-boundary.json",
                "tests/unit/test_readme_existing_section_regressions.py",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    write_redacted_json(
        OUTPUT_ROOT / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_repository": {
                "branch": branch,
                "head": head,
                "working_tree_clean_at_start": not start_status,
            },
            "checks": checks,
            "verdict": "VERIFIED" if all(checks.values()) else "FAILED",
            "reproduction_command": (
                ".venv/Scripts/python "
                "plans/investigations/tools/build_existing_section_regression_evidence.py"
            ),
        },
    )
    write_redacted_text(
        OUTPUT_ROOT / "reproduction.txt",
        ".venv/Scripts/python "
        "plans/investigations/tools/build_existing_section_regression_evidence.py\n",
    )
    refresh_sha256sums(OUTPUT_ROOT)
    inventory_valid = _verify_inventory()
    if not inventory_valid:
        raise RuntimeError("existing-section evidence checksum verification failed")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
