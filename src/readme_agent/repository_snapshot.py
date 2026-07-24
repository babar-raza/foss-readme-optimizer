"""Capture and bind one immutable repository view to a logical supervisor run."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.errors import RepositorySnapshotError
from readme_agent.gitsafety._git import run_git
from readme_agent.inspection.file_inventory import scan
from readme_agent.profile.detector import build_profile
from readme_agent.profile.schema import PackageRoot
from readme_agent.registry.models import ProductEntry


class SnapshotProvenanceV1(BaseModel):
    """How the immutable view was captured."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: Literal["baseline_clone"] = "baseline_clone"
    clone_url: str = Field(min_length=1)
    source_ref: Literal["HEAD"] = "HEAD"
    git_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RepositorySnapshotV1(BaseModel):
    """Same-revision input consumed by every analysis stage in one run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str = Field(min_length=7)
    snapshot_root: str
    readme_path: str | None = None
    readme_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_roots: tuple[PackageRoot, ...] = ()
    captured_at: str
    provenance: SnapshotProvenanceV1

    @model_validator(mode="after")
    def _validate_paths_and_readme_pair(self) -> RepositorySnapshotV1:
        if len(self.org_repo.split("/")) != 2:
            raise ValueError("org_repo must be 'org/repo'")
        root = Path(self.snapshot_root)
        if not root.is_absolute():
            raise ValueError("snapshot_root must be absolute")
        if self.readme_path is not None and Path(self.readme_path).is_absolute():
            raise ValueError("readme_path must be relative to snapshot_root")
        if (self.readme_path is None) != (self.readme_sha256 is None):
            raise ValueError("readme_path and readme_sha256 must both be present or absent")
        return self

    @property
    def root_path(self) -> Path:
        return Path(self.snapshot_root)


_CURRENT_SNAPSHOT: ContextVar[RepositorySnapshotV1 | None] = ContextVar(
    "readme_agent_repository_snapshot",
    default=None,
)
_LOCAL_FACT_VERIFICATION_ALLOWED: ContextVar[bool] = ContextVar(
    "readme_agent_local_fact_verification_allowed",
    default=False,
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_value(root: Path, args: list[str], label: str) -> str:
    result = run_git(args, cwd=root)
    if result.returncode != 0:
        raise RepositorySnapshotError(f"cannot capture {label}: {result.stderr}")
    return result.stdout


def _git_inventory(root: Path) -> tuple[str, str]:
    revision = _git_value(root, ["rev-parse", "HEAD"], "repository revision").strip()
    tree_listing = _git_value(
        root,
        ["ls-tree", "-r", "--full-tree", "HEAD"],
        "repository tree inventory",
    )
    return revision, _sha256_bytes(tree_listing.encode("utf-8"))


def capture_repository_snapshot(
    entry: ProductEntry,
    snapshot_root: Path,
) -> RepositorySnapshotV1:
    """Capture checksums and package roots from an already-created baseline clone."""

    root = snapshot_root.resolve()
    if not root.is_dir():
        raise RepositorySnapshotError(f"snapshot root does not exist: {root}")
    revision, inventory_sha256 = _git_inventory(root)
    inventory = scan(root)
    readme_path = (
        inventory.readme_path.relative_to(root).as_posix()
        if inventory.readme_path is not None
        else None
    )
    readme_sha256 = (
        _sha256_bytes(inventory.readme_path.read_bytes())
        if inventory.readme_path is not None
        else None
    )
    profile = build_profile(entry.org_repo, root)
    return RepositorySnapshotV1(
        org_repo=entry.org_repo,
        source_revision=revision,
        snapshot_root=str(root),
        readme_path=readme_path,
        readme_sha256=readme_sha256,
        inventory_sha256=inventory_sha256,
        package_roots=tuple(profile.package_roots),
        captured_at=datetime.now(UTC).isoformat(),
        provenance=SnapshotProvenanceV1(
            clone_url=entry.clone_url,
            git_tree_sha256=inventory_sha256,
        ),
    )


def verify_repository_snapshot(snapshot: RepositorySnapshotV1) -> None:
    """Fail closed if the bound clone or its checked README changed during the run."""

    root = snapshot.root_path
    if not root.is_dir():
        raise RepositorySnapshotError(f"snapshot root disappeared: {root}")
    revision, inventory_sha256 = _git_inventory(root)
    if revision != snapshot.source_revision:
        raise RepositorySnapshotError(
            f"snapshot revision drifted from {snapshot.source_revision} to {revision}"
        )
    if inventory_sha256 != snapshot.inventory_sha256:
        raise RepositorySnapshotError("snapshot Git tree inventory changed during the run")
    if snapshot.readme_path is not None:
        readme = root / snapshot.readme_path
        if not readme.is_file():
            raise RepositorySnapshotError("snapshot README disappeared during the run")
        if _sha256_bytes(readme.read_bytes()) != snapshot.readme_sha256:
            raise RepositorySnapshotError("snapshot README changed during the run")
    for package_root in snapshot.package_roots:
        if not (root / package_root.manifest_path).is_file():
            raise RepositorySnapshotError(
                f"snapshot package manifest disappeared: {package_root.manifest_path}"
            )


def current_repository_snapshot(org_repo: str | None = None) -> RepositorySnapshotV1 | None:
    """Return the active view, rejecting accidental cross-repository reuse."""

    snapshot = _CURRENT_SNAPSHOT.get()
    if snapshot is not None and org_repo is not None and snapshot.org_repo != org_repo:
        raise RepositorySnapshotError(
            f"active snapshot is for {snapshot.org_repo}, not requested repository {org_repo}"
        )
    return snapshot


def local_fact_verification_allowed() -> bool:
    """Whether this profile permits isolated build/example subprocesses."""

    return _LOCAL_FACT_VERIFICATION_ALLOWED.get()


@contextmanager
def repository_snapshot_scope(
    snapshot: RepositorySnapshotV1,
    *,
    allow_local_fact_verification: bool = False,
) -> Iterator[RepositorySnapshotV1]:
    """Bind one snapshot to all nested deterministic and agentic stages."""

    active = _CURRENT_SNAPSHOT.get()
    if active is not None and active != snapshot:
        raise RepositorySnapshotError("cannot replace an active repository snapshot")
    token = _CURRENT_SNAPSHOT.set(snapshot)
    verification_token = _LOCAL_FACT_VERIFICATION_ALLOWED.set(allow_local_fact_verification)
    try:
        verify_repository_snapshot(snapshot)
        yield snapshot
        verify_repository_snapshot(snapshot)
    finally:
        _LOCAL_FACT_VERIFICATION_ALLOWED.reset(verification_token)
        _CURRENT_SNAPSHOT.reset(token)
