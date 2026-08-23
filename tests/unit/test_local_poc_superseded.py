"""Tests for crash-safe superseded local README evidence."""

from __future__ import annotations

import hashlib
import json
from zipfile import ZipFile

from readme_agent.supervisor.local_poc_superseded import preserve_superseded_candidate


def test_packet_cache_is_compacted_and_interrupted_archive_resumes(tmp_path) -> None:
    bundle = tmp_path / "bundle"
    candidate = "# Candidate\n"
    candidate_hash = hashlib.sha256(candidate.encode()).hexdigest()
    (bundle / "candidate").mkdir(parents=True)
    (bundle / "candidate" / "README.md").write_text(candidate, encoding="utf-8")
    packet_cache = bundle / "review" / "bounded-packet-cache"
    packet_cache.mkdir(parents=True)
    packet_receipt = b'{"verdict":"ACCEPT"}\n'
    (packet_cache / ("a" * 64 + ".json")).write_bytes(packet_receipt)
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "source_revision": "b" * 40,
                "candidate_hash": candidate_hash,
                "lifecycle_status": "AGENT_REVIEWING",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    interrupted = bundle / "superseded" / candidate_hash[:16]
    (interrupted / "candidate").mkdir(parents=True)
    (interrupted / "candidate" / "README.md").write_text(candidate, encoding="utf-8")
    partial_cache = interrupted / "review" / "bounded-packet-cache"
    partial_cache.mkdir(parents=True)
    (partial_cache / ("a" * 64 + ".json")).write_bytes(packet_receipt[:5])

    preserved_hash = preserve_superseded_candidate(
        bundle,
        json.loads((bundle / "manifest.json").read_text(encoding="utf-8")),
        reason="candidate dependency changed",
    )

    assert preserved_hash == candidate_hash
    cache_archive = interrupted / "review" / "bounded-packet-cache.zip"
    assert cache_archive.is_file()
    assert not partial_cache.exists()
    with ZipFile(cache_archive) as archive:
        assert archive.namelist() == ["a" * 64 + ".json"]
        assert archive.read(archive.namelist()[0]) == packet_receipt
    record = json.loads((interrupted / "superseded.json").read_text(encoding="utf-8"))
    assert record["candidate_hash"] == candidate_hash
    assert record["packet_cache_archive"] == "review/bounded-packet-cache.zip"
    assert "review/bounded-packet-cache.zip" in (interrupted / "sha256sums.txt").read_text(
        encoding="utf-8"
    )

    assert (
        preserve_superseded_candidate(
            bundle,
            json.loads((bundle / "manifest.json").read_text(encoding="utf-8")),
            reason="candidate dependency changed",
        )
        == candidate_hash
    )
