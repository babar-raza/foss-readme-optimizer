"""Inventory repository-owned example fixtures from one immutable Git tree."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RECOGNIZED_FIXTURE_EXTENSIONS = (
    ".3ds",
    ".dae",
    ".doc",
    ".docx",
    ".eml",
    ".eot",
    ".fbx",
    ".glb",
    ".gltf",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".mbox",
    ".msg",
    ".obj",
    ".one",
    ".otf",
    ".pdf",
    ".ply",
    ".png",
    ".ppt",
    ".pptx",
    ".stl",
    ".svg",
    ".tif",
    ".tiff",
    ".ttf",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RepositoryFixturePathV1(_StrictModel):
    path: str = Field(min_length=1)
    extension: str = Field(min_length=1)
    object_id: str = Field(min_length=7)
    size: int = Field(ge=0)


class SnapshotFixtureInventoryV1(_StrictModel):
    """Complete or explicitly unscanned fixture view for one immutable Git tree."""

    schema_version: Literal[1] = 1
    scan_status: Literal["complete", "unscanned"]
    scan_root: Literal["."] = "."
    source_revision: str | None = None
    tree_id: str | None = None
    inventory_sha256: str | None = None
    tracked_file_count: int | None = Field(default=None, ge=0)
    recognized_extensions: list[str]
    fixture_paths: list[RepositoryFixturePathV1]
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _status_is_truthful(self) -> SnapshotFixtureInventoryV1:
        if self.recognized_extensions != sorted(set(self.recognized_extensions)):
            raise ValueError("fixture extensions must be unique and sorted")
        if [item.path for item in self.fixture_paths] != sorted(
            {item.path for item in self.fixture_paths}
        ):
            raise ValueError("fixture paths must be unique and sorted")
        if self.scan_status == "complete":
            if not all(
                (
                    self.source_revision,
                    self.tree_id,
                    self.inventory_sha256,
                    self.tracked_file_count is not None,
                )
            ):
                raise ValueError("complete fixture inventory requires revision and inventory proof")
            if self.failure_reason is not None:
                raise ValueError("complete fixture inventory cannot carry a failure reason")
        elif self.fixture_paths or any(
            value is not None
            for value in (self.tree_id, self.inventory_sha256, self.tracked_file_count)
        ):
            raise ValueError("unscanned fixture inventory cannot imply repository absence")
        elif not self.failure_reason:
            raise ValueError("unscanned fixture inventory requires a failure reason")
        return self

    def matching_paths(self, reference: str) -> tuple[str, ...]:
        """Return tracked fixture paths matching a README-relative reference or basename."""

        normalized = reference.replace("\\", "/").removeprefix("./")
        name = PurePosixPath(normalized).name.casefold()
        return tuple(
            item.path
            for item in self.fixture_paths
            if item.path.casefold() == normalized.casefold()
            or PurePosixPath(item.path).name.casefold() == name
        )


def _unscanned(source_revision: str | None, reason: str) -> SnapshotFixtureInventoryV1:
    return SnapshotFixtureInventoryV1(
        scan_status="unscanned",
        source_revision=source_revision,
        recognized_extensions=list(RECOGNIZED_FIXTURE_EXTENSIONS),
        fixture_paths=[],
        failure_reason=reason,
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )


def snapshot_fixture_inventory(
    root: Path,
    source_revision: str | None,
) -> SnapshotFixtureInventoryV1:
    """Return a revision-bound tracked fixture inventory or an explicit unscanned result."""

    if not source_revision:
        return _unscanned(None, "missing_source_revision")
    try:
        top = _git(root, "rev-parse", "--show-toplevel")
        head = _git(root, "rev-parse", "HEAD")
        revision = _git(root, "rev-parse", f"{source_revision}^{{commit}}")
    except OSError:
        return _unscanned(source_revision, "git_unavailable")
    if any(result.returncode != 0 for result in (top, head, revision)):
        return _unscanned(source_revision, "git_revision_unavailable")
    try:
        top_path = Path(top.stdout.decode("utf-8").strip()).resolve()
        head_id = head.stdout.decode("ascii").strip()
        revision_id = revision.stdout.decode("ascii").strip()
    except UnicodeDecodeError:
        return _unscanned(source_revision, "git_identity_decode_failed")
    if top_path != root.resolve():
        return _unscanned(source_revision, "scan_root_is_not_git_toplevel")
    if head_id != revision_id:
        return _unscanned(source_revision, "worktree_head_differs_from_source_revision")
    dirty = _git(root, "diff", "--quiet", "--no-ext-diff", "--ignore-submodules", "HEAD", "--")
    if dirty.returncode != 0:
        reason = "tracked_worktree_modified" if dirty.returncode == 1 else "tracked_scan_failed"
        return _unscanned(source_revision, reason)
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    listing = _git(root, "ls-tree", "-r", "-z", "-l", "--full-tree", "HEAD")
    if tree.returncode != 0 or listing.returncode != 0:
        return _unscanned(source_revision, "git_tree_enumeration_failed")
    try:
        tree_id = tree.stdout.decode("ascii").strip()
        records = [record for record in listing.stdout.split(b"\0") if record]
        fixtures: list[RepositoryFixturePathV1] = []
        for record in records:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id, raw_size = metadata.split(maxsplit=3)
            if object_type != b"blob" or raw_size == b"-":
                return _unscanned(source_revision, "non_blob_tree_entry_requires_separate_scan")
            path = raw_path.decode("utf-8")
            extension = PurePosixPath(path).suffix.casefold()
            if extension in RECOGNIZED_FIXTURE_EXTENSIONS:
                fixtures.append(
                    RepositoryFixturePathV1(
                        path=path,
                        extension=extension,
                        object_id=object_id.decode("ascii"),
                        size=int(raw_size),
                    )
                )
    except (UnicodeDecodeError, ValueError):
        return _unscanned(source_revision, "git_tree_inventory_malformed")
    return SnapshotFixtureInventoryV1(
        scan_status="complete",
        source_revision=head_id,
        tree_id=tree_id,
        inventory_sha256=hashlib.sha256(listing.stdout).hexdigest(),
        tracked_file_count=len(records),
        recognized_extensions=list(RECOGNIZED_FIXTURE_EXTENSIONS),
        fixture_paths=sorted(fixtures, key=lambda item: item.path),
    )


__all__ = [
    "RECOGNIZED_FIXTURE_EXTENSIONS",
    "RepositoryFixturePathV1",
    "SnapshotFixtureInventoryV1",
    "snapshot_fixture_inventory",
]
