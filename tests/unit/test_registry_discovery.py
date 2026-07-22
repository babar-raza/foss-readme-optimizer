import json
from pathlib import Path

import pytest

from readme_agent.registry import discovery as registry_sync
from readme_agent.registry.models import ProductEntry

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("repo_name", "expected"),
    [
        ("Aspose.3D-FOSS-for-Java", ("3d", "java")),
        ("Aspose.3D-FOSS-for-.NET", ("3d", "net")),
        ("Aspose.Cells-FOSS-for-TypeScript", ("cells", "typescript")),
        ("Aspose.Email-FOSS-for-.Net", ("email", "net")),
        ("aspose-pdf-foss-for-go", ("pdf", "go")),
        ("Aspose-PDF-FOSS-for-Go", ("pdf", "go")),
        ("some-unrelated-repo", None),
        ("Aspose.Cells", None),
    ],
)
def test_classify_repo_name(repo_name, expected):
    assert registry_sync.classify_repo_name(repo_name) == expected


def test_real_families_json_has_26_entries_with_matching_org_convention():
    families = registry_sync.load_families(REPO_ROOT / "data" / "families.json")
    assert len(families) == 26
    for fam in families:
        assert fam["github_org"] == f"aspose-{fam['family']}-foss"


def test_real_families_json_covers_every_org_referenced_by_products_json():
    families = registry_sync.load_families(REPO_ROOT / "data" / "families.json")
    known_orgs = {f["github_org"] for f in families}
    products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    for entry in products:
        org = entry["repo_url"].split("/")[3]
        assert org in known_orgs, f"{org!r} (from {entry['repo_name']}) missing from families.json"


def test_merge_new_entry_defaults_to_disabled():
    discovered = [
        {
            "family": "3d",
            "platform": "rust",
            "repo_name": "Aspose.3D-FOSS-for-Rust",
            "repo_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Rust",
            "clone_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Rust.git",
            "active": True,
            "discovered_via": "github",
        }
    ]
    merged = registry_sync.merge([], discovered)
    assert len(merged) == 1
    assert merged[0]["mode"] == "disabled"
    assert merged[0]["ecosystem"] is None
    assert merged[0]["policy_profile"] is None


def test_merge_preserves_owned_fields_on_existing_entry():
    existing = [
        {
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
    ]
    discovered = [
        {
            "family": "cells",
            "platform": "java",
            "repo_name": "Aspose.Cells-FOSS-for-Java",
            "repo_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
            "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.git",
            "active": False,  # e.g. GitHub now reports it archived
            "discovered_via": "github",
        }
    ]
    merged = registry_sync.merge(existing, discovered)
    assert len(merged) == 1
    entry = merged[0]
    assert entry["mode"] == "full"
    assert entry["ecosystem"] == "maven"
    assert entry["policy_profile"] == "aspose-cells-foss"
    assert entry["active"] is False  # upstream-shaped field does refresh


def test_merge_never_deletes_entries_missing_from_discovery():
    existing = [
        {
            "family": "slides",
            "platform": "java",
            "repo_name": "Aspose.Slides-FOSS-for-Java",
            "repo_url": "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
            "clone_url": "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java.git",
            "active": True,
            "discovered_via": "github",
            "mode": "disabled",
            "ecosystem": None,
            "policy_profile": None,
        }
    ]
    merged = registry_sync.merge(existing, [])
    assert merged == existing


def test_merged_entries_validate_against_the_loader_schema():
    existing = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    discovered = [
        {
            "family": "3d",
            "platform": "rust",
            "repo_name": "Aspose.3D-FOSS-for-Rust",
            "repo_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Rust",
            "clone_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Rust.git",
            "active": True,
            "discovered_via": "github",
        }
    ]
    merged = registry_sync.merge(existing, discovered)
    for entry in merged:
        ProductEntry.model_validate(entry)  # raises on schema violation


def test_write_atomic_writes_sorted_valid_json(tmp_path):
    path = tmp_path / "products.json"
    data = [
        {"family": "pdf", "platform": "java"},
        {"family": "3d", "platform": "java"},
    ]
    registry_sync.write_atomic(path, data)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == data
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_merge_is_deterministically_sorted():
    existing = [
        {
            "family": "words",
            "platform": "python",
            "repo_name": "x",
            "repo_url": "https://github.com/aspose-words-foss/x",
            "clone_url": "https://github.com/aspose-words-foss/x.git",
            "active": True,
            "discovered_via": "github",
            "mode": "disabled",
            "ecosystem": None,
            "policy_profile": None,
        },
        {
            "family": "3d",
            "platform": "java",
            "repo_name": "y",
            "repo_url": "https://github.com/aspose-3d-foss/y",
            "clone_url": "https://github.com/aspose-3d-foss/y.git",
            "active": True,
            "discovered_via": "github",
            "mode": "disabled",
            "ecosystem": None,
            "policy_profile": None,
        },
    ]
    merged = registry_sync.merge(existing, [])
    assert [(e["family"], e["platform"]) for e in merged] == [("3d", "java"), ("words", "python")]


class _FakeResponse:
    def __init__(self, headers):
        self.headers = headers


class TestRateLimitWaitSeconds:
    def test_secondary_rate_limit_uses_retry_after(self):
        # Secondary/abuse-detection limit can fire with core quota still remaining --
        # Retry-After (relative seconds) must win over X-RateLimit-Reset when both are absent
        # or misleading.
        resp = _FakeResponse({"Retry-After": "30"})
        assert registry_sync._rate_limit_wait_seconds(resp) == 32

    def test_primary_rate_limit_falls_back_to_reset_epoch(self):
        import time

        resp = _FakeResponse({"X-RateLimit-Reset": str(int(time.time()) + 10)})
        wait = registry_sync._rate_limit_wait_seconds(resp)
        assert 10 <= wait <= 13

    def test_no_headers_defaults_to_about_a_minute(self):
        resp = _FakeResponse({})
        wait = registry_sync._rate_limit_wait_seconds(resp)
        assert 55 <= wait <= 63


class _Fake403Response:
    status_code = 403

    def __init__(self, headers):
        self.headers = headers


def test_paginate_raises_instead_of_sleeping_beyond_max_rate_limit_wait(monkeypatch):
    # The runtime self-heal's fail-open promise depends on this: a 403 asking for
    # a wait over the caller's cap must surface as an exception the heal can turn
    # into a visible skip, never a silent multi-minute sleep inside supervise.
    monkeypatch.setattr(
        registry_sync.requests, "get", lambda *a, **k: _Fake403Response({"Retry-After": "300"})
    )
    monkeypatch.setattr(
        registry_sync.time, "sleep", lambda s: pytest.fail(f"slept {s}s instead of raising")
    )
    with pytest.raises(registry_sync.RegistryScanRateLimited) as excinfo:
        list(
            registry_sync._paginate(
                "https://api.github.com/orgs/x/repos", {}, None, max_rate_limit_wait_seconds=60
            )
        )
    assert excinfo.value.wait_seconds == 302
    assert excinfo.value.max_wait_seconds == 60


def test_discover_returns_org_failures_instead_of_dropping_them(monkeypatch):
    def fake_scan_org(org, *, token=None, max_rate_limit_wait_seconds=None):
        if org == "aspose-broken-foss":
            raise RuntimeError("boom")
        return [
            {
                "name": "Aspose.3D-FOSS-for-Java",
                "html_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java",
                "clone_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java.git",
                "archived": False,
            }
        ]

    monkeypatch.setattr(registry_sync, "scan_org", fake_scan_org)
    families = [{"github_org": "aspose-broken-foss"}, {"github_org": "aspose-3d-foss"}]
    discovered, org_failures = registry_sync.discover(families)
    assert [(e["family"], e["platform"]) for e in discovered] == [("3d", "java")]
    assert org_failures == [{"org": "aspose-broken-foss", "error": "boom"}]
