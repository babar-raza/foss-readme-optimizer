"""Fail-closed evidence-tree enumeration, including Windows long paths."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def filesystem_path(path: Path) -> Path:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return Path(f"\\\\?\\{resolved}")
    return Path(resolved)


def enumerate_files(root: Path) -> list[tuple[Path, Path]]:
    """Return ``(relative, physical)`` files and raise on any traversal error."""

    def raise_walk_error(error: OSError) -> None:
        raise error

    physical_root = filesystem_path(root)
    files: list[tuple[Path, Path]] = []
    for current_root, directories, filenames in os.walk(
        physical_root,
        topdown=True,
        onerror=raise_walk_error,
    ):
        directories.sort()
        for filename in sorted(filenames):
            physical = Path(current_root) / filename
            mode = physical.stat().st_mode
            if not stat.S_ISREG(mode):
                raise OSError(f"unsupported non-regular evidence artifact: {physical}")
            files.append((physical.relative_to(physical_root), physical))
    return files
