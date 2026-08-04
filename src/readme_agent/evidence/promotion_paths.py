"""Compact, checksum-bound storage paths for promoted README evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from readme_agent.evidence.file_inventory import enumerate_files, filesystem_path


def compact_readme_path(
    repository: str,
    platform: str,
    source_revision: str,
    candidate_sha256: str,
) -> Path:
    family = repository.split("/", 1)[0].removeprefix("aspose-").removesuffix("-foss")
    return (
        Path("repositories")
        / platform
        / f"{family}--{source_revision[:12]}--{candidate_sha256[:12]}"
        / "README.md"
    )


def enumerate_readmes(root: Path) -> set[Path]:
    """Return every README below *root*, failing if any subtree is unreadable."""

    return {
        (root / relative).resolve()
        for relative, physical in enumerate_files(root)
        if physical.name == "README.md"
    }


def migrate_preserved_entry(
    item: dict,
    *,
    repo_root: Path,
    output_root: Path,
    read_committed_file: Callable[[Path], bytes],
) -> dict:
    """Move a preserved manifest row to the compact path without changing its bytes."""

    required = {
        "repository",
        "platform",
        "source_revision",
        "candidate_sha256",
        "committed_readme",
    }
    if not required <= item.keys():
        raise ValueError(f"preserved manifest row is incomplete: {item!r}")
    old_relative = Path(str(item["committed_readme"]))
    old_source = repo_root / old_relative
    old_source.resolve().relative_to(output_root.resolve())
    relative = compact_readme_path(
        str(item["repository"]),
        str(item["platform"]),
        str(item["source_revision"]),
        str(item["candidate_sha256"]),
    )
    destination = output_root / relative
    expected_hash = str(item["candidate_sha256"])
    if old_source == destination:
        content = destination.read_bytes()
    else:
        try:
            content = old_source.read_bytes()
        except OSError:
            content = read_committed_file(old_relative)
        if hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError(f"preserved README hash mismatch for {item['repository']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    if (
        hashlib.sha256(content).hexdigest() != expected_hash
        or hashlib.sha256(destination.read_bytes()).hexdigest() != expected_hash
    ):
        raise ValueError(f"preserved README hash mismatch for {item['repository']}")
    if old_source != destination:
        try:
            filesystem_path(old_source).unlink()
        except FileNotFoundError:
            pass
        _remove_empty_parents(
            old_source,
            output_root / "repositories" / str(item["platform"]),
        )
    migrated = dict(item)
    migrated["committed_readme"] = destination.relative_to(repo_root).as_posix()
    return migrated


def remove_preserved_entry(
    item: dict,
    *,
    repo_root: Path,
    output_root: Path,
    read_committed_file: Callable[[Path], bytes],
) -> None:
    """Remove a checksum-verified superseded README after its replacement is sealed."""

    old_relative = Path(str(item["committed_readme"]))
    old_source = repo_root / old_relative
    old_source.resolve().relative_to(output_root.resolve())
    try:
        content = old_source.read_bytes()
    except OSError:
        content = read_committed_file(old_relative)
    if hashlib.sha256(content).hexdigest() != str(item["candidate_sha256"]):
        raise ValueError(f"superseded README hash mismatch for {item['repository']}")
    try:
        filesystem_path(old_source).unlink()
    except FileNotFoundError:
        pass
    _remove_empty_parents(
        old_source,
        output_root / "repositories" / str(item["platform"]),
    )


def _remove_empty_parents(path: Path, stop: Path) -> None:
    current = path.parent
    while current != stop and current.is_relative_to(stop):
        try:
            filesystem_path(current).rmdir()
        except OSError:
            break
        current = current.parent
