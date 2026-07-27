"""Verify pinned Aspose.org blobs, licensing, local seams, and runtime isolation."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
LICENSE_CANDIDATES = ("LICENSE", "LICENSE.md", "COPYING", "COPYING.md")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_output(git_dir: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "--git-dir", str(git_dir), *args],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def committed_blob(git_dir: Path, commit: str, path: str) -> bytes:
    return git_output(git_dir, "show", f"{commit}:{path}")


def source_records(contract: dict[str, Any]) -> list[dict[str, str]]:
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


def verify_source_test_mappings(contract: dict[str, Any]) -> list[str]:
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


def verify_committed_sources(
    contract: dict[str, Any], git_dir: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for expected in source_records(contract):
        content = committed_blob(git_dir, expected["commit"], expected["path"])
        actual_sha256 = sha256(content)
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


def verify_commits(contract: dict[str, Any], git_dir: Path) -> tuple[list[str], list[str]]:
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


def license_review(
    contract: dict[str, Any], git_dir: Path, records: list[dict[str, Any]]
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
    for record in records:
        content = committed_blob(git_dir, record["commit"], record["path"])
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


def hash_local_paths(contract: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
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
                "sha256": sha256(path.read_bytes()) if exists else None,
            }
    return [records[key] for key in sorted(records)], failures


def runtime_dependency_scan(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
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


def source_repository_state(
    sibling_root: Path, git_dir: Path, contract: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    source = contract["source_repository"]
    actual_head = git_output(git_dir, "rev-parse", "HEAD").decode().strip()
    remote = git_output(git_dir, "config", "--get", "remote.origin.url").decode().strip()
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
            "working_tree_porcelain_sha256": sha256(porcelain),
            "blob_reconstruction_uses_git_dir_only": True,
            "working_tree_bytes_used": False,
        },
        failures,
    )
