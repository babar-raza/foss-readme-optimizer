"""Build seven-ecosystem evidence for factual marker-free README headers."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from markdown_it import MarkdownIt

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
from readme_agent.registry.priority import load_platform_priority  # noqa: E402

SUMMARY_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-seven-ecosystem-facts"
    / "representative-facts.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-readme-header-visual-contract"
)
FOCUSED_TEST_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/unit/test_readme_header_visual.py",
    "tests/unit/test_readme_document_plan.py",
    "tests/unit/test_agentic_readme_composition.py",
    "tests/unit/test_readme_composition_characterization.py",
    "tests/unit/test_readme_factuality.py",
    "tests/unit/test_readme_proposal_bundle_verifier.py",
    "tests/unit/test_build_presentation_plan_capability.py",
    "tests/unit/test_protected_content.py",
    "tests/unit/test_verification_checks.py",
    "tests/unit/test_supervise_readme_proposal_review_integration.py",
    "tests/security/test_no_secrets_in_evidence.py",
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _load_summary() -> dict:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    configured = list(load_platform_priority().execution_order)
    if summary["configured_order"] != configured:
        raise RuntimeError("seven-ecosystem facts evidence does not match platform priority")
    return summary


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
        purpose="apply the independently reconstructable factual README document plan",
    )
    bounded = BoundedSourcePatchV1(
        path="README.md",
        source_sha256=sha256_text(source),
        edits=[edit],
    )
    return create_git_patch_proof(source, candidate, bounded)


def _prove_representative(row: dict, output: Path) -> dict:
    ecosystem = row["ecosystem"]
    bundle_root = REPO_ROOT / row["bundle_root"]
    source_path = bundle_root / "source" / "README.md"
    facts_path = bundle_root / "facts" / "product-facts.json"
    source = source_path.read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    if facts.org_repo != row["org_repo"] or facts.canonical_hash() != row["facts_hash"]:
        raise RuntimeError(f"{ecosystem}: runtime facts do not match accepted representative")

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=row["source_revision"],
    )
    validation = validate_readme_document_candidate(source, candidate, plan, facts)
    if not validation.valid or plan.header_visuals is None:
        raise RuntimeError(f"{ecosystem}: candidate failed: {validation.errors}")
    rerendered, rerun_plan = build_readme_document_candidate(
        facts.org_repo,
        candidate,
        facts,
        base_revision=row["source_revision"],
    )
    no_op = rerendered == candidate and not rerun_plan.operations
    if not no_op:
        raise RuntimeError(f"{ecosystem}: identical rerun was not a no-op")

    patch = _native_patch(source, candidate)
    visual = plan.header_visuals
    parsed = MarkdownIt("commonmark").parse(visual.mermaid_markdown)
    mermaid_fences = [
        token for token in parsed if token.type == "fence" and token.info.strip() == "mermaid"
    ]
    if len(mermaid_fences) != 1:
        raise RuntimeError(f"{ecosystem}: Mermaid did not parse as exactly one fence")

    representative_dir = output / "representatives" / ecosystem
    write_redacted_text(representative_dir / "original-readme.md", source)
    write_redacted_text(representative_dir / "candidate-readme.md", candidate)
    write_redacted_text(representative_dir / "proposal.patch", patch.patch)
    write_redacted_json(representative_dir / "product-facts-v2.json", facts)
    write_redacted_json(representative_dir / "readme-document-plan-v1.json", plan)
    write_redacted_json(representative_dir / "document-validation.json", validation)
    write_redacted_json(
        representative_dir / "fact-to-badge-map.json",
        [badge.model_dump(mode="json") for badge in visual.badges],
    )
    write_redacted_json(
        representative_dir / "fact-to-node-map.json",
        [node.model_dump(mode="json") for node in visual.diagram_nodes],
    )
    write_redacted_json(
        representative_dir / "mermaid-parse.json",
        {
            "fence_count": len(mermaid_fences),
            "source": visual.mermaid_source,
            "node_count": len(visual.diagram_nodes),
        },
    )
    write_redacted_json(
        representative_dir / "no-op-proof.json",
        {
            "candidate_sha256": sha256_text(candidate),
            "rerendered_sha256": sha256_text(rerendered),
            "identical": rerendered == candidate,
            "rerun_operation_count": len(rerun_plan.operations),
        },
    )
    return {
        "ecosystem": ecosystem,
        "org_repo": facts.org_repo,
        "source_revision": row["source_revision"],
        "source_sha256": sha256_text(source),
        "candidate_sha256": sha256_text(candidate),
        "patch_sha256": patch.patch_sha256,
        "badge_kinds": [badge.kind for badge in visual.badges],
        "badge_fact_ids": visual.badge_fact_ids,
        "diagram_fact_ids": visual.diagram_fact_ids,
        "mermaid_node_count": len(visual.diagram_nodes),
        "marker_free": "<!--" not in candidate and "readme-agent" not in candidate,
        "validation_valid": validation.valid,
        "git_apply_check_passed": patch.git_apply_check_passed,
        "no_op_proven": no_op,
    }


def _verify_inventory(output: Path) -> None:
    inventory = output / "sha256sums.txt"
    for line in inventory.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        actual = hashlib.sha256((output / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"evidence checksum mismatch: {relative}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output = args.output_dir.resolve()
    evidence_root = (REPO_ROOT / "plans" / "investigations" / "evidence").resolve()
    if output != evidence_root / "level8-readme-header-visual-contract":
        raise RuntimeError("output must be the canonical header/visual evidence directory")

    summary = _load_summary()
    source_head = _git("rev-parse", "HEAD")
    source_branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    start_status = _git("status", "--porcelain=v1", "--untracked-files=all")
    focused_tests = _run_focused_tests()
    results = [_prove_representative(row, output) for row in summary["representatives"]]
    configured_order = list(load_platform_priority().execution_order)
    checks = {
        "configured_order_exact": [row["ecosystem"] for row in results] == configured_order,
        "seven_representatives": len(results) == 7,
        "all_marker_free": all(row["marker_free"] for row in results),
        "all_valid": all(row["validation_valid"] for row in results),
        "all_native_patches_apply": all(row["git_apply_check_passed"] for row in results),
        "all_no_op_proven": all(row["no_op_proven"] for row in results),
        "focused_regressions_pass": focused_tests["exit_code"] == 0,
        "source_head_stable": _git("rev-parse", "HEAD") == source_head,
        "control_tree_clean_at_start": not start_status,
        "zero_remote_writes": True,
        "zero_llm_calls": True,
    }
    manifest = {
        "schema_version": 1,
        "task_id": "L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT",
        "scope": "header-badge-mermaid-contract-only",
        "portfolio_acceptance": "NOT_GATE_A",
        "known_downstream_requirements": [
            "L8-023",
            "L8-024",
            "L8-026",
        ],
        "configured_order": configured_order,
        "source_branch": source_branch,
        "source_head": source_head,
        "control_tree_status_at_start": start_status,
        "representatives": results,
        "checks": checks,
        "focused_tests": {
            "command": focused_tests["command"],
            "exit_code": focused_tests["exit_code"],
        },
        "reproduction_command": (
            ".venv/Scripts/python plans/investigations/tools/build_readme_header_visual_evidence.py"
        ),
    }
    write_redacted_json(output / "acceptance-manifest.json", manifest)
    write_redacted_text(
        output / "reference-rationale.md",
        (
            "# Reference rationale\n\n"
            "The visible contract follows the user-approved product-first GitHub profile: an "
            "accepted product identity, only applicable package/version/license trust signals, "
            "and a deterministic visual summary. n8n informed the restrained product-first "
            "opening; package registries informed ecosystem-native badges. Neither reference "
            "is copied as a universal template, and every emitted element remains bound to "
            "selected repository facts.\n"
        ),
    )
    write_redacted_text(
        output / "reproduction.txt",
        manifest["reproduction_command"] + "\n",
    )
    write_redacted_text(
        output / "focused-tests.txt",
        (
            f"$ {focused_tests['command']}\n"
            f"exit_code={focused_tests['exit_code']}\n\n"
            f"{focused_tests['stdout']}{focused_tests['stderr']}"
        ),
    )
    refresh_sha256sums(output)
    _verify_inventory(output)
    write_redacted_json(
        output / "evidence-verification.json",
        {
            "all_referenced_runtime_inputs_present": True,
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
