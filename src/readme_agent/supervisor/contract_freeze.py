"""Immutable plan and pipeline-contract freeze schemas and builders."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def raw_sha256(data: bytes) -> str:
    """Return the identity of exact bytes without newline normalization."""

    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return raw_sha256(payload.encode("utf-8"))


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrozenFileV1(_StrictFrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if not normalized or normalized.startswith(("/", "../")) or "/../" in normalized:
            raise ValueError("path must be repository-relative")
        return normalized


class PlanFreezeV1(_StrictFrozenModel):
    schema_version: Literal["PlanFreezeV1"] = "PlanFreezeV1"
    campaign_id: Literal["CAMP-PLAN-FREEZE"] = "CAMP-PLAN-FREEZE"
    control_branch: str
    control_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    members: list[FrozenFileV1] = Field(min_length=1)
    plan_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acceptance_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    freeze_status: Literal["SEALED"] = "SEALED"
    created_at: str = Field(default_factory=utc_now_iso)


class PipelineContractFileV1(FrozenFileV1):
    source_status: Literal["modified", "untracked"]
    contract_group: str
    selection_reason: str
    snapshot_path: str

    @field_validator("snapshot_path")
    @classmethod
    def _safe_snapshot_path(cls, value: str) -> str:
        return FrozenFileV1._safe_relative_path(value)


class PipelineContractSnapshotV1(_StrictFrozenModel):
    schema_version: Literal["PipelineContractSnapshotV1"] = "PipelineContractSnapshotV1"
    source_worktree: str
    source_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_root: str
    files: list[PipelineContractFileV1] = Field(min_length=1)
    acceptance_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_status: Literal["SEALED"] = "SEALED"
    created_at: str = Field(default_factory=utc_now_iso)


def _git(repo_root: Path, *args: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, check=True, capture_output=True, text=text
    )
    return result.stdout


def build_plan_freeze(
    repo_root: Path,
    *,
    control_commit: str,
    members: list[str],
    acceptance_receipt_id: str,
) -> PlanFreezeV1:
    """Bind exact committed bytes and reject dirty or missing membership."""

    branch = str(_git(repo_root, "branch", "--show-current", text=True)).strip()
    frozen: list[FrozenFileV1] = []
    for relative in sorted(set(members)):
        committed = _git(repo_root, "show", f"{control_commit}:{relative}")
        assert isinstance(committed, bytes)
        current = (repo_root / relative).read_bytes()
        if current != committed:
            raise ValueError(
                f"plan-freeze member is dirty relative to {control_commit}: {relative}"
            )
        frozen.append(
            FrozenFileV1(path=relative, sha256=raw_sha256(committed), size=len(committed))
        )
    identity = [item.model_dump(mode="json") for item in frozen]
    graph = next(
        item for item in frozen if item.path.endswith("level8-autonomous-mission-task-graph.yaml")
    )
    receipt_identity = canonical_sha256(
        {"control_commit": control_commit, "members": identity, "result": "ACCEPTED"}
    )
    if receipt_identity != acceptance_receipt_id:
        raise ValueError("acceptance receipt identity does not match committed membership")
    return PlanFreezeV1(
        control_branch=branch,
        control_commit=control_commit,
        members=frozen,
        plan_set_sha256=canonical_sha256(identity),
        graph_sha256=graph.sha256,
        acceptance_receipt_id=acceptance_receipt_id,
    )


def materialize_pipeline_snapshot(
    repo_root: Path,
    *,
    selections: dict[str, tuple[str, str, str]],
    output_root: Path,
) -> PipelineContractSnapshotV1:
    """Copy selected dirty bytes into a content-addressed read-only snapshot."""

    head = str(_git(repo_root, "rev-parse", "HEAD", text=True)).strip()
    entries: list[tuple[str, str, int, Literal["modified", "untracked"], str, str]] = []
    for path, (status, group, reason) in sorted(selections.items()):
        data = (repo_root / path).read_bytes()
        source_status: Literal["modified", "untracked"] = (
            "untracked" if status == "untracked" else "modified"
        )
        entries.append(
            (path.replace("\\", "/"), raw_sha256(data), len(data), source_status, group, reason)
        )
    identity_entries = [
        {
            "path": path,
            "sha256": digest,
            "size": size,
            "source_status": status,
            "contract_group": group,
            "selection_reason": reason,
        }
        for path, digest, size, status, group, reason in entries
    ]
    snapshot_id = canonical_sha256({"source_head": head, "files": identity_entries})
    snapshot_root = output_root / snapshot_id
    files: list[PipelineContractFileV1] = []
    for path, digest, size, status, group, reason in entries:
        source = repo_root / path
        relative_snapshot = f"files/{path}"
        target = snapshot_root / relative_snapshot
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o444)
        files.append(
            PipelineContractFileV1(
                path=path,
                sha256=digest,
                size=size,
                source_status=status,
                contract_group=group,
                selection_reason=reason,
                snapshot_path=relative_snapshot,
            )
        )
    acceptance_receipt_id = canonical_sha256(
        {"snapshot_id": snapshot_id, "files": [item.model_dump(mode="json") for item in files]}
    )
    manifest = PipelineContractSnapshotV1(
        source_worktree=str(repo_root.resolve()),
        source_head=head,
        snapshot_id=snapshot_id,
        snapshot_root=str(snapshot_root.resolve()),
        files=files,
        acceptance_receipt_id=acceptance_receipt_id,
    )
    manifest_path = snapshot_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_path.chmod(0o444)
    return manifest


def verify_pipeline_snapshot(manifest: PipelineContractSnapshotV1) -> None:
    """Fail when any content-addressed snapshot byte or identity changed."""

    root = Path(manifest.snapshot_root)
    for item in manifest.files:
        target = root / item.snapshot_path
        data = target.read_bytes()
        if len(data) != item.size or raw_sha256(data) != item.sha256:
            raise ValueError(f"pipeline snapshot mismatch: {item.path}")
        if os.access(target, os.W_OK):
            # Windows ACLs may report writable; the read-only file attribute is authoritative.
            if not target.stat().st_file_attributes & 1:  # type: ignore[attr-defined]
                raise ValueError(f"pipeline snapshot file is writable: {item.path}")
    expected = canonical_sha256(
        {
            "source_head": manifest.source_head,
            "files": [
                {
                    key: value
                    for key, value in item.model_dump(mode="json").items()
                    if key != "snapshot_path"
                }
                for item in manifest.files
            ],
        }
    )
    if expected != manifest.snapshot_id:
        raise ValueError("pipeline snapshot identity mismatch")
