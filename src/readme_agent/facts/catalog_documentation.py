"""Derive exact product documentation links from the governed link catalog."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.registry.models import ProductEntry

_SURFACES = ("docs", "kb", "reference")
_DEFAULT_CATALOG = Path(__file__).parents[3] / "data" / "aspose_org_links.json"


def _identity_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _catalog_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog_documentation_fact(
    entry: ProductEntry,
    *,
    catalog_path: Path = _DEFAULT_CATALOG,
) -> FactRecordV2 | None:
    """Return canonical links only when exact family, platform, and product evidence agrees."""

    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    records = payload.get("records")
    if payload.get("parent_domain") != "aspose.org" or not isinstance(records, dict):
        return None
    product_key = _identity_key(entry.repo_name)
    selected: list[dict[str, object]] = []
    for surface in _SURFACES:
        matches = [
            record
            for record in records.values()
            if isinstance(record, dict)
            and record.get("surface") == surface
            and str(record.get("family", "")).casefold() == entry.family.casefold()
            and entry.platform.casefold()
            in {str(platform).casefold() for platform in record.get("platforms", [])}
            and record.get("content_evidence") == "source_body"
            and _identity_key(str(record.get("title", ""))) == product_key
            and isinstance(record.get("url"), str)
            and urlparse(str(record["url"])).scheme == "https"
        ]
        if not matches:
            continue
        record = min(
            matches,
            key=lambda item: (
                len(urlparse(str(item["url"])).path.strip("/").split("/")),
                str(item["url"]),
                str(item.get("record_id", "")),
            ),
        )
        selected.append(
            {
                "surface": surface,
                "url": record["url"],
                "title": record["title"],
                "record_id": record["record_id"],
                "family": record["family"],
                "platform": entry.platform,
                "product": entry.repo_name,
                "source_location": record["source_location"],
                "source_revision_or_hash": record["source_revision_or_hash"],
            }
        )
    if not selected:
        return None
    digest = _catalog_sha256(catalog_path)
    return FactRecordV2(
        fact_id=descriptive_fact_id("documentation.links", "governed-aspose-org-catalog"),
        field="documentation.links",
        value=selected,
        source=FactSourceV2(
            source_type="external_registry",
            location="data/aspose_org_links.json",
            source_revision=f"sha256:{digest}",
        ),
        verification_state="verified",
        authoritative_owner="documentation-catalog-owner",
        confidence=1.0,
        affected_surfaces=SURFACE_DEPENDENCIES["documentation.links"],
    )
