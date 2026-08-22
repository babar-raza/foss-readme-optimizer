from pathlib import Path

import pytest

from readme_agent.facts.aspose_benchmark_profile import (
    _validate_complete_audit,
    build_quality_profile,
    inventory_tree,
)


def test_inventory_tree_is_content_addressed_and_deterministic(tmp_path: Path) -> None:
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "two.txt").write_text("two\n", encoding="utf-8")
    (tmp_path / "one.txt").write_text("one\n", encoding="utf-8")

    first = inventory_tree(tmp_path)
    second = inventory_tree(tmp_path)

    assert first == second
    assert first["file_count"] == 2
    assert [entry["path"] for entry in first["files"]] == ["b/two.txt", "one.txt"]


def test_quality_profile_separates_benchmark_value_from_authority() -> None:
    profile = build_quality_profile(
        audit={"total": 31, "clean_count": 9, "dirty_count": 22},
        snapshot_sha256="a" * 64,
    )

    assert profile["state"] == "BENCHMARK_PROFILE_FROZEN"
    assert profile["runtime_dependency_on_aspose_org"] is False
    assert set(profile["disposition_counts"]) == {
        "accepted",
        "adapted",
        "quarantined",
        "not_applicable",
    }
    assert profile["authority"]["facts"].startswith("current immutable product repositories")


def test_complete_audit_rejects_skips_or_denominator_drift() -> None:
    with pytest.raises(ValueError, match="denominator mismatch"):
        _validate_complete_audit({"total": 30, "products": [{}] * 30, "skipped": []}, 31)
    with pytest.raises(ValueError, match="skipped"):
        _validate_complete_audit({"total": 31, "products": [{}] * 31, "skipped": [{}]}, 31)
