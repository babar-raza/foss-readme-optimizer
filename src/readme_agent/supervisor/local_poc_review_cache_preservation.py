"""Preserve exact-key bounded-review caches across downstream evidence pruning."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

PACKET_CACHE_DIRECTORY = "bounded-packet-cache"


@contextmanager
def preserve_bounded_review_cache(bundle_dir: Path) -> Iterator[None]:
    """Retain reusable receipts while their derived review directory is rebuilt.

    Cache consumers independently validate every receipt's complete input identity.
    Preservation is therefore only an execution optimization and never acceptance.
    """

    cache_dir = bundle_dir / "review" / PACKET_CACHE_DIRECTORY
    if not cache_dir.is_dir():
        yield
        return

    with TemporaryDirectory(prefix="readme-agent-review-cache-", dir=bundle_dir.parent) as temp:
        snapshot = Path(temp) / PACKET_CACHE_DIRECTORY
        shutil.copytree(cache_dir, snapshot)
        try:
            yield
        finally:
            cache_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(snapshot, cache_dir, dirs_exist_ok=True)
