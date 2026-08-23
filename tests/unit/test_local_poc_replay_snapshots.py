"""Immutable local-POC first/replay transaction snapshots."""

from __future__ import annotations

import json

import pytest

from readme_agent.evidence.writer import refresh_sha256sums
from readme_agent.supervisor.local_poc_replay_snapshots import (
    ReplaySnapshotError,
    materialize_transaction_snapshot,
)


def _bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "candidate").mkdir()
    (bundle / "candidate" / "README.md").write_text("# Candidate\n", encoding="utf-8")
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "org_repo": "example-org/example-repo",
                "source_revision": "a" * 40,
                "candidate_hash": "b" * 64,
                "reviewer_standard_hash": "c" * 64,
            }
        ),
        encoding="utf-8",
    )
    refresh_sha256sums(bundle)
    return bundle


def _add_packet_cache(bundle) -> None:
    cache = bundle / "review" / "bounded-packet-cache"
    cache.mkdir(parents=True)
    (cache / f"{'d' * 64}.json").write_text('{"verdict":"ACCEPT"}\n', encoding="utf-8")
    refresh_sha256sums(bundle)


def test_first_snapshot_is_immutable_and_idempotently_reused(tmp_path) -> None:
    bundle = _bundle(tmp_path)

    first = materialize_transaction_snapshot(bundle, label="first")
    repeated = materialize_transaction_snapshot(bundle, label="first")

    assert repeated == first
    assert (first / "candidate" / "README.md").read_text(encoding="utf-8") == "# Candidate\n"
    assert not (first / "superseded").exists()


def test_existing_snapshot_corruption_fails_instead_of_overwriting(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    first = materialize_transaction_snapshot(bundle, label="first")
    (first / "candidate" / "README.md").write_text("corrupt\n", encoding="utf-8")

    with pytest.raises(ReplaySnapshotError, match="checksum validation"):
        materialize_transaction_snapshot(bundle, label="first")


def test_snapshot_copies_hash_named_packet_cache_through_short_windows_path(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    _add_packet_cache(bundle)

    first = materialize_transaction_snapshot(bundle, label="first")

    assert first.parent.parent.name == "_tx"
    assert first.name == "f"
    assert (first / "review" / "bounded-packet-cache" / f"{'d' * 64}.json").is_file()
