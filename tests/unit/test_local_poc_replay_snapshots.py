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
                "facts_hash": "d" * 64,
                "fact_acceptance_contract_hash": "e" * 64,
                "candidate_hash": "b" * 64,
                "candidate_stage_dependency_key": "f" * 64,
                "prompt_registry_content_hash": "1" * 64,
                "prompt_dependency_hashes": {"author": "2" * 64},
                "deterministic_validation_hash": "3" * 64,
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


def test_changed_fact_contract_uses_a_distinct_transaction_root(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    first = materialize_transaction_snapshot(bundle, label="first")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["fact_acceptance_contract_hash"] = "4" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    refresh_sha256sums(bundle)

    changed = materialize_transaction_snapshot(bundle, label="first")

    assert changed != first
    assert changed.parent != first.parent


def test_snapshot_copies_hash_named_packet_cache_through_short_windows_path(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    _add_packet_cache(bundle)

    first = materialize_transaction_snapshot(bundle, label="first")

    assert first.parent.parent.name == "_tx"
    assert first.name == "f"
    assert (first / "review" / "bounded-packet-cache" / f"{'d' * 64}.json").is_file()
