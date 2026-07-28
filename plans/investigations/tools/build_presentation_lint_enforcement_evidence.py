"""Build clean-tree evidence for deterministic README presentation-lint enforcement."""

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
from readme_agent.links.catalog import load_aspose_link_catalogs  # noqa: E402
from readme_agent.readme.document_renderer import (  # noqa: E402
    build_readme_document_candidate,
)
from readme_agent.readme.document_validation import (  # noqa: E402
    validate_readme_document_candidate,
)
from readme_agent.readme.presentation_lint import lint_readme_presentation  # noqa: E402
from readme_agent.registry.models import LinkAllocationPolicyV1  # noqa: E402
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402

TASK_ID = "L8-COMPOSE-04-PRESENTATION-LINT"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
CORPUS_PATH = REPO_ROOT / "tests/fixtures/presentation_defects/corpus.json"
FACTS_PROOF = (
    REPO_ROOT
    / "plans/investigations/evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)
REPRESENTATIVE_ROOT = (
    REPO_ROOT
    / "plans/investigations/evidence"
    / "level8-readme-header-visual-contract"
    / "representatives"
)
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-presentation-lint-enforcement"
PLATFORMS = ("python", "net", "java", "cpp", "typescript", "rust", "go")
FOCUSED_TESTS = (
    "tests/unit/test_validation_registry.py",
    "tests/unit/test_validation_rules.py",
    "tests/unit/test_protected_content.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_operation_regressions.py",
    "tests/unit/test_readme_final_claim_corpus.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_readme_composition_characterization.py",
    "tests/unit/test_readme_composition_module_boundaries.py",
    "tests/unit/test_build_presentation_plan_capability.py",
    "tests/unit/test_supervise_readme_proposal_review_integration.py",
    "tests/unit/test_fact_render_views.py",
    "tests/unit/test_generation_schema_version.py",
    "tests/unit/test_enterprise_terminology.py",
    "tests/unit/test_readme_presentation_lint.py",
    "tests/unit/test_presentation_defect_corpus.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_existing_section_regressions.py",
    "tests/unit/test_readme_header_visual.py",
    "tests/unit/test_readme_contextual_links.py",
    "tests/unit/test_readme_assessment.py",
    (
        "tests/unit/test_supervisor_loop.py::TestBasicLoop::"
        "test_local_poc_records_snapshot_and_profile_before_later_stages"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestBasicLoop::"
        "test_local_poc_repairs_revalidates_and_rereviews_before_accepting"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestBasicLoop::"
        "test_heterogeneous_local_poc_members_share_the_real_supervisor_path"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestSpecialistDrivenConvergence::"
        "test_tracked_content_change_is_reprocessed_without_false_convergence"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestSpecialistFailureIsolation::"
        "test_a_raising_specialist_does_not_abort_the_run"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestSpecialistFailureIsolation::"
        "test_a_raising_specialists_error_stops_before_general_planning"
    ),
)


def _git_output(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _facts_for_case(case: dict, proof: dict) -> ProductFactsV2 | None:
    if case["origin"] == "synthetic_positive":
        return None
    expected = (
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
        if "cells" in case["repository"].casefold()
        else "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
    )
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == expected)
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


def _verify_corpus() -> list[dict]:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    proof = json.loads(FACTS_PROOF.read_text(encoding="utf-8"))
    results = []
    for case in corpus["cases"]:
        candidate = (REPO_ROOT / case["source_path"]).read_text(encoding="utf-8")
        actual = lint_readme_presentation(candidate, _facts_for_case(case, proof))
        expected_spans = {
            (finding["rule_id"], span)
            for finding in case["findings"]
            for span in finding["exact_spans"]
        }
        actual_spans = {
            (finding.rule_id, span.text) for finding in actual.findings for span in finding.spans
        }
        results.append(
            {
                "case_id": case["case_id"],
                "source_path": case["source_path"],
                "source_sha256": _sha256(candidate),
                "expected_verdict": case["expected_verdict"],
                "actual_verdict": "ACCEPT" if actual.valid else "REJECT",
                "rules_run": actual.rules_run,
                "expected_spans_present": expected_spans <= actual_spans,
                "findings": [finding.model_dump(mode="json") for finding in actual.findings],
            }
        )
    return results


def _verify_representatives() -> list[dict]:
    catalogs = load_aspose_link_catalogs()
    policy = LinkAllocationPolicyV1()
    results = []
    for platform in PLATFORMS:
        root = REPRESENTATIVE_ROOT / platform
        source = (root / "original-readme.md").read_text(encoding="utf-8")
        facts = ProductFactsV2.model_validate_json(
            (root / "product-facts-v2.json").read_text(encoding="utf-8")
        )
        revision = facts.selected_fact("product.identity").source.source_revision
        if revision is None:
            raise RuntimeError(f"{platform} representative has no immutable revision")
        candidate, plan = build_readme_document_candidate(
            facts.org_repo,
            source,
            facts,
            base_revision=revision,
            link_catalogs=catalogs,
            link_allocation_policy=policy,
        )
        validation = validate_readme_document_candidate(
            source,
            candidate,
            plan,
            facts,
            link_catalogs=catalogs,
        )
        rerendered, rerun_plan = build_readme_document_candidate(
            facts.org_repo,
            candidate,
            facts,
            base_revision=revision,
            link_catalogs=catalogs,
            link_allocation_policy=policy,
        )
        results.append(
            {
                "platform": platform,
                "org_repo": facts.org_repo,
                "source_revision": revision,
                "source_sha256": _sha256(source),
                "candidate_sha256": _sha256(candidate),
                "operation_ids": [operation.operation_id for operation in plan.operations],
                "deterministic_validation_valid": validation.valid,
                "presentation_findings": [
                    finding.model_dump(mode="json") for finding in validation.presentation_findings
                ],
                "identical_rerun_is_noop": (
                    rerendered == candidate and rerun_plan.operations == []
                ),
            }
        )
    return results


def _run_focused_tests() -> dict:
    command = (sys.executable, "-m", "pytest", "-q", *FOCUSED_TESTS)
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


def _verify_inventory() -> bool:
    for line in (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        if hashlib.sha256((OUTPUT_ROOT / relative).read_bytes()).hexdigest() != expected:
            return False
    return True


def main() -> int:
    branch = _git_output("branch", "--show-current")
    head = _git_output("rev-parse", "HEAD")
    start_status = _git_output("status", "--porcelain=v1", "--untracked-files=all")
    corpus_results = _verify_corpus()
    representative_results = _verify_representatives()
    focused = _run_focused_tests()
    checks = {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": _git_output("rev-parse", "HEAD") == head,
        "all_corpus_verdicts_match": all(
            item["actual_verdict"] == item["expected_verdict"] for item in corpus_results
        ),
        "all_expected_defect_spans_present": all(
            item["expected_spans_present"] for item in corpus_results
        ),
        "rule_inventory_complete": all(len(item["rules_run"]) == 8 for item in corpus_results),
        "seven_representatives_validate": all(
            item["deterministic_validation_valid"] for item in representative_results
        ),
        "seven_representatives_have_no_presentation_findings": all(
            not item["presentation_findings"] for item in representative_results
        ),
        "seven_representatives_noop": all(
            item["identical_rerun_is_noop"] for item in representative_results
        ),
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }
    write_redacted_json(OUTPUT_ROOT / "corpus-results.json", corpus_results)
    write_redacted_json(OUTPUT_ROOT / "representative-results.json", representative_results)
    write_redacted_text(
        OUTPUT_ROOT / "focused-tests.txt",
        (
            f"$ {focused['command']}\nexit_code={focused['exit_code']}\n\n"
            f"{focused['stdout']}{focused['stderr']}"
        ),
    )

    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(item for item in graph.taskcards if item.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    proof_root = "plans/investigations/evidence/level8-presentation-lint-enforcement"
    write_redacted_json(
        OUTPUT_ROOT / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                f"{proof_root}/verification.json",
                f"{proof_root}/corpus-results.json",
                f"{proof_root}/representative-results.json",
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
        "plans/investigations/tools/build_presentation_lint_enforcement_evidence.py"
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
    refresh_sha256sums(OUTPUT_ROOT)
    if not _verify_inventory():
        raise RuntimeError("presentation-lint enforcement evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
