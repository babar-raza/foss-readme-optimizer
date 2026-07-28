"""Shared deterministic assembly and atomic replacement for both Aspose catalogs."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from readme_agent.links.catalog import canonical_catalog_payload_hash
from readme_agent.links.catalog_models import (
    AsposeLinkCatalogV2,
    AsposeLinkRecordV2,
    AsposeParentDomain,
    LinkCatalogSourceV2,
)

GENERATOR_NAME = "scripts/data-refresh/build_aspose_link_catalogs.py"
GENERATOR_VERSION = "2.0.0"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def merge_records(records: Iterable[AsposeLinkRecordV2]) -> dict[str, AsposeLinkRecordV2]:
    """Merge exact records while rejecting duplicate IDs, URLs, or disagreement."""

    by_id: dict[str, AsposeLinkRecordV2] = {}
    by_url: dict[str, AsposeLinkRecordV2] = {}
    for record in records:
        prior_id = by_id.get(record.record_id)
        if prior_id is not None and prior_id != record:
            raise ValueError(f"catalog record ID disagreement: {record.record_id}")
        prior_url = by_url.get(record.url)
        if prior_url is not None and prior_url != record:
            raise ValueError(f"catalog URL disagreement: {record.url}")
        by_id[record.record_id] = record
        by_url[record.url] = record
    return dict(sorted(by_id.items()))


def build_catalog(
    *,
    parent_domain: AsposeParentDomain,
    records: Iterable[AsposeLinkRecordV2],
    sources: list[LinkCatalogSourceV2],
    generated_at: str | None = None,
) -> AsposeLinkCatalogV2:
    """Build and self-validate one checksum-complete V2 catalog."""

    merged = merge_records(records)
    if not merged:
        raise ValueError(f"refusing empty {parent_domain} link catalog")
    verified = sum(record.http_status == 200 for record in merged.values())
    if verified == 0:
        raise ValueError(f"refusing unverified {parent_domain} link catalog")
    payload = {
        "schema_version": "2.0",
        "parent_domain": parent_domain,
        "provenance": {
            "generated_at": generated_at or utc_now_iso(),
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
            "sources": [source.model_dump(mode="json") for source in sources],
            "total_records": len(merged),
            "verified_records": verified,
            "output_hash": "",
        },
        "records": {
            record_id: record.model_dump(mode="json") for record_id, record in merged.items()
        },
    }
    payload["provenance"]["output_hash"] = canonical_catalog_payload_hash(payload)
    return AsposeLinkCatalogV2.model_validate(payload)


def write_catalog_atomic(catalog: AsposeLinkCatalogV2, path: Path) -> None:
    """Atomically replace one catalog only after complete in-memory validation."""

    payload = catalog.model_dump(mode="json")
    if payload["provenance"]["output_hash"] != canonical_catalog_payload_hash(payload):
        raise ValueError("refusing catalog whose output hash is not self-consistent")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
