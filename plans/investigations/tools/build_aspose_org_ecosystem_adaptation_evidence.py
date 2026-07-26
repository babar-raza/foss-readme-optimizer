"""Build committed-blob provenance and adaptation evidence for ecosystem truth."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json

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
LICENSE_CANDIDATES = ("LICENSE", "LICENSE.md", "COPYING", "COPYING.md")


def _git(git_dir: Path, *args: str, check: bool = True) -> bytes:
    completed = subprocess.run(
        ["git", "--git-dir", str(git_dir), *args],
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _blob(git_dir: Path, commit: str, path: str) -> bytes:
    return _git(git_dir, "show", f"{commit}:{path}")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _walk_source_records(contract: dict[str, Any]) -> list[dict[str, str]]:
    records: dict[tuple[str, str], dict[str, str]] = {}
    for source in contract["source_test_inventory"]:
        key = (source["commit"], source["path"])
        records[key] = {
            "commit": source["commit"],
            "path": source["path"],
            "expected_sha256": source["sha256"],
        }
    for platform in contract["platforms"]:
        for behavior in platform["adopted_behaviors"]:
            commit = behavior["source_commit"]
            for source in behavior["source_paths"]:
                key = (commit, source["path"])
                record = {
                    "commit": commit,
                    "path": source["path"],
                    "expected_sha256": source["sha256"],
                }
                prior = records.get(key)
                if prior is not None and prior != record:
                    raise RuntimeError(
                        f"conflicting source declaration for {commit}:{source['path']}"
                    )
                records[key] = record
        for behavior in platform["rejected_behaviors"]:
            if all(key in behavior for key in ("source_commit", "source_path", "source_sha256")):
                key = (behavior["source_commit"], behavior["source_path"])
                records[key] = {
                    "commit": behavior["source_commit"],
                    "path": behavior["source_path"],
                    "expected_sha256": behavior["source_sha256"],
                }
    return [records[key] for key in sorted(records)]


def _verify_source_test_mappings(contract: dict[str, Any]) -> list[str]:
    inventory = {(entry["commit"], entry["path"]) for entry in contract["source_test_inventory"]}
    failures = []
    for platform in contract["platforms"]:
        for behavior in platform["adopted_behaviors"]:
            commit = behavior["source_commit"]
            for test_reference in behavior["source_tests"]:
                path = test_reference.split("::", maxsplit=1)[0]
                if (commit, path) not in inventory:
                    failures.append(
                        f"source test lacks pinned blob record: {commit}:{test_reference}"
                    )
    return failures


def _verify_committed_sources(
    contract: dict[str, Any], git_dir: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for expected in _walk_source_records(contract):
        content = _blob(git_dir, expected["commit"], expected["path"])
        actual_sha256 = _sha256(content)
        match = actual_sha256 == expected["expected_sha256"]
        if not match:
            failures.append(f"source hash mismatch: {expected['commit']}:{expected['path']}")
        records.append(
            {
                **expected,
                "actual_sha256": actual_sha256,
                "byte_count": len(content),
                "verified": match,
                "retrieval": "git --git-dir <sibling>/.git show <commit>:<path>",
            }
        )
    return records, failures


def _verify_commits(contract: dict[str, Any], git_dir: Path) -> tuple[list[str], list[str]]:
    source = contract["source_repository"]
    commits = [
        source["pinned_head"],
        source["python_property_commit"],
        *source["rust_commits"],
    ]
    failures: list[str] = []
    for commit in commits:
        completed = subprocess.run(
            ["git", "--git-dir", str(git_dir), "cat-file", "-e", f"{commit}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            failures.append(f"missing pinned commit: {commit}")
    return commits, failures


def _license_review(
    contract: dict[str, Any], git_dir: Path, source_records: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    pinned_head = contract["source_repository"]["pinned_head"]
    present_license_files = []
    for path in LICENSE_CANDIDATES:
        completed = subprocess.run(
            ["git", "--git-dir", str(git_dir), "cat-file", "-e", f"{pinned_head}:{path}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode == 0:
            present_license_files.append(path)

    source_spdx_paths = []
    for record in source_records:
        content = _blob(git_dir, record["commit"], record["path"])
        if b"SPDX-License-Identifier:" in content:
            source_spdx_paths.append(f"{record['commit']}:{record['path']}")

    failures: list[str] = []
    expected_status = contract["license_policy"]["source_license_status"]
    actual_status = (
        "no-root-license-or-source-spdx-at-pinned-head"
        if not present_license_files and not source_spdx_paths
        else "license-declaration-present"
    )
    if actual_status != expected_status:
        failures.append(
            f"source license disposition changed: expected {expected_status}, got {actual_status}"
        )
    return (
        {
            "schema_version": 1,
            "pinned_head": pinned_head,
            "root_license_candidates": list(LICENSE_CANDIDATES),
            "present_root_license_files": present_license_files,
            "source_paths_with_spdx": source_spdx_paths,
            "actual_source_license_status": actual_status,
            "transfer_rule": contract["license_policy"]["transfer_rule"],
            "verbatim_source_copy_allowed": contract["license_policy"][
                "verbatim_source_copy_allowed"
            ],
            "rationale": contract["license_policy"]["rationale"],
            "dependency_review": contract["source_dependencies"],
        },
        failures,
    )


def _hash_local_paths(contract: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for platform in contract["platforms"]:
        for relative in platform["current_local_paths"]:
            path = REPO_ROOT / relative
            exists = path.is_file()
            if not exists:
                failures.append(f"missing current local seam: {relative}")
            records[relative] = {
                "path": relative,
                "exists": exists,
                "sha256": _sha256(path.read_bytes()) if exists else None,
            }
    return [records[key] for key in sorted(records)], failures


def _runtime_dependency_scan(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    scan_paths: list[Path] = []
    for relative in contract["verification_sources"]["local_runtime_scan_roots"]:
        path = REPO_ROOT / relative
        if path.is_dir():
            scan_paths.extend(sorted(item for item in path.rglob("*.py") if item.is_file()))
        elif path.is_file():
            scan_paths.append(path)

    matches = []
    patterns = contract["verification_sources"]["forbidden_runtime_dependency_patterns"]
    for path in scan_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern in text:
                matches.append(
                    {
                        "path": path.relative_to(REPO_ROOT).as_posix(),
                        "pattern": pattern,
                    }
                )
    failures = [f"forbidden runtime sibling dependency: {item}" for item in matches]
    return (
        {
            "schema_version": 1,
            "scan_path_count": len(scan_paths),
            "scan_roots": contract["verification_sources"]["local_runtime_scan_roots"],
            "forbidden_patterns": patterns,
            "matches": matches,
            "runtime_dependency_absent": not matches,
        },
        failures,
    )


def _source_repository_state(
    sibling_root: Path, git_dir: Path, contract: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    source = contract["source_repository"]
    actual_head = _git(git_dir, "rev-parse", "HEAD").decode().strip()
    remote = _git(git_dir, "config", "--get", "remote.origin.url").decode().strip()
    porcelain = subprocess.run(
        ["git", "-C", str(sibling_root), "status", "--porcelain=v1"],
        capture_output=True,
        check=True,
    ).stdout
    dirty_lines = porcelain.decode("utf-8", errors="replace").splitlines()
    failures = []
    if actual_head != source["pinned_head"]:
        failures.append(f"sibling HEAD drift: expected {source['pinned_head']}, got {actual_head}")
    if remote.rstrip("/") != source["expected_remote"].rstrip("/"):
        failures.append(
            f"sibling remote mismatch: expected {source['expected_remote']}, got {remote}"
        )
    return (
        {
            "schema_version": 1,
            "expected_remote": source["expected_remote"],
            "actual_remote": remote,
            "expected_head": source["pinned_head"],
            "actual_head": actual_head,
            "head_matches": actual_head == source["pinned_head"],
            "working_tree_dirty": bool(dirty_lines),
            "working_tree_change_count": len(dirty_lines),
            "working_tree_porcelain_sha256": _sha256(porcelain),
            "blob_reconstruction_uses_git_dir_only": True,
            "working_tree_bytes_used": False,
        },
        failures,
    )


def _control_repository_state() -> dict[str, Any]:
    head = (
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )
    branch = (
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )
    porcelain = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain=v1"],
        capture_output=True,
        check=True,
    ).stdout
    return {
        "head": head,
        "branch": branch,
        "tree_clean_at_start": not porcelain,
        "tree_porcelain_sha256": _sha256(porcelain),
        "contract_path": CONTRACT_PATH.relative_to(REPO_ROOT).as_posix(),
        "contract_sha256": _sha256(CONTRACT_PATH.read_bytes()),
        "builder_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
        "builder_sha256": _sha256(Path(__file__).read_bytes()),
    }


def _adaptation_matrix(
    contract: dict[str, Any], local_paths: list[dict[str, Any]]
) -> dict[str, Any]:
    local_by_path = {entry["path"]: entry for entry in local_paths}
    platforms = []
    for platform in contract["platforms"]:
        platforms.append(
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
        )
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


def _write_reproduction(sibling_root: Path) -> None:
    command = (
        ".venv/Scripts/python "
        "plans/investigations/tools/build_aspose_org_ecosystem_adaptation_evidence.py "
        f'--sibling-root "{sibling_root}" --check'
    )
    (EVIDENCE_DIR / "reproduction.txt").write_text(command + "\n", encoding="utf-8")


def build(sibling_root: Path) -> list[str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    control_state = _control_repository_state()
    git_dir = sibling_root / ".git"
    if not git_dir.is_dir():
        raise RuntimeError(f"sibling Git directory does not exist: {git_dir}")

    commits, commit_failures = _verify_commits(contract, git_dir)
    source_test_mapping_failures = _verify_source_test_mappings(contract)
    source_records, source_failures = _verify_committed_sources(contract, git_dir)
    license_review, license_failures = _license_review(contract, git_dir, source_records)
    local_paths, local_failures = _hash_local_paths(contract)
    runtime_scan, runtime_failures = _runtime_dependency_scan(contract)
    source_state, source_state_failures = _source_repository_state(sibling_root, git_dir, contract)
    failures = [
        *commit_failures,
        *source_test_mapping_failures,
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
    write_redacted_json(EVIDENCE_DIR / "license-and-dependency-review.json", license_review)
    write_redacted_json(EVIDENCE_DIR / "runtime-independence.json", runtime_scan)
    write_redacted_json(
        EVIDENCE_DIR / "adaptation-matrix.json",
        _adaptation_matrix(contract, local_paths),
    )
    write_redacted_json(
        EVIDENCE_DIR / "verification.json",
        {
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
                "all_source_tests_are_pinned": not source_test_mapping_failures,
                "all_source_hashes_match": not source_failures,
                "license_disposition_matches": not license_failures,
                "current_local_seams_exist": not local_failures,
                "runtime_has_no_sibling_checkout_dependency": not runtime_failures,
                "sibling_head_and_remote_match": not source_state_failures,
            },
            "failures": failures,
            "verdict": "PASS" if not failures else "FAIL",
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "mission-contribution.json",
        {
            "schema_version": 1,
            "mission_id": "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION",
            "task_id": "L8-TRUTH-02A-ASPOSE-ORG-ADAPTATION",
            "goal_ids": ["GOAL-TRUTH"],
            "contribution_kind": "visible_deliverable",
            "summary": (
                "Pinned and independently reconstructable Python, TypeScript, and Rust "
                "behavioral adaptation scopes with source hashes, license constraints, "
                "dependency decisions, local seams, tests, and rejected shortcuts."
            ),
            "closeout_ready": not failures,
        },
    )
    _write_reproduction(sibling_root)
    refresh_sha256sums(EVIDENCE_DIR)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sibling-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    failures = build(args.sibling_root.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print(f"wrote verified adaptation evidence to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
