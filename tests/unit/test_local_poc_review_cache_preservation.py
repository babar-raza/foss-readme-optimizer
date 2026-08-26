"""`preserve_bounded_review_cache` must survive a >MAX_PATH cache directory."""

from __future__ import annotations

import os

import pytest

from readme_agent.evidence.writer import win_long_path
from readme_agent.supervisor.local_poc_review_cache_preservation import (
    PACKET_CACHE_DIRECTORY,
    preserve_bounded_review_cache,
)


def _lp(path) -> str:
    return win_long_path(path) if os.name == "nt" else str(path)


def _make_long_bundle(tmp_path):
    """A bundle whose `review/bounded-packet-cache` exceeds 260 characters,
    matching the real shape: `<repo>/<40-char revision>/review/
    bounded-packet-cache/...` under a deep temp root."""

    bundle_dir = tmp_path
    for segment in ("x" * 60, "y" * 60, "z" * 60, "w" * 60):
        bundle_dir = bundle_dir / segment
    cache_dir = bundle_dir / "review" / PACKET_CACHE_DIRECTORY
    os.makedirs(_lp(cache_dir), exist_ok=True)
    with open(_lp(cache_dir / "entry.json"), "w", encoding="utf-8") as handle:
        handle.write("{}")
    assert len(os.path.abspath(cache_dir)) > 260, "fixture must exceed MAX_PATH to be meaningful"
    return bundle_dir, cache_dir


@pytest.mark.skipif(os.name != "nt", reason="MAX_PATH is a Windows-specific limit")
def test_survives_a_cache_directory_beyond_windows_max_path(tmp_path):
    """Three separate blind spots had to be found and fixed for this to work:

    1. `Path.is_dir()` on the entry guard returned `False` for a genuinely
       existing 372-character `cache_dir`, so the whole context manager
       silently no-op'd -- no exception, but nothing was ever preserved.
    2. `tempfile.TemporaryDirectory(dir=...)` -- via `mkdtemp` -- has no
       long-path handling and raised `FileNotFoundError` when `bundle_dir.parent`
       itself was long.
    3. `shutil.copytree()` has no long-path handling either, for whichever
       side (source or destination) happens to be the long one -- the restore
       direction puts it on the destination, the snapshot direction puts it
       on the source.
    """

    bundle_dir, cache_dir = _make_long_bundle(tmp_path)

    with preserve_bounded_review_cache(bundle_dir):
        # Simulate the derived review directory being rebuilt mid-context.
        import shutil

        shutil.rmtree(_lp(cache_dir), ignore_errors=True)
        assert not os.path.isdir(_lp(cache_dir))

    restored = cache_dir / "entry.json"
    assert os.path.isfile(_lp(restored))


def test_no_cache_directory_is_a_pure_pass_through(tmp_path):
    """Negative control: nothing to preserve must not raise or create anything."""

    bundle_dir = tmp_path / "bundle"
    entered = False
    with preserve_bounded_review_cache(bundle_dir):
        entered = True
    assert entered
    assert not (bundle_dir / "review" / PACKET_CACHE_DIRECTORY).exists()


def test_short_cache_directory_still_round_trips(tmp_path):
    """The fix must not regress the ordinary, well-under-MAX_PATH case."""

    bundle_dir = tmp_path / "bundle"
    cache_dir = bundle_dir / "review" / PACKET_CACHE_DIRECTORY
    cache_dir.mkdir(parents=True)
    (cache_dir / "entry.json").write_text("{}", encoding="utf-8")

    with preserve_bounded_review_cache(bundle_dir):
        import shutil

        shutil.rmtree(cache_dir)
        assert not cache_dir.is_dir()

    assert (cache_dir / "entry.json").is_file()
