"""CORE-034 (decision #47): the supervise-time registry drift self-heal.

Everything here is offline: GitHub scanning is monkeypatched at the
`discovery` module seam, registry files live in tmp_path, and the runs/
directory is redirected via README_AGENT_RUNS_DIR -- same conventions as the
rest of the unit tier.
"""

import json
import time

import pytest

from readme_agent.registry import discovery, self_heal

_CELLS_JAVA_ENABLED = {
    "family": "cells",
    "platform": "java",
    "repo_name": "Aspose.Cells-FOSS-for-Java",
    "repo_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.git",
    "active": True,
    "discovered_via": "github",
    "mode": "full",
    "ecosystem": "maven",
    "policy_profile": "aspose-cells-foss",
}

_CELLS_JAVA_UPSTREAM = {
    "name": "Aspose.Cells-FOSS-for-Java",
    "html_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.git",
    "archived": False,
}

_CELLS_NET_UPSTREAM = {
    "name": "Aspose.Cells-FOSS-for-.NET",
    "html_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET.git",
    "archived": False,
}


@pytest.fixture(autouse=True)
def _isolated_runs_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    return tmp_path / "runs"


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "test-token")


@pytest.fixture
def registry_files(tmp_path):
    families_path = tmp_path / "families.json"
    families_path.write_text(
        json.dumps([{"family": "cells", "name": "Aspose.Cells", "github_org": "aspose-cells-foss"}])
        + "\n",
        encoding="utf-8",
    )
    products_path = tmp_path / "products.json"
    products_path.write_text(json.dumps([_CELLS_JAVA_ENABLED], indent=2) + "\n", encoding="utf-8")
    return products_path, families_path


def _heal(products_path, families_path, **kwargs):
    return self_heal.heal_registry_drift(
        products_path=products_path, families_path=families_path, **kwargs
    )


def _evidence_files(runs_dir, name):
    evidence_root = runs_dir / "evidence"
    return sorted(evidence_root.glob(f"*/{name}")) if evidence_root.is_dir() else []


def test_heal_inserts_new_entry_disabled_and_never_touches_owned_fields(
    monkeypatch, registry_files
):
    products_path, families_path = registry_files
    monkeypatch.setattr(
        discovery,
        "scan_org",
        lambda org, **kw: [_CELLS_JAVA_UPSTREAM, _CELLS_NET_UPSTREAM],
    )

    result = _heal(products_path, families_path)

    assert result.status == "HEALED"
    assert [(e["family"], e["platform"]) for e in result.new_entries] == [("cells", "net")]
    written = json.loads(products_path.read_text(encoding="utf-8"))
    assert len(written) == 2
    by_key = {(e["family"], e["platform"]): e for e in written}
    # The pre-existing enabled entry keeps every agent-owned field verbatim.
    assert by_key[("cells", "java")] == _CELLS_JAVA_ENABLED
    # The healed entry lands read-only-eligible, never operable.
    new_entry = by_key[("cells", "net")]
    assert new_entry["mode"] == "disabled"
    assert new_entry["ecosystem"] is None
    assert new_entry["policy_profile"] is None
    # A real attempt writes the TTL marker.
    assert self_heal.paths.registry_heal_marker_path().is_file()


def test_heal_is_fail_open_when_scan_raises(monkeypatch, registry_files, _isolated_runs_dir):
    products_path, families_path = registry_files
    before = products_path.read_bytes()

    def _boom(families, **kw):
        raise RuntimeError("github exploded")

    monkeypatch.setattr(discovery, "discover", _boom)

    result = _heal(products_path, families_path)

    assert result.status == "SKIPPED_ERROR"
    assert "github exploded" in result.detail
    assert products_path.read_bytes() == before
    evidence = _evidence_files(_isolated_runs_dir, "registry_heal.json")
    assert len(evidence) == 1
    assert json.loads(evidence[0].read_text(encoding="utf-8"))["status"] == "SKIPPED_ERROR"


def test_heal_skips_without_token_and_never_calls_the_network(monkeypatch, registry_files):
    products_path, families_path = registry_files
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PAT", raising=False)
    monkeypatch.setattr(
        discovery, "scan_org", lambda org, **kw: pytest.fail("scan_org must not be called")
    )

    result = _heal(products_path, families_path)

    assert result.status == "SKIPPED_NO_TOKEN"


def test_heal_ttl_guard_skips_within_interval(monkeypatch, registry_files):
    products_path, families_path = registry_files
    marker = self_heal.paths.registry_heal_marker_path()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({"last_heal_epoch": time.time(), "last_status": "NO_DRIFT"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        discovery, "scan_org", lambda org, **kw: pytest.fail("scan_org must not be called")
    )

    result = _heal(products_path, families_path)

    assert result.status == "SKIPPED_RECENT"


def test_heal_no_drift_does_not_rewrite_the_file(monkeypatch, registry_files):
    products_path, families_path = registry_files
    before = products_path.read_bytes()
    monkeypatch.setattr(discovery, "scan_org", lambda org, **kw: [_CELLS_JAVA_UPSTREAM])

    result = _heal(products_path, families_path)

    assert result.status == "NO_DRIFT"
    assert products_path.read_bytes() == before


def test_heal_writes_registry_heal_evidence(monkeypatch, registry_files, _isolated_runs_dir):
    products_path, families_path = registry_files
    monkeypatch.setattr(
        discovery,
        "scan_org",
        lambda org, **kw: [_CELLS_JAVA_UPSTREAM, _CELLS_NET_UPSTREAM],
    )

    result = _heal(products_path, families_path)

    assert result.status == "HEALED"
    assert result.run_id is not None
    evidence = _evidence_files(_isolated_runs_dir, "registry_heal.json")
    assert len(evidence) == 1
    payload = json.loads(evidence[0].read_text(encoding="utf-8"))
    assert payload["status"] == "HEALED"
    assert payload["orgs_scanned"] == ["aspose-cells-foss"]
    assert payload["org_failures"] == []
    assert [e["repo_name"] for e in payload["new_entries"]] == ["Aspose.Cells-FOSS-for-.NET"]
    manifest = _evidence_files(_isolated_runs_dir, "manifest.json")
    assert len(manifest) == 1
    assert json.loads(manifest[0].read_text(encoding="utf-8"))["kind"] == "registry_heal"


def test_heal_org_failures_are_recorded_not_fatal(monkeypatch, registry_files):
    """One unreachable org degrades that org only -- discovery's own isolation,
    surfaced through the heal result instead of a lost stderr line."""
    products_path, families_path = registry_files
    families_path.write_text(
        json.dumps(
            [
                {"family": "cells", "name": "Aspose.Cells", "github_org": "aspose-cells-foss"},
                {"family": "words", "name": "Aspose.Words", "github_org": "aspose-words-foss"},
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def _scan(org, **kw):
        if org == "aspose-words-foss":
            raise RuntimeError("504 from GitHub")
        return [_CELLS_JAVA_UPSTREAM]

    monkeypatch.setattr(discovery, "scan_org", _scan)

    result = _heal(products_path, families_path)

    assert result.status == "NO_DRIFT"
    assert result.org_failures == [{"org": "aspose-words-foss", "error": "504 from GitHub"}]


def test_heal_never_bootstraps_a_missing_products_file(tmp_path, monkeypatch, registry_files):
    _, families_path = registry_files
    missing = tmp_path / "nowhere" / "products.json"
    monkeypatch.setattr(
        discovery, "scan_org", lambda org, **kw: pytest.fail("scan_org must not be called")
    )

    result = _heal(missing, families_path)

    assert result.status == "SKIPPED_ERROR"
    assert "not found" in result.detail
    assert not missing.exists()
