import json
from pathlib import Path

import pytest

from readme_agent.errors import ConfigError
from readme_agent.registry import loader

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_real_products_json_loads_and_has_25_entries():
    entries = loader.load_products(REPO_ROOT / "data" / "products.json")
    assert len(entries) == 25


def test_exactly_three_entries_are_enabled():
    entries = loader.load_products(REPO_ROOT / "data" / "products.json")
    enabled = [e for e in entries if e.mode != "disabled"]
    assert {e.org_repo for e in enabled} == {
        "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java",
    }


def test_pilot_modes_match_plan():
    entries = {e.org_repo: e for e in loader.load_products(REPO_ROOT / "data" / "products.json")}
    assert entries["aspose-3d-foss/Aspose.3D-FOSS-for-Java"].mode == "full"
    assert entries["aspose-cells-foss/Aspose.Cells-FOSS-for-Java"].mode == "full"
    assert entries["aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"].mode == "dry_run"


def test_all_three_policy_profiles_load():
    for profile in ["aspose-3d-foss", "aspose-cells-foss", "aspose-pdf-foss"]:
        policy = loader.load_policy(profile, REPO_ROOT / "config" / "policies")
        assert policy.policy_profile == profile
        assert policy.schema_version == 2


def test_malformed_json_fails_closed(tmp_path):
    bad = tmp_path / "products.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigError):
        loader.load_products(bad)


def test_missing_file_fails_closed(tmp_path):
    with pytest.raises(ConfigError):
        loader.load_products(tmp_path / "nope.json")


def test_malformed_entry_fails_closed(tmp_path):
    bad = tmp_path / "products.json"
    bad.write_text(json.dumps([{"family": "x"}]), encoding="utf-8")
    with pytest.raises(ConfigError):
        loader.load_products(bad)


def test_is_permitted_allows_enabled_repo(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    entry = loader.is_permitted("aspose-cells-foss/Aspose.Cells-FOSS-for-Java")
    assert entry is not None
    assert entry.mode == "full"


def test_is_permitted_blocks_disabled_repo(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    assert loader.is_permitted("aspose-slides-foss/Aspose.Slides-FOSS-for-Java") is None


def test_is_permitted_blocks_unknown_repo(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    assert loader.is_permitted("some-org/not-listed") is None


def test_enabled_entries_returns_exactly_three(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    assert len(loader.enabled_entries()) == 3
