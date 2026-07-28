"""Materialize a safe temporary snapshot from exact committed Git bytes."""

from __future__ import annotations

import subprocess
import tarfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory


def _validate_members(members: list[tarfile.TarInfo], destination: Path) -> None:
    root = destination.resolve()
    for member in members:
        relative = PurePosixPath(member.name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe git archive member: {member.name!r}")
        if not member.isdir() and not member.isfile():
            raise ValueError(f"unsupported git archive member: {member.name!r}")
        target = (destination / Path(*relative.parts)).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"git archive member escapes snapshot root: {member.name!r}")


def _existing_paths(repository_root: Path, revision: str, paths: Sequence[str]) -> list[str]:
    existing: list[str] = []
    for path in paths:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "cat-file", "-e", f"{revision}:{path}"],
            check=False,
            capture_output=True,
            timeout=20,
        )
        if result.returncode == 0:
            existing.append(path)
    if not existing:
        raise ValueError("none of the requested link-source paths exist at the pinned commit")
    return existing


@contextmanager
def materialize_git_snapshot(
    repository_root: Path,
    revision: str,
    paths: Sequence[str],
) -> Iterator[Path]:
    """Yield committed files at ``revision`` without reading sibling worktree bytes."""

    resolved_revision = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", f"{revision}^{{commit}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout.strip()
    if resolved_revision != revision:
        raise ValueError("requested link source revision is not one exact commit")
    existing_paths = _existing_paths(repository_root, revision, paths)

    with TemporaryDirectory(prefix="aspose-link-source-") as temporary:
        temporary_root = Path(temporary)
        archive_path = temporary_root / "source.tar"
        snapshot_root = temporary_root / "snapshot"
        snapshot_root.mkdir()
        with archive_path.open("wb") as archive_stream:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository_root),
                    "archive",
                    "--format=tar",
                    revision,
                    "--",
                    *existing_paths,
                ],
                check=True,
                stdout=archive_stream,
                stderr=subprocess.PIPE,
                timeout=120,
            )
        with tarfile.open(archive_path, mode="r") as archive:
            members = archive.getmembers()
            _validate_members(members, snapshot_root)
            archive.extractall(snapshot_root, members=members)
        yield snapshot_root
