"""Bind the canonical .NET facts-only regression to claim-polarity evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.facts.schema_v2 import ProductFactsV2

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "plans/investigations/evidence/level8-claim-polarity"
FAILURE_DIR = REPO_ROOT / "runs/control/claim-polarity-live-regression-failure"
BUNDLE_ROOT = (
    REPO_ROOT
    / "runs/readme-poc"
    / "aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
    / "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"
)
SUPERVISOR_MANIFEST = REPO_ROOT / "runs/evidence/20260727-194315-e589/manifest.json"
STDOUT_PATH = REPO_ROOT / "runs/level8-truth-seven-ecosystems/dotnet-partial-selection.stdout.log"
STDERR_PATH = REPO_ROOT / "runs/level8-truth-seven-ecosystems/dotnet-partial-selection.stderr.log"
IMPLEMENTATION_PATHS = (
    "prompts/generation/draft_product_truth.yaml",
    "src/readme_agent/capabilities/draft_product_truth.py",
    "src/readme_agent/facts/agentic_drafting.py",
    "src/readme_agent/facts/policy_evidence.py",
    "tests/unit/test_agentic_drafting.py",
    "tests/unit/test_draft_product_truth_capability.py",
    "tests/unit/test_evidence_polarity.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _bundle_inventory_valid() -> bool:
    inventory = BUNDLE_ROOT / "sha256sums.txt"
    for line in inventory.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        candidate = BUNDLE_ROOT / relative
        if not candidate.is_file() or _sha256(candidate) != expected:
            return False
    return True


def _build() -> tuple[dict[str, Any], list[str]]:
    facts_path = BUNDLE_ROOT / "facts/product-facts.json"
    bundle_manifest_path = BUNDLE_ROOT / "manifest.json"
    proposed_path = BUNDLE_ROOT / "facts/proposed-product-truth.json"
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    proposed = json.loads(proposed_path.read_text(encoding="utf-8"))
    supervisor = json.loads(SUPERVISOR_MANIFEST.read_text(encoding="utf-8"))
    capabilities = facts.selected_fact("product.capabilities")
    limitations = facts.selected_fact("product.limitations")
    problems = facts.selected_fact("product.problems_solved")
    latest_run_id = supervisor["run_id"]
    latest_stages = [
        checkpoint["stage"]
        for checkpoint in supervisor["checkpoints"]
        if checkpoint["run_id"] == latest_run_id
    ]
    all_directional = [
        assessment
        for fact in (capabilities, limitations)
        for assessment in (fact.evidence_assessments or [])
    ]
    checks = {
        "control_tree_clean": not _git("status", "--porcelain=v1", "--untracked-files=all"),
        "bundle_inventory_valid": _bundle_inventory_valid(),
        "facts_contract_valid": True,
        "facts_ready": (
            bundle_manifest["lifecycle_status"] == "FACTS_READY"
            and bundle_manifest["completed_stages"] == ["SNAPSHOTTED", "PROFILED", "FACTS_READY"]
        ),
        "capabilities_verified_nonempty": (
            capabilities.verification_state == "verified"
            and isinstance(capabilities.value, list)
            and bool(capabilities.value)
        ),
        "limitations_verified_nonempty": (
            limitations.verification_state == "verified"
            and isinstance(limitations.value, list)
            and bool(limitations.value)
        ),
        "selected_directional_evidence_all_accepted": (
            bool(all_directional) and all(assessment.accepted for assessment in all_directional)
        ),
        "unsupported_siblings_pruned": (
            len(proposed["capabilities"]) > len(capabilities.value)
            or len(proposed["limitations"]) > len(limitations.value)
        ),
        "interpretive_claims_cite_selected_capabilities": (
            problems.verification_state == "verified"
            and capabilities.fact_id in problems.supporting_fact_ids
        ),
        "exact_run_accounting": (
            supervisor["status"] == "STAGE_COMPLETE"
            and supervisor["llm_accounting_status"] == "EXACT"
            and supervisor["llm_call_count"] == 3
            and supervisor["llm_calls_by_job"] == {"draft_product_truth": 3}
        ),
        "no_later_stage_or_effect": (
            latest_stages
            == [
                "trigger_accepted",
                "run_started",
                "profile_completed",
                "snapshot_captured",
                "final_acceptance",
            ]
            and supervisor["verifier"]["status"] == "not_run"
            and supervisor["effects"] == []
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return (
        {
            "schema_version": 1,
            "task_id": "L8-TRUTH-03-CLAIM-POLARITY",
            "repository": facts.org_repo,
            "control_repository": {
                "head": _git("rev-parse", "HEAD"),
                "branch": _git("branch", "--show-current"),
                "implementation": {
                    path: _sha256(REPO_ROOT / path) for path in IMPLEMENTATION_PATHS
                },
            },
            "source_revision": bundle_manifest["source_revision"],
            "facts_sha256": _sha256(facts_path),
            "bundle_manifest_sha256": _sha256(bundle_manifest_path),
            "supervisor_manifest_sha256": _sha256(SUPERVISOR_MANIFEST),
            "accepted_capabilities": capabilities.value,
            "accepted_limitations": limitations.value,
            "directional_assessments": [
                assessment.model_dump(mode="json") for assessment in all_directional
            ],
            "latest_checkpoint_stages": latest_stages,
            "checks": checks,
            "failures": failures,
            "verdict": "FAILED" if failures else "VERIFIED",
        },
        failures,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    evidence, failures = _build()
    if failures:
        FAILURE_DIR.mkdir(parents=True, exist_ok=True)
        write_redacted_json(FAILURE_DIR / "verification.json", evidence)
        refresh_sha256sums(FAILURE_DIR)
        if args.check:
            raise SystemExit("live claim-polarity regression failed: " + ", ".join(failures))
        return
    write_redacted_json(EVIDENCE_DIR / "live-canonical-dotnet-regression.json", evidence)
    write_redacted_text(
        EVIDENCE_DIR / "live-canonical-dotnet.stdout.log",
        STDOUT_PATH.read_text(encoding="utf-8", errors="replace"),
    )
    write_redacted_text(
        EVIDENCE_DIR / "live-canonical-dotnet.stderr.log",
        STDERR_PATH.read_text(encoding="utf-8", errors="replace"),
    )
    contribution_path = EVIDENCE_DIR / "mission-contribution.json"
    contribution = json.loads(contribution_path.read_text(encoding="utf-8"))
    proof_ref = (
        "plans/investigations/evidence/level8-claim-polarity/live-canonical-dotnet-regression.json"
    )
    contribution["proof_refs"] = sorted(set([*contribution["proof_refs"], proof_ref]))
    write_redacted_json(contribution_path, contribution)
    refresh_sha256sums(EVIDENCE_DIR)
    print(f"wrote live claim-polarity regression evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
