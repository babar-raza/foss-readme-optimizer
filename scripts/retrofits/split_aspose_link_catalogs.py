"""Split verified aspose.org records out of the legacy combined link catalog.

The 2026-07-22 policy-profile retrofit added a live-probed ``products.aspose.org``
surface to ``data/aspose_com_links.json``. This migration preserves that surface and
its verification provenance in ``data/aspose_org_links.json`` before removing it from
the .com catalog. It is idempotent and refuses conflicting or incomplete state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
COM_PATH = REPO_ROOT / "data" / "aspose_com_links.json"
ORG_PATH = REPO_ROOT / "data" / "aspose_org_links.json"
ORG_SURFACE = "products.aspose.org"
GENERATOR = "scripts/retrofits/split_aspose_link_catalogs.py"


def _output_hash(payload: dict) -> str:
    hashable = copy.deepcopy(payload)
    hashable["provenance"]["output_hash"] = ""
    encoded = json.dumps(hashable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _file_hash(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _write_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _link_count(payload: dict) -> int:
    surface_count = sum(
        len(surface.get("families", {})) + len(surface.get("platforms", {}))
        for surface in payload.get("surfaces", {}).values()
    )
    return surface_count + len(payload.get("blog", {}).get("categories", {}))


def _assert_domain_pure(payload: dict, parent_domain: str) -> None:
    suffix = f".{parent_domain}"
    for surface_name, surface in payload.get("surfaces", {}).items():
        if surface_name != parent_domain and not surface_name.endswith(suffix):
            raise ValueError(f"cross-domain surface in {parent_domain} catalog: {surface_name}")
        for bucket_name in ("families", "platforms"):
            for key, record in surface.get(bucket_name, {}).items():
                hostname = (urlparse(record["url"]).hostname or "").lower()
                if hostname != parent_domain and not hostname.endswith(suffix):
                    raise ValueError(
                        f"cross-domain URL in {parent_domain} catalog: {bucket_name}/{key}"
                    )
                if record.get("http_status") != 200:
                    raise ValueError(
                        f"unverified URL in {parent_domain} catalog: {bucket_name}/{key}"
                    )


def _build_org_catalog(surface: dict, source_file_hash: str) -> dict:
    source_provenance = copy.deepcopy(surface.get("provenance", {}))
    cleaned_surface = {
        "families": copy.deepcopy(surface.get("families", {})),
        "platforms": copy.deepcopy(surface.get("platforms", {})),
    }
    payload = {
        "schema_version": "1.0",
        "provenance": {
            "generated_at": datetime.now(UTC).isoformat(),
            "generator": GENERATOR,
            "generator_version": "1.0.0",
            "mode": "lossless-catalog-split",
            "sources": [
                {
                    "type": "verified-catalog-surface",
                    "path": "data/aspose_com_links.json",
                    "source_file_hash": source_file_hash,
                    "source_verification": source_provenance,
                }
            ],
            "total_links": 0,
            "output_hash": "",
        },
        "surfaces": {ORG_SURFACE: cleaned_surface},
    }
    payload["provenance"]["total_links"] = _link_count(payload)
    payload["provenance"]["output_hash"] = _output_hash(payload)
    return payload


def _validate_existing_org_catalog(payload: dict, expected_surface: dict | None) -> None:
    _assert_domain_pure(payload, "aspose.org")
    if payload["provenance"].get("total_links") != _link_count(payload):
        raise ValueError("aspose.org catalog total_links does not match its contents")
    if payload["provenance"].get("output_hash") != _output_hash(payload):
        raise ValueError("aspose.org catalog output_hash is invalid")
    if expected_surface is not None:
        actual = payload["surfaces"].get(ORG_SURFACE)
        expected = {
            "families": expected_surface.get("families", {}),
            "platforms": expected_surface.get("platforms", {}),
        }
        if actual != expected:
            raise ValueError("existing aspose.org catalog conflicts with the legacy surface")


def main() -> int:
    combined = json.loads(COM_PATH.read_text(encoding="utf-8"))
    legacy_surface = combined.get("surfaces", {}).get(ORG_SURFACE)

    if ORG_PATH.exists():
        org_catalog = json.loads(ORG_PATH.read_text(encoding="utf-8"))
        _validate_existing_org_catalog(org_catalog, legacy_surface)
    elif legacy_surface is None:
        raise ValueError("neither a legacy .org surface nor a split .org catalog exists")
    else:
        org_catalog = _build_org_catalog(legacy_surface, _file_hash(COM_PATH))
        _assert_domain_pure(org_catalog, "aspose.org")
        _write_atomic(ORG_PATH, org_catalog)

    if legacy_surface is None:
        _assert_domain_pure(combined, "aspose.com")
        print("Aspose link catalogs are already split and valid.")
        return 0

    del combined["surfaces"][ORG_SURFACE]
    combined["provenance"]["total_links"] = _link_count(combined)
    combined["provenance"]["catalog_split_at"] = datetime.now(UTC).isoformat()
    combined["provenance"]["catalog_split_generator"] = GENERATOR
    combined["provenance"]["output_hash"] = _output_hash(combined)
    _assert_domain_pure(combined, "aspose.com")
    _write_atomic(COM_PATH, combined)

    print(
        "Split Aspose link catalogs:",
        f"com={combined['provenance']['total_links']}",
        f"org={org_catalog['provenance']['total_links']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
