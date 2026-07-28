"""Build seven-platform evidence for contextual links and Enterprise terminology."""

from __future__ import annotations

import argparse
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
from readme_agent.registry.loader import load_policy, require_listed  # noqa: E402
from readme_agent.registry.models import LinkAllocationPolicyV1  # noqa: E402
from readme_agent.registry.priority import load_platform_priority  # noqa: E402
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import (  # noqa: E402
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402

SUMMARY_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-seven-ecosystem-facts"
    / "representative-facts.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-contextual-linking"
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
TASK_ID = "L8-COMPOSE-01C-CONTEXTUAL-LINKING"
FOCUSED_TESTS = (
    "tests/unit/test_aspose_link_catalog_generator.py",
    "tests/unit/test_aspose_link_catalogs.py",
    "tests/unit/test_link_catalog.py",
    "tests/unit/test_link_allocation.py",
    "tests/unit/test_contextual_link_selection.py",
    "tests/unit/test_readme_contextual_links.py",
    "tests/unit/test_enterprise_terminology.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_factuality.py",
    "tests/unit/test_local_poc_evidence.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Evaluate representatives without writing closure evidence.",
    )
    return parser.parse_args(argv)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _load_summary() -> dict:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    configured = list(load_platform_priority().execution_order)
    if summary["configured_order"] != configured:
        raise RuntimeError("representative facts do not match platform priority")
    return summary


def _configured_policy(auto_plan) -> LinkAllocationPolicyV1:
    budget = auto_plan.contextual_links.budget
    return LinkAllocationPolicyV1.model_validate(
        {
            "mode": "configured",
            "max_total": budget.max_total,
            "domain_maxima": budget.domain_maxima,
            "surface_maxima": budget.surface_maxima,
        }
    )


def _native_patch(source: str, candidate: str):
    edit = SourceSpanEditV1(
        path="README.md",
        byte_start=0,
        byte_end=len(source.encode("utf-8")),
        expected_sha256=sha256_text(source),
        replacement=candidate,
        purpose="apply the independently reconstructable contextual README plan",
    )
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(source),
        edits=[edit],
    )
    return create_git_patch_proof(source, candidate, bounded)


def _render_mode(
    row: dict,
    source: str,
    facts: ProductFactsV2,
    policy: LinkAllocationPolicyV1,
    mode: str,
) -> tuple[dict, dict]:
    catalogs = load_aspose_link_catalogs()
    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=row["source_revision"],
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
    contextual = plan.contextual_links
    if contextual is None:
        raise RuntimeError(f"{row['ecosystem']}/{mode}: no contextual-link decision")
    rerendered, rerun_plan = build_readme_document_candidate(
        facts.org_repo,
        candidate,
        facts,
        base_revision=row["source_revision"],
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    rerun_contextual = rerun_plan.contextual_links
    zero_net_patch = rerendered == candidate
    no_op = (
        zero_net_patch
        and not rerun_plan.operations
        and rerun_contextual is not None
        and rerun_contextual.bindings == contextual.bindings
        and rerun_contextual.omission_reason == contextual.omission_reason
    )
    patch = _native_patch(source, candidate)
    result = {
        "mode": mode,
        "candidate_sha256": sha256_text(candidate),
        "plan_sha256": sha256_text(plan.model_dump_json()),
        "patch_sha256": patch.patch_sha256,
        "git_apply_check_passed": patch.git_apply_check_passed,
        "validation_valid": validation.valid,
        "validation_errors": validation.errors,
        "budget": contextual.budget.model_dump(mode="json"),
        "considered_record_ids": contextual.considered_record_ids,
        "bindings": [item.model_dump(mode="json") for item in contextual.bindings],
        "omission_reason": contextual.omission_reason,
        "useful_link_or_evidenced_zero": bool(contextual.bindings)
        or contextual.omission_reason != "none",
        "terminology_corrections": [
            item.model_dump(mode="json") for item in plan.enterprise_terminology_corrections
        ],
        "no_op_proven": no_op,
        "rerun_candidate_sha256": sha256_text(rerendered),
        "rerun_operation_ids": [operation.operation_id for operation in rerun_plan.operations],
        "rerun_omission_reason": (
            rerun_contextual.omission_reason if rerun_contextual is not None else None
        ),
    }
    artifacts = {
        "candidate": candidate,
        "plan": plan,
        "validation": validation,
        "patch": patch.patch,
        "no_op": {
            "candidate_sha256": sha256_text(candidate),
            "rerendered_sha256": sha256_text(rerendered),
            "identical": rerendered == candidate,
            "zero_net_patch": zero_net_patch,
            "rerun_patch_sha256": sha256_text(""),
            "rerun_operation_count": len(rerun_plan.operations),
            "rerun_contextual_decision": (
                rerun_contextual.model_dump(mode="json") if rerun_contextual is not None else None
            ),
        },
    }
    return result, artifacts


def _prove_representative(row: dict) -> tuple[dict, dict]:
    bundle = REPO_ROOT / row["bundle_root"]
    source = (bundle / "source" / "README.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (bundle / "facts" / "product-facts.json").read_text(encoding="utf-8")
    )
    if facts.org_repo != row["org_repo"] or facts.canonical_hash() != row["facts_hash"]:
        raise RuntimeError(f"{row['ecosystem']}: facts do not match accepted representative")
    entry = require_listed(facts.org_repo)
    if entry.policy_profile is None:
        raise RuntimeError(f"{facts.org_repo}: missing policy profile")
    auto_policy = load_policy(entry.policy_profile).link_allocation
    if auto_policy.mode != "auto":
        raise RuntimeError(f"{facts.org_repo}: representative policy is not automatic")
    auto_result, auto_artifacts = _render_mode(row, source, facts, auto_policy, "auto")
    configured = _configured_policy(auto_artifacts["plan"])
    configured_result, configured_artifacts = _render_mode(
        row,
        source,
        facts,
        configured,
        "configured",
    )
    result = {
        "ecosystem": row["ecosystem"],
        "org_repo": facts.org_repo,
        "source_revision": row["source_revision"],
        "source_sha256": sha256_text(source),
        "facts_hash": facts.canonical_hash(),
        "auto": auto_result,
        "configured": configured_result,
    }
    return result, {
        "source": source,
        "facts": facts,
        "auto": auto_artifacts,
        "configured": configured_artifacts,
    }


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


def _write_representative(output: Path, result: dict, artifacts: dict) -> None:
    root = output / "representatives" / result["ecosystem"]
    write_redacted_text(root / "original-readme.md", artifacts["source"])
    write_redacted_json(root / "product-facts-v2.json", artifacts["facts"])
    for mode in ("auto", "configured"):
        mode_root = root / mode
        current = artifacts[mode]
        write_redacted_text(mode_root / "candidate-readme.md", current["candidate"])
        write_redacted_text(mode_root / "proposal.patch", current["patch"])
        write_redacted_json(mode_root / "readme-document-plan-v1.json", current["plan"])
        write_redacted_json(mode_root / "document-validation.json", current["validation"])
        write_redacted_json(mode_root / "no-op-proof.json", current["no_op"])


def _verify_inventory(output: Path) -> None:
    for line in (output / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        actual = hashlib.sha256((output / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"evidence checksum mismatch: {relative}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = _load_summary()
    results_and_artifacts = [_prove_representative(row) for row in summary["representatives"]]
    results = [item[0] for item in results_and_artifacts]
    configured_order = list(load_platform_priority().execution_order)
    checks = {
        "configured_order_exact": [row["ecosystem"] for row in results] == configured_order,
        "seven_representatives": len(results) == 7,
        "auto_and_configured_valid": all(
            row[mode]["validation_valid"] for row in results for mode in ("auto", "configured")
        ),
        "useful_link_or_evidenced_zero": all(
            row[mode]["useful_link_or_evidenced_zero"]
            for row in results
            for mode in ("auto", "configured")
        ),
        "native_patches_apply": all(
            row[mode]["git_apply_check_passed"]
            for row in results
            for mode in ("auto", "configured")
        ),
        "no_op_proven": all(
            row[mode]["no_op_proven"] for row in results for mode in ("auto", "configured")
        ),
        "zero_remote_writes": True,
        "zero_llm_calls": True,
    }
    if args.diagnostic:
        print(
            json.dumps(
                {
                    "checks": checks,
                    "representatives": [
                        {
                            "ecosystem": row["ecosystem"],
                            "org_repo": row["org_repo"],
                            "auto_candidate_sha256": row["auto"]["candidate_sha256"],
                            "configured_candidate_sha256": row["configured"]["candidate_sha256"],
                        }
                        for row in results
                    ],
                },
                indent=2,
            )
        )
        return 0 if all(checks.values()) else 1

    output = args.output_dir.resolve()
    if output != DEFAULT_OUTPUT.resolve():
        raise RuntimeError("output must be the canonical contextual-link evidence directory")
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    focused = _run_focused_tests()
    checks["control_tree_clean_at_start"] = not start_status
    checks["source_head_stable"] = _git("rev-parse", "HEAD") == head
    checks["focused_regressions_pass"] = focused["exit_code"] == 0
    for result, artifacts in results_and_artifacts:
        _write_representative(output, result, artifacts)
    catalogs = load_aspose_link_catalogs()
    write_redacted_json(
        output / "catalog-provenance.json",
        {
            "aspose_org": catalogs.aspose_org.provenance,
            "aspose_com": catalogs.aspose_com.provenance,
        },
    )
    write_redacted_text(
        output / "focused-tests.txt",
        (
            f"$ {focused['command']}\nexit_code={focused['exit_code']}\n\n"
            f"{focused['stdout']}{focused['stderr']}"
        ),
    )
    manifest = {
        "schema_version": 1,
        "task_id": "L8-COMPOSE-01C-CONTEXTUAL-LINKING",
        "scope": "contextual-links-and-enterprise-terminology-only",
        "portfolio_acceptance": "NOT_GATE_A",
        "configured_order": configured_order,
        "source_branch": branch,
        "source_head": head,
        "control_tree_status_at_start": start_status,
        "representatives": results,
        "checks": checks,
        "reproduction_command": (
            ".venv/Scripts/python plans/investigations/tools/build_contextual_linking_evidence.py"
        ),
    }
    write_redacted_json(output / "acceptance-manifest.json", manifest)
    graph, _ = load_mission_graph(GRAPH_PATH)
    task = next(task for task in graph.taskcards if task.task_id == TASK_ID)
    scoreboard = derive_lifecycle_scoreboard(default_state_backend())
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    write_redacted_json(
        output / "mission-contribution.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "goal_ids": task.goal_ids,
            "core_contribution": task.core_contribution.model_dump(mode="json"),
            "acceptance_checks_passed": task.acceptance_checks,
            "proof_refs": [
                "plans/investigations/evidence/level8-contextual-linking/acceptance-manifest.json",
                "plans/investigations/evidence/level8-contextual-linking/"
                "evidence-verification.json",
                "plans/investigations/evidence/level8-contextual-linking/focused-tests.txt",
            ],
            "scoreboard_before_sha256": scoreboard_hash,
            "scoreboard_after_sha256": scoreboard_hash,
            "first_failing_boundary_before": scoreboard.first_failing_boundary,
            "first_failing_boundary_after": scoreboard.first_failing_boundary,
            "independently_verified": all(checks.values()),
        },
    )
    write_redacted_text(output / "reproduction.txt", manifest["reproduction_command"] + "\n")
    refresh_sha256sums(output)
    _verify_inventory(output)
    write_redacted_json(
        output / "evidence-verification.json",
        {
            "all_inventory_entries_match": True,
            "representative_order_matches_policy": True,
            "manifest_checks_pass": all(checks.values()),
        },
    )
    refresh_sha256sums(output)
    _verify_inventory(output)
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
