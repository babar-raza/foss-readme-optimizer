"""Preserve exact-key bounded-review caches across downstream evidence pruning."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from readme_agent.evidence.writer import win_long_path

PACKET_CACHE_DIRECTORY = "bounded-packet-cache"


def _long_path(path: Path | str) -> str | Path:
    """`path`, prefixed for Win32 MAX_PATH safety when running on Windows.

    `cache_dir` is `<bundle>/review/bounded-packet-cache/...` -- nested under
    the bundle's own already-long `<repo>/<40-char revision>/` path, which
    measured 372 characters on a real reproduction -- while `snapshot` is a
    short-prefixed temp directory, so *either* side can be the one that
    crosses 260 characters depending on which direction is copying: the
    restore direction (temp -> cache_dir) puts the long path on the
    destination, the snapshot direction (cache_dir -> temp) puts it on the
    source. None of `tempfile.mkdtemp` (via `TemporaryDirectory(dir=...)`),
    `Path.mkdir`, or `shutil.copytree` have long-path handling of their own,
    unlike `os.replace` elsewhere in this codebase (see `evidence/writer.py::
    win_long_path`, which this reuses); safe to prefix every one of them here
    since, unlike `local_poc_superseded.py`'s copy, nothing downstream
    compares a walked path back against the un-prefixed original.
    """

    return win_long_path(path) if os.name == "nt" else path


@contextmanager
def preserve_bounded_review_cache(bundle_dir: Path) -> Iterator[None]:
    """Retain reusable receipts while their derived review directory is rebuilt.

    Cache consumers independently validate every receipt's complete input identity.
    Preservation is therefore only an execution optimization and never acceptance.
    """

    cache_dir = bundle_dir / "review" / PACKET_CACHE_DIRECTORY
    # `Path.is_dir()` itself has no long-path handling on Windows: it returned
    # `False` for a genuinely-existing 372-character `cache_dir` on a real
    # reproduction, which took this early-return path and skipped every other
    # fix in this module -- preservation silently never ran at all.
    if not os.path.isdir(_long_path(cache_dir)):
        yield
        return

    with TemporaryDirectory(
        prefix="readme-agent-review-cache-", dir=_long_path(bundle_dir.parent)
    ) as temp:
        snapshot = Path(temp) / PACKET_CACHE_DIRECTORY
        shutil.copytree(_long_path(cache_dir), _long_path(snapshot))
        try:
            yield
        finally:
            os.makedirs(_long_path(cache_dir.parent), exist_ok=True)
            shutil.copytree(_long_path(snapshot), _long_path(cache_dir), dirs_exist_ok=True)
