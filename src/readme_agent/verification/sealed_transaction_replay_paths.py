"""Path safety and sealed-bundle walking for replay attestation."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from readme_agent.evidence.file_inventory import filesystem_path
from readme_agent.verification.sealed_transaction_replay_vocabulary import _HEX64


def _resolve_declared_path(root: Path, relative_posix: str) -> Path | None:
    """Resolve a declared relative path beneath root, rejecting any symlink in the chain."""

    current = root
    parts = relative_posix.split("/")
    for part in parts[:-1]:
        current = current / part
        try:
            entry_stat = os.lstat(current)
        except OSError:
            return None
        if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISDIR(entry_stat.st_mode):
            return None
    final = current / parts[-1]
    try:
        final_stat = os.lstat(final)
    except OSError:
        return None
    if stat.S_ISLNK(final_stat.st_mode) or not stat.S_ISREG(final_stat.st_mode):
        return None
    try:
        resolved_root = root.resolve()
        resolved_final = final.resolve()
        resolved_final.relative_to(resolved_root)
    except (OSError, ValueError):
        return None
    return final


def _is_non_semantic(
    relative_posix: str,
    *,
    non_semantic_paths: frozenset[str],
    non_semantic_basenames: frozenset[str],
    non_semantic_suffixes: frozenset[str],
    non_semantic_directories: frozenset[str],
) -> bool:
    if relative_posix in non_semantic_paths:
        return True
    segments = relative_posix.split("/")
    basename = segments[-1]
    if basename in non_semantic_basenames:
        return True
    if any(basename.endswith(suffix) for suffix in non_semantic_suffixes):
        return True
    return any(segment in non_semantic_directories for segment in segments[:-1])


def _under_lifecycle_directory(
    relative_posix: str, lifecycle_directories: tuple[str, ...]
) -> str | None:
    for directory in lifecycle_directories:
        prefix = directory.rstrip("/") + "/"
        if relative_posix.startswith(prefix):
            return directory
    return None


class _WalkResult:
    __slots__ = ("regular_files", "unsafe_paths", "file_count", "total_bytes", "walk_error")

    def __init__(self) -> None:
        self.regular_files: list[str] = []
        self.unsafe_paths: list[str] = []
        self.file_count = 0
        self.total_bytes = 0
        self.walk_error: str | None = None


def _walk_bundle(root: Path, *, max_files: int, max_bytes: int) -> _WalkResult:
    result = _WalkResult()
    physical_root = filesystem_path(root)
    root_str = str(physical_root)
    try:
        for dirpath, dirnames, filenames in os.walk(root_str, topdown=True, followlinks=False):
            dirnames.sort()
            safe_dirnames: list[str] = []
            for name in dirnames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root_str).replace(os.sep, "/")
                try:
                    entry_stat = os.lstat(full)
                except OSError as exc:
                    result.walk_error = str(exc)
                    return result
                if stat.S_ISLNK(entry_stat.st_mode):
                    result.unsafe_paths.append(rel)
                    continue
                safe_dirnames.append(name)
            dirnames[:] = safe_dirnames
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root_str).replace(os.sep, "/")
                try:
                    entry_stat = os.lstat(full)
                except OSError as exc:
                    result.walk_error = str(exc)
                    return result
                if stat.S_ISLNK(entry_stat.st_mode) or not stat.S_ISREG(entry_stat.st_mode):
                    result.unsafe_paths.append(rel)
                    continue
                result.file_count += 1
                result.total_bytes += entry_stat.st_size
                if result.file_count > max_files or result.total_bytes > max_bytes:
                    result.walk_error = "inventory_bounds_exceeded"
                    return result
                result.regular_files.append(rel)
    except OSError as exc:
        result.walk_error = str(exc)
    result.regular_files.sort()
    result.unsafe_paths.sort()
    return result


def _parse_sha256sums(path: Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    duplicates: list[str] = []
    if not path.is_file():
        return entries, duplicates
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return entries, duplicates
    for line in text.splitlines():
        if not line.strip() or "  " not in line:
            continue
        digest, relpath = line.split("  ", 1)
        if not _HEX64.match(digest) or not relpath:
            continue
        if relpath in entries:
            duplicates.append(relpath)
            continue
        entries[relpath] = digest
    return entries, sorted(set(duplicates))
