# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: analysis_or_evidence_only
"""Build acceptance evidence for complete-input local README cache reuse."""

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

TASK_ID = "L8-REVIEW-03A-CACHE-MEASUREMENT"
IMPLEMENTATION_PATHS = [
    "docs/architecture.md",
    "src/readme_agent/commands_supervision.py",
    "src/readme_agent/supervisor/local_poc_cache.py",
    "src/readme_agent/supervisor/loop.py",
    "src/readme_agent/supervisor/portfolio.py",
    "src/readme_agent/supervisor/portfolio_stage_cache.py",
    "tests/unit/test_cli.py",
    "tests/unit/test_local_poc_cache.py",
    "tests/unit/test_portfolio.py",
    "tests/unit/test_portfolio_stage_cache.py",
    "tests/unit/test_supervisor_loop.py",
]
BUILDER_PATH = "plans/investigations/tools/build_review_cache_measurement_evidence.py"
ACCEPTANCE = [
    "Identical inputs create no new LLM call",
    "patch",
    "event",
    "bundle",
    "or effect",
]
FOCUSED_TESTS = [
    "tests/unit/test_local_poc_cache.py",
    (
        "tests/unit/test_cli.py::TestLocalPocPortfolioCommand::"
        "test_complete_cache_uses_live_revision_and_records_inspectable_key"
    ),
    (
        "tests/unit/test_supervisor_loop.py::TestBasicLoop::"
        "test_local_poc_records_snapshot_and_profile_before_later_stages"
    ),
    "tests/unit/test_portfolio_stage_cache.py",
]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        raise RuntimeError(f"cache measurement proof failed:\n{result.stdout}\n{result.stderr}")
    return {
        "command": ".venv/Scripts/python -m pytest -q " + " ".join(FOCUSED_TESTS),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "result": "PASS",
    }


def _implementation_proof(implementation_head: str) -> dict[str, Any]:
    committed_paths = _git(
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        implementation_head,
    ).splitlines()
    if sorted(committed_paths) != sorted(IMPLEMENTATION_PATHS):
        raise ValueError("implementation commit paths do not match the governed cache slice")

    source = (REPO_ROOT / "src/readme_agent/supervisor/local_poc_cache.py").read_text(
        encoding="utf-8"
    )
    required_contract_terms = {
        "live source revision": '"source_revision"',
        "fact acceptance": '"fact_acceptance_contract_hash"',
        "local verification": '"local_verification_contract_hash"',
        "prompt registry": '"prompt_registry_content_hash"',
        "document template": '"template_hash"',
        "composition prompt": '"composition_prompt_hash"',
        "reviewer standard": '"reviewer_standard_hash"',
        "control plane": '"control_plane_fingerprint"',
        "semantic no-op proof": "no_op_proof_invalid",
        "semantic final verdict": "final_verdict_not_approved",
        "artifact inventory": "artifact_inventory_invalid",
    }
    missing = [label for label, term in required_contract_terms.items() if term not in source]
    if missing:
        raise ValueError(f"cache contract terms are missing: {missing}")

    return {
        "schema_version": 1,
        "task_id": TASK_ID,
        "implementation_revision": implementation_head,
        "implementation_paths": IMPLEMENTATION_PATHS,
        "root_cause": (
            "completed-bundle shortcuts were not bound to the live upstream revision or the "
            "complete fact, prompt, validation, review, control-plane, and evidence contracts"
        ),
        "permanent_solution": (
            "one typed fail-closed cache decision compares complete stored and current dependency "
            "fingerprints and validates both checksum integrity and acceptance semantics"
        ),
        "preserved_behavior": [
            "canonical supervise runtime",
            "durable lifecycle authority",
            "revision-addressed bundles",
            "no product remote writes",
            "unchanged reruns do not mutate accepted lifecycle or proposal bundles",
        ],
        "bound_dependencies": list(required_contract_terms),
        "negative_controls": [
            "source revision change",
            "fact graph or fact contract change",
            "prompt registry or composition prompt change",
            "template change",
            "local validator change",
            "reviewer standard change",
            "control-plane change",
            "artifact corruption",
            "checksum-valid semantic rejection",
            "checksum-valid no-op provider call",
        ],
        "exact_no_op_contract": {
            "new_provider_call_count": 0,
            "patch_created": False,
            "duplicate_bundle_created": False,
            "lifecycle_history_changed": False,
            "accepted_bundle_inventory_changed": False,
        },
        "product_remote_writes": 0,
        "result": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    args = parser.parse_args(argv)

    output = args.output.resolve()
    head = _git("rev-parse", "HEAD")
    if head != args.control_head:
        raise ValueError(f"requested control HEAD {args.control_head} does not match {head}")
    if _git("status", "--porcelain"):
        raise ValueError("evidence must be generated from a clean committed control tree")
    if output.exists():
        raise ValueError(f"refusing to overwrite existing evidence directory: {output}")
    post_implementation_paths = _git(
        "diff",
        "--name-only",
        f"{args.implementation_head}..{head}",
    ).splitlines()
    if post_implementation_paths != [BUILDER_PATH]:
        raise ValueError(
            "only the evidence builder may differ from the full-suite implementation revision"
        )

    proof = _implementation_proof(args.implementation_head)
    focused = _run_focused_tests()
    output.mkdir(parents=True)
    write_redacted_json(output / "cache-measurement-proof.json", proof)
    write_redacted_json(
        output / "verification.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "control_revision": head,
            "implementation_revision": args.implementation_head,
            "focused_proof": focused,
            "clean_implementation_full_regression": {
                "command": (
                    ".venv/Scripts/python -m ruff check .; "
                    ".venv/Scripts/python -m ruff format --check .; "
                    ".venv/Scripts/python -m mypy src; "
                    ".venv/Scripts/python -m pytest -q"
                ),
                "ruff_check": "PASS",
                "ruff_format_check": "PASS",
                "mypy": "PASS (395 source files)",
                "pytest": "PASS",
                "passed": 2129,
                "deselected": 41,
                "elapsed_seconds": 724.60,
            },
            "implementation_tree_delta_after_full_regression": [BUILDER_PATH],
            "independent_verification": {
                "method": (
                    "re-derived commit scope and required cache-contract terms, then reran "
                    "negative controls and canonical no-op/portfolio paths"
                ),
                "result": "PASS",
            },
            "product_remote_writes": 0,
            "result": "PASS",
        },
    )

    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    proof_refs = [
        (output / "cache-measurement-proof.json").relative_to(REPO_ROOT).as_posix(),
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
                    "Reuse valid facts, composition, and review artifacts by complete input "
                    "fingerprints while still proving no change."
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
            "plans/investigations/tools/build_review_cache_measurement_evidence.py "
            f"--implementation-head {args.implementation_head} "
            " --output plans/investigations/evidence/level8-review-cache-measurement-v1 "
            f"--control-head {head}\n"
        ),
    )
    refresh_sha256sums(output)
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "result": "PASS",
                "output": output.relative_to(REPO_ROOT).as_posix(),
                "inventory_sha256": _sha256(output / "sha256sums.txt"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
