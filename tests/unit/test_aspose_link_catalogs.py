"""Verify that Aspose link catalogs remain domain-pure and checksum-valid."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / "data" / name).read_text(encoding="utf-8"))


def _count(payload: dict) -> int:
    surfaces = sum(
        len(surface.get("families", {})) + len(surface.get("platforms", {}))
        for surface in payload["surfaces"].values()
    )
    return surfaces + len(payload.get("blog", {}).get("categories", {}))


def _hash(payload: dict) -> str:
    hashable = copy.deepcopy(payload)
    hashable["provenance"]["output_hash"] = ""
    encoded = json.dumps(hashable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _assert_domain(payload: dict, parent_domain: str) -> None:
    suffix = f".{parent_domain}"
    for surface_name, surface in payload["surfaces"].items():
        assert surface_name == parent_domain or surface_name.endswith(suffix)
        for bucket in ("families", "platforms"):
            for record in surface.get(bucket, {}).values():
                hostname = (urlparse(record["url"]).hostname or "").lower()
                assert hostname == parent_domain or hostname.endswith(suffix)
                assert record["http_status"] == 200


def test_aspose_link_catalogs_are_separate_complete_and_checksum_valid() -> None:
    com = _load("aspose_com_links.json")
    org = _load("aspose_org_links.json")

    _assert_domain(com, "aspose.com")
    _assert_domain(org, "aspose.org")

    assert "products.aspose.org" not in com["surfaces"]
    assert "products.aspose.org" in org["surfaces"]
    assert com["provenance"]["total_links"] == _count(com)
    assert org["provenance"]["total_links"] == _count(org)
    assert com["provenance"]["output_hash"] == _hash(com)
    assert org["provenance"]["output_hash"] == _hash(org)
