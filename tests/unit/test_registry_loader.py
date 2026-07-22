import json
from pathlib import Path

import pytest

from readme_agent.errors import ConfigError
from readme_agent.registry import loader

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_real_products_json_loads_and_has_at_least_the_known_entries():
    """Not a fixed count -- the weekly discovery workflow
    (update-products-registry.yml) and manual registry edits both grow this
    file over time (25 -> 31 entries as of 2026-07-22); a hardcoded count
    would need updating every time either one runs. Asserts a floor, not an
    exact size."""
    entries = loader.load_products(REPO_ROOT / "data" / "products.json")
    assert len(entries) >= 25


def test_enabled_entries_match_non_disabled_entries_in_the_file():
    """Registry broadened 2026-07-22 (decisions #24/PIL-011: research/dev
    scope is the full registry, not just the 3-repo write/rollout pilot) --
    more repos are now `dry_run`-enabled for read/audit coverage. Asserts
    the real invariant (enabled == every entry whose mode != "disabled")
    computed fresh from the file, rather than a specific point-in-time
    count or org_repo set, so this can't drift out of sync with the
    registry again the next time it legitimately grows."""
    raw = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    expected = {
        f"{e['repo_url'].rstrip('/').split('/')[-2]}/{e['repo_name']}"
        for e in raw
        if e["mode"] != "disabled"
    }
    entries = loader.load_products(REPO_ROOT / "data" / "products.json")
    enabled = {e.org_repo for e in entries if e.mode != "disabled"}
    assert enabled == expected
    # The original 3-repo write/rollout pilot boundary (decision #10/#24)
    # must always be a subset of whatever else is enabled around it --
    # see test_pilot_modes_match_plan for their exact modes.
    assert {
        "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java",
    } <= enabled


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
    # aspose-cells-foss/Aspose.Cells-FOSS-for-Go: confirmed `mode: "disabled"`
    # directly against the real file at the time this test was written --
    # aspose-slides-foss/Aspose.Slides-FOSS-for-Java (this test's prior
    # example) moved to `dry_run` in the 2026-07-22 registry broadening.
    assert loader.is_permitted("aspose-cells-foss/Aspose.Cells-FOSS-for-Go") is None


def test_is_permitted_blocks_unknown_repo(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    assert loader.is_permitted("some-org/not-listed") is None


def test_enabled_entries_returns_every_non_disabled_entry(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    raw = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    expected_count = sum(1 for e in raw if e["mode"] != "disabled")
    assert len(loader.enabled_entries()) == expected_count
