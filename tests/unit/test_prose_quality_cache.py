"""Direct unit tests for `verification/prose_quality_cache.py` (Decision #110/#113,
requirement LLM-023, 2026-08-27 production recovery sprint)."""

from __future__ import annotations

from readme_agent.verification.prose_quality_cache import (
    load_cached_prose_quality,
    persist_prose_quality_verdict,
    prose_quality_cache_key,
)


def test_cache_key_is_stable_for_identical_text():
    assert prose_quality_cache_key("same text") == prose_quality_cache_key("same text")


def test_cache_key_differs_for_different_text():
    assert prose_quality_cache_key("text a") != prose_quality_cache_key("text b")


def test_cache_key_differs_across_contract_versions():
    key_v1 = prose_quality_cache_key("same text", contract_version="v1")
    key_v2 = prose_quality_cache_key("same text", contract_version="v2")
    assert key_v1 != key_v2


def test_load_on_missing_file_is_a_clean_miss(tmp_path):
    assert load_cached_prose_quality(tmp_path / "missing.json", "any-key") is None


def test_load_on_corrupt_file_is_a_clean_miss_not_a_crash(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text("not valid json{{{", encoding="utf-8")
    assert load_cached_prose_quality(path, "any-key") is None


def test_persist_then_load_round_trips_the_exact_verdict(tmp_path):
    path = tmp_path / "nested" / "cache.json"
    key = prose_quality_cache_key("some final readme text")
    verdict = {"flagged": True, "corroborated": True, "quoted_span": "x", "reason": "y"}

    persist_prose_quality_verdict(path, key, verdict)

    assert load_cached_prose_quality(path, key) == verdict


def test_persist_preserves_other_keys_already_in_the_file(tmp_path):
    path = tmp_path / "cache.json"
    key_a = prose_quality_cache_key("text a")
    key_b = prose_quality_cache_key("text b")

    persist_prose_quality_verdict(path, key_a, {"flagged": False})
    persist_prose_quality_verdict(path, key_b, {"flagged": True})

    assert load_cached_prose_quality(path, key_a) == {"flagged": False}
    assert load_cached_prose_quality(path, key_b) == {"flagged": True}


def test_a_wrong_key_is_a_miss_even_when_the_file_has_entries(tmp_path):
    path = tmp_path / "cache.json"
    key = prose_quality_cache_key("known text")
    persist_prose_quality_verdict(path, key, {"flagged": False})

    other_key = prose_quality_cache_key("different text")
    assert load_cached_prose_quality(path, other_key) is None


def test_persist_writes_atomically_via_a_staging_file(tmp_path):
    path = tmp_path / "cache.json"
    key = prose_quality_cache_key("text")
    persist_prose_quality_verdict(path, key, {"flagged": False})

    assert path.is_file()
    assert not path.with_suffix(".json.tmp").exists()
