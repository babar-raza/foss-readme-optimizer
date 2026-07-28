"""Verify the committed Aspose link catalogs and current-registry coverage."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from readme_agent.links.catalog import (
    canonical_catalog_payload_hash,
    load_aspose_link_catalogs,
    query_linkable_targets,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_aspose_link_catalogs_are_domain_pure_checksum_valid_and_registry_scoped() -> None:
    catalogs = load_aspose_link_catalogs()

    for catalog in (catalogs.aspose_com, catalogs.aspose_org):
        raw = json.loads(
            (
                REPO_ROOT
                / (
                    "data/aspose_com_links.json"
                    if catalog.parent_domain == "aspose.com"
                    else "data/aspose_org_links.json"
                )
            ).read_text(encoding="utf-8")
        )
        assert catalog.provenance.output_hash == canonical_catalog_payload_hash(raw)
        assert catalog.provenance.total_records == len(catalog.records)
        assert catalog.provenance.verified_records == sum(
            record.http_status == 200 for record in catalog.records.values()
        )
        assert all(
            (urlparse(record.url).hostname or "").endswith(catalog.parent_domain)
            for record in catalog.records.values()
        )

    products = json.loads((REPO_ROOT / "data/products.json").read_text(encoding="utf-8"))
    uncovered = [
        (entry["family"], entry["platform"])
        for entry in products
        if entry.get("active", True)
        and not query_linkable_targets(
            catalogs,
            family=entry["family"],
            platform=entry["platform"],
        )
    ]
    assert not uncovered
