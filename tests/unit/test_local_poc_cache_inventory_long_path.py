r"""`_inventory_valid` must see the same files the checksum writer sealed.

`evidence/writer.py` seals and verifies a bundle through
`evidence/file_inventory.py::enumerate_files()`, which prefixes `\?\` on Windows and
raises on any traversal error. `supervisor/local_poc_cache.py::_inventory_valid()` had
hand-rolled a second enumeration over the same tree using `Path.rglob("*")`, which has
neither property: pathlib silently swallows the `os.scandir` failure Win32 raises for a
path at or beyond MAX_PATH, so the directory's files simply never appear.

The real bundle shape puts a packet-cache entry at
`<repo>/<40-char revision>/review/bounded-packet-cache/<64-hex>.json`, which
`win_long_path`'s own docstring records as landing on 260 characters for
`aspose-note-foss__Aspose.Note-FOSS-for-Python` and 259 for
`aspose-3d-foss__Aspose.3D-FOSS-for-Python`. So on Windows the sealed inventory listed
every file while the validator counted only the short-path subset, the two sets could
never be equal, and `evaluate_approved_local_poc_cache()` returned
`artifact_inventory_invalid` for a bundle that was in fact intact -- which made
`NO_OP_PROVEN` unreachable for exactly the repositories whose names are long enough.

Observed live 2026-08-29 in
`test_local_poc_records_snapshot_and_profile_before_later_stages`: sealed inventory 64
entries, `rglob` saw 46, and the cache directory held the missing 18 (46 + 18 = 64).
"""

from __future__ import annotations

import os

import pytest

from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums, win_long_path
from readme_agent.supervisor.local_poc_cache import _inventory_valid, _load_inventory

_MAX_PATH = 260


def _lp(path) -> str:
    return win_long_path(path) if os.name == "nt" else str(path)


def _make_long_bundle(tmp_path):
    """Reproduce the real bundle shape: a bundle root short enough that its own
    `sha256sums.txt` and `manifest.json` open normally, with a
    `review/bounded-packet-cache/<64-hex>.json` entry that crosses MAX_PATH. That
    asymmetry is the whole point -- the inventory loads fine, so the failure surfaces
    only as a set mismatch, never as a read error anyone would notice.

    The padding depth is derived, not hardcoded. `scripts/governance/run_full_pytest.py`
    deliberately passes a short `--basetemp` (`%TEMP%/ra-p`, "keep this deliberately
    short"), while a bare `pytest` run gets a much longer one. A fixed number of padding
    segments therefore lands on the wrong side of 260 depending on which runner invoked
    the test -- the first version of this fixture used a fixed 40+40 and silently passed
    standalone while failing inside the canonical suite. Both bounds are asserted below,
    so the fixture fails loudly rather than quietly testing nothing.
    """

    suffix = len(os.path.join("review", "bounded-packet-cache", f"{0:064x}.json"))
    bundle_dir = tmp_path
    # Grow until the deepest cache entry is at or beyond MAX_PATH, while keeping the
    # bundle root itself comfortably under it so the inventory still opens normally.
    while len(os.path.abspath(bundle_dir)) + 1 + suffix < _MAX_PATH:
        bundle_dir = bundle_dir / ("r" * 40)
    cache_dir = bundle_dir / "review" / "bounded-packet-cache"
    os.makedirs(_lp(cache_dir), exist_ok=True)
    with open(_lp(bundle_dir / "manifest.json"), "w", encoding="utf-8") as handle:
        handle.write("{}")
    for index in range(3):
        with open(_lp(cache_dir / f"{index:064x}.json"), "w", encoding="utf-8") as handle:
            handle.write(f'{{"packet": {index}}}')
    entry = cache_dir / f"{0:064x}.json"
    # `win_long_path`'s own docstring: Win32 rejects a path "at or beyond 260".
    assert len(os.path.abspath(entry)) >= _MAX_PATH, "fixture cache entry must reach MAX_PATH"
    assert len(os.path.abspath(bundle_dir / "sha256sums.txt")) < _MAX_PATH, (
        "fixture bundle root must stay under MAX_PATH so the inventory itself still loads"
    )
    return bundle_dir


@pytest.mark.skipif(os.name != "nt", reason="MAX_PATH is a Windows-specific limit")
def test_inventory_validates_a_bundle_whose_cache_path_exceeds_max_path(tmp_path):
    bundle_dir = _make_long_bundle(tmp_path)
    refresh_sha256sums(bundle_dir)

    # The writer's own verifier already handles this correctly -- it is the reference.
    assert verify_sha256sums(bundle_dir) is True

    expected, inventory_sha256 = _load_inventory(bundle_dir)
    assert inventory_sha256 is not None
    assert len(expected) == 4, expected
    assert sum("bounded-packet-cache" in relative for relative in expected) == 3

    # The cache validator must agree with the writer, not under-enumerate.
    assert _inventory_valid(bundle_dir, expected) is True


@pytest.mark.skipif(os.name != "nt", reason="MAX_PATH is a Windows-specific limit")
def test_inventory_still_rejects_a_genuinely_corrupt_long_path_bundle(tmp_path):
    """Negative control: the long-path fix must not turn the check into a rubber stamp."""

    bundle_dir = _make_long_bundle(tmp_path)
    refresh_sha256sums(bundle_dir)
    expected, _ = _load_inventory(bundle_dir)

    cache_entry = bundle_dir / "review" / "bounded-packet-cache" / f"{0:064x}.json"
    with open(_lp(cache_entry), "w", encoding="utf-8") as handle:
        handle.write('{"packet": "tampered"}')

    assert _inventory_valid(bundle_dir, expected) is False
