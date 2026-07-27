"""Build committed-blob provenance and adaptation evidence for ecosystem truth."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from aspose_org_adaptation_evidence_support import (
    hash_local_paths,
    license_review,
    runtime_dependency_scan,
    sha256,
    source_repository_state,
    verify_commits,
    verify_committed_sources,
    verify_source_test_mappings,
)

from readme_agent.evidence.writer import (
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "control"
    / "aspose-org-ecosystem-adaptation-contract.json"
)
EVIDENCE_DIR = (
    REPO_ROOT / "plans" / "investigations" / "evidence" / "level8-aspose-org-ecosystem-adaptation"
)
OFFICIAL_COMMAND = (
    str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
    "scripts/governance/run_official_checks.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _control_repository_state() -> dict[str, Any]:
    porcelain = _git("status", "--porcelain=v1").encode()
    return {
        "head": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "tree_clean_at_start": not porcelain,
        "tree_porcelain_sha256": sha256(porcelain),
        "contract_path": CONTRACT_PATH.relative_to(REPO_ROOT).as_posix(),
        "contract_sha256": sha256(CONTRACT_PATH.read_bytes()),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": sha256(Path(__file__).read_bytes()),
    }


def _run_official_checks(control_state: dict[str, Any]) -> dict[str, Any]:
    if not control_state["tree_clean_at_start"]:
        raise RuntimeError("official adaptation proof requires a clean committed starting tree")
    result = subprocess.run(
        OFFICIAL_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("official adaptation checks failed")
    if _git("rev-parse", "HEAD") != control_state["head"] or _git("status", "--porcelain=v1"):
        raise RuntimeError("HEAD or working tree changed during official adaptation checks")
    return {
        "command": " ".join(OFFICIAL_COMMAND).replace(str(REPO_ROOT) + "\\", ""),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _adaptation_matrix(
    contract: dict[str, Any], local_paths: list[dict[str, Any]]
) -> dict[str, Any]:
    local_by_path = {entry["path"]: entry for entry in local_paths}
    platforms = [
        {
            "platform": platform["platform"],
            "child_task_id": platform["child_task_id"],
            "dependency_decision": platform["dependency_decision"],
            "target_contracts": platform["target_contracts"],
            "current_local_seams": [
                local_by_path[path] for path in platform["current_local_paths"]
            ],
            "adopted_behaviors": platform["adopted_behaviors"],
            "rejected_behaviors": platform["rejected_behaviors"],
            "implementation_status": "scoped_not_implemented",
        }
        for platform in contract["platforms"]
    ]
    return {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "task_id": "L8-TRUTH-02A-ASPOSE-ORG-ADAPTATION",
        "requirement_id": "L8-029",
        "platforms": platforms,
        "shared_local_contract": {
            "planned_schema_path": "src/readme_agent/facts/public_api_schema.py",
            "planned_test_path": "tests/unit/test_public_api_schema.py",
            "rule": (
                "Each visitor-facing symbol must identify its import path, kind, visibility "
                "evidence, source revision, and verification state."
            ),
        },
        "downstream_order": [
            "L8-TRUTH-02B-PYTHON-API-TRUTH",
            "L8-TRUTH-02C-TYPESCRIPT-EXPORT-TRUTH",
            "L8-TRUTH-02D-RUST-API-TRUTH",
        ],
    }


def _write_evidence(
    sibling_root: Path,
    *,
    run_official: bool,
) -> list[str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    control_state = _control_repository_state()
    official = _run_official_checks(control_state) if run_official else None
    git_dir = sibling_root / ".git"
    if not git_dir.is_dir():
        raise RuntimeError(f"sibling Git directory does not exist: {git_dir}")

    commits, commit_failures = verify_commits(contract, git_dir)
    mapping_failures = verify_source_test_mappings(contract)
    source_records, source_failures = verify_committed_sources(contract, git_dir)
    reviewed_license, license_failures = license_review(contract, git_dir, source_records)
    local_paths, local_failures = hash_local_paths(contract)
    runtime_scan, runtime_failures = runtime_dependency_scan(contract)
    source_state, source_state_failures = source_repository_state(sibling_root, git_dir, contract)
    failures = [
        *commit_failures,
        *mapping_failures,
        *source_failures,
        *license_failures,
        *local_failures,
        *runtime_failures,
        *source_state_failures,
    ]

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(
        EVIDENCE_DIR / "source-provenance.json",
        {
            "schema_version": 1,
            "source_repository": source_state,
            "verified_commits": commits,
            "committed_blob_records": source_records,
        },
    )
    write_redacted_json(EVIDENCE_DIR / "license-and-dependency-review.json", reviewed_license)
    write_redacted_json(EVIDENCE_DIR / "runtime-independence.json", runtime_scan)
    write_redacted_json(
        EVIDENCE_DIR / "adaptation-matrix.json",
        _adaptation_matrix(contract, local_paths),
    )
    if official is not None:
        write_redacted_text(EVIDENCE_DIR / "official-checks.stdout.log", official["stdout"] + "\n")
        write_redacted_text(EVIDENCE_DIR / "official-checks.stderr.log", official["stderr"] + "\n")
    verification = {
        "schema_version": 1,
        "task_id": "L8-TRUTH-02A-ASPOSE-ORG-ADAPTATION",
        "requirement_id": "L8-029",
        "control_repository": control_state,
        "source_record_count": len(source_records),
        "platform_count": len(contract["platforms"]),
        "working_tree_negative_control": {
            "dirty": source_state["working_tree_dirty"],
            "change_count": source_state["working_tree_change_count"],
            "committed_blobs_reconstructed_without_worktree": True,
        },
        "checks": {
            "pinned_commits_exist": not commit_failures,
            "all_source_tests_are_pinned": not mapping_failures,
            "all_source_hashes_match": not source_failures,
            "license_disposition_matches": not license_failures,
            "current_local_seams_exist": not local_failures,
            "runtime_has_no_sibling_checkout_dependency": not runtime_failures,
            "sibling_head_and_remote_match": not source_state_failures,
            "official_checks_pass": official is not None and official["exit_code"] == 0,
        },
        "official_check": (
            {
                "command": official["command"],
                "exit_code": official["exit_code"],
                "raw_stdout": "official-checks.stdout.log",
                "raw_stderr": "official-checks.stderr.log",
            }
            if official is not None
            else {"status": "not_run"}
        ),
        "failures": failures,
        "verdict": "VERIFIED" if not failures and official is not None else "PRELIMINARY",
    }
    write_redacted_json(EVIDENCE_DIR / "verification.json", verification)
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "mission_id": "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION",
            "task_id": "L8-TRUTH-02A-ASPOSE-ORG-ADAPTATION",
            "goal_ids": ["GOAL-TRUTH"],
            "contribution_kind": "visible_deliverable",
            "summary": (
                "Pinned and reconstructable Python, TypeScript, and Rust adaptation scopes "
                "with source hashes, license constraints, dependency decisions, local seams, "
                "tests, and rejected shortcuts."
            ),
            "closeout_ready": not failures and official is not None,
        },
    )
    command = (
        ".venv/Scripts/python "
        "plans/investigations/tools/build_aspose_org_ecosystem_adaptation_evidence.py "
        f'--sibling-root "{sibling_root}" --official --check'
    )
    write_redacted_text(EVIDENCE_DIR / "reproduction.txt", command + "\n")
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sibling-root", type=Path, required=True)
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = _write_evidence(
        args.sibling_root.resolve(),
        run_official=args.official,
    )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print(f"wrote adaptation evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
