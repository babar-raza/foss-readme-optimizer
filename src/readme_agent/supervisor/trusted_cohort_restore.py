"""Restore immutable cohort inputs into disposable ACT runtime locations."""

from __future__ import annotations

import hashlib
import subprocess
import tarfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.evidence.writer import sha256_file, verify_sha256sums
from readme_agent.state.migrations import load_run_state_json
from readme_agent.state.trusted_cohort_schema import QualifiedTrustedCohortV1


class _ArchiveBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_count: int | None = None
    ref_count: int | None = None


class TrustedCohortActInputsV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: int
    cohort_id: str
    runtime_inputs: _ArchiveBindingV1
    state_bundle: _ArchiveBindingV1
    member_state_versions: dict[str, int]


def _verified_input(path: Path, expected_sha256: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"ACT input does not exist: {resolved}")
    if hashlib.sha256(resolved.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError(f"ACT input checksum mismatch: {resolved}")
    return resolved


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, mode="r:") as stream:
        for member in stream.getmembers():
            target = (root / member.name).resolve()
            if root != target and root not in target.parents:
                raise ValueError(f"ACT archive member escapes destination: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(f"ACT archive links are not permitted: {member.name}")
        stream.extractall(root, filter="data")


def _verify_runtime_inputs(
    cohort: QualifiedTrustedCohortV1,
    runtime_root: Path,
) -> None:
    for member in cohort.members:
        org, repo = member.org_repo.split("/", maxsplit=1)
        revision_root = runtime_root / f"{org}__{repo}" / member.source_revision
        assurance = revision_root / "assurance" / "trusted_inherited"
        bindings = {
            revision_root / "source" / "README.md": member.readme_sha256,
            assurance / "candidate" / "README.md": member.candidate_sha256,
            assurance / "manifest.json": member.bundle_manifest_sha256,
            assurance / "sha256sums.txt": member.bundle_inventory_sha256,
        }
        for path, expected in bindings.items():
            if not path.is_file() or sha256_file(path)[0] != expected:
                raise ValueError(f"restored ACT runtime binding mismatch: {path}")
        if not verify_sha256sums(assurance):
            raise ValueError(f"restored ACT assurance inventory is invalid: {assurance}")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise ValueError(f"git {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def _restore_state_remote(
    cohort: QualifiedTrustedCohortV1,
    state_bundle: Path,
    state_remote: Path,
    expected_versions: dict[str, int],
) -> None:
    if not state_remote.exists():
        state_remote.parent.mkdir(parents=True, exist_ok=True)
        _git("init", "--bare", str(state_remote))
        refspecs = [
            (
                f"+refs/readme-agent-state/{member.org_repo.replace('/', '__', 1)}:"
                f"refs/readme-agent-state/{member.org_repo.replace('/', '__', 1)}"
            )
            for member in cohort.members
        ]
        _git("--git-dir", str(state_remote), "fetch", str(state_bundle), *refspecs)
    if not (state_remote / "HEAD").is_file():
        raise ValueError(f"ACT state remote is not a bare Git repository: {state_remote}")

    for member in cohort.members:
        ref = f"refs/readme-agent-state/{member.org_repo.replace('/', '__', 1)}"
        payload = _git("--git-dir", str(state_remote), "show", f"{ref}:state.json")
        state = load_run_state_json(payload)
        expected_version = expected_versions.get(member.org_repo)
        if expected_version is None or state.state_version < expected_version:
            raise ValueError(f"ACT state version mismatch for {member.org_repo}")


def restore_trusted_cohort_act_inputs(
    cohort: QualifiedTrustedCohortV1,
    *,
    input_manifest_path: Path,
    runtime_root: Path,
    state_remote: Path,
) -> dict[str, object]:
    """Restore once, then verify idempotently without resetting accumulated ACT state."""

    input_manifest_path = input_manifest_path.resolve()
    inputs = TrustedCohortActInputsV1.model_validate_json(
        input_manifest_path.read_text(encoding="utf-8")
    )
    if inputs.cohort_id != cohort.cohort_id:
        raise ValueError("ACT input manifest cohort does not match the requested frozen cohort")
    archive = _verified_input(
        input_manifest_path.parent / inputs.runtime_inputs.path,
        inputs.runtime_inputs.sha256,
    )
    state_bundle = _verified_input(
        input_manifest_path.parent / inputs.state_bundle.path,
        inputs.state_bundle.sha256,
    )

    first_member_root = runtime_root / cohort.members[0].bundle_path.split("/")[2]
    if not first_member_root.exists():
        _safe_extract(archive, runtime_root)
    _verify_runtime_inputs(cohort, runtime_root)
    _restore_state_remote(
        cohort,
        state_bundle,
        state_remote,
        inputs.member_state_versions,
    )
    return {
        "schema_version": 1,
        "cohort_id": cohort.cohort_id,
        "qualified_count": cohort.qualified_count,
        "runtime_root": str(runtime_root.resolve()),
        "state_remote": str(state_remote.resolve()),
        "input_manifest_sha256": hashlib.sha256(input_manifest_path.read_bytes()).hexdigest(),
        "target_remote_writes": 0,
    }
