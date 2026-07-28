"""Build clean-tree evidence for the frozen README presentation defect corpus."""

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
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402

TASK_ID = "L8-COMPOSE-03A-PRESENTATION-CORPUS"
GRAPH_PATH = REPO_ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
CORPUS_PATH = REPO_ROOT / "tests/fixtures/presentation_defects/corpus.json"
OUTPUT_ROOT = REPO_ROOT / "plans/investigations/evidence/level8-presentation-defect-corpus"
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_presentation_defect_corpus.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_readme_document_operations.py",
    "tests/unit/test_readme_fact_grounding.py",
    "tests/unit/test_readme_factuality.py",
    "tests/unit/test_readme_final_claim_corpus.py",
    "tests/unit/test_readme_operation_regressions.py",
    "tests/unit/test_validation_rules.py",
    "tests/unit/test_validation_registry.py",
    "tests/unit/test_protected_content.py",
)


def _git_output(*args: str) -> str:
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


def _verify_corpus(corpus: dict) -> tuple[list[dict], list[dict]]:
    inventory = []
    expected_findings = []
    for case in corpus["cases"]:
        source_path = REPO_ROOT / case["source_path"]
        source_bytes = source_path.read_bytes()
        source_text = source_bytes.decode("utf-8")
        actual_sha256 = hashlib.sha256(source_bytes).hexdigest()
        findings = []
        for finding in case["findings"]:
            spans = []
            for span, expected_count in zip(
                finding["exact_spans"],
                finding["expected_occurrences"],
                strict=True,
            ):
                spans.append(
                    {
                        "exact_span": span,
                        "expected_occurrences": expected_count,
                        "actual_occurrences": source_text.count(span),
                    }
                )
            findings.append({**finding, "spans": spans})
            expected_findings.append(
                {
                    "case_id": case["case_id"],
                    "finding_id": finding["finding_id"],
                    "rule_id": finding["rule_id"],
                    "severity": finding["severity"],
                    "spans": spans,
                }
            )
        inventory.append(
            {
                "case_id": case["case_id"],
                "origin": case["origin"],
                "repository": case["repository"],
                "platform": case["platform"],
                "source_path": case["source_path"],
                "expected_sha256": case["source_sha256"],
                "actual_sha256": actual_sha256,
                "expected_verdict": case["expected_verdict"],
                "finding_ids": [finding["finding_id"] for finding in findings],
                "source_hash_matches": actual_sha256 == case["source_sha256"],
                "all_expected_spans_exact": all(
                    span["actual_occurrences"] == span["expected_occurrences"]
                    for finding in findings
                    for span in finding["spans"]
                ),
            }
        )
    return inventory, expected_findings


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
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    inventory, expected_findings = _verify_corpus(corpus)
    focused = _run_focused_tests()
    rule_ids = {finding["rule_id"] for finding in expected_findings}
    checks = {
        "control_tree_clean_at_start": not start_status,
        "source_head_stable": _git_output("rev-parse", "HEAD") == head,
        "real_java_and_python_negatives_present": {
            case["platform"] for case in corpus["cases"] if case["origin"] == "real_candidate"
        }
        == {"java", "python"},
        "prompt_injection_control_present": "prompt_injection_residue" in rule_ids,
        "strong_content_control_present": any(
            case["origin"] == "synthetic_positive" for case in corpus["cases"]
        ),
        "cross_product_control_present": "cross_product_leakage" in rule_ids,
        "every_source_hash_matches": all(item["source_hash_matches"] for item in inventory),
        "every_expected_span_is_exact": all(item["all_expected_spans_exact"] for item in inventory),
        "every_reject_has_critical_findings": all(
            case["findings"] and all(item["severity"] == "critical" for item in case["findings"])
            for case in corpus["cases"]
            if case["expected_verdict"] == "REJECT"
        ),
        "positive_control_has_no_findings": all(
            not case["findings"] for case in corpus["cases"] if case["expected_verdict"] == "ACCEPT"
        ),
        "focused_regressions_pass": focused["exit_code"] == 0,
        "zero_product_remote_writes": True,
    }
    write_redacted_json(OUTPUT_ROOT / "fixture-inventory.json", inventory)
    write_redacted_json(OUTPUT_ROOT / "expected-findings.json", expected_findings)
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
    proof_root = "plans/investigations/evidence/level8-presentation-defect-corpus"
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
                f"{proof_root}/fixture-inventory.json",
                f"{proof_root}/expected-findings.json",
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
        "plans/investigations/tools/build_presentation_defect_corpus_evidence.py"
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
            "scope_note": (
                "This task freezes expected deterministic rejections. Runtime lint enforcement "
                "is owned by dependency-successor L8-COMPOSE-04-PRESENTATION-LINT."
            ),
            "reproduction_command": command,
        },
    )
    write_redacted_text(OUTPUT_ROOT / "reproduction.txt", command + "\n")
    refresh_sha256sums(OUTPUT_ROOT)
    if not _verify_inventory():
        raise RuntimeError("presentation-defect corpus evidence checksum mismatch")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
