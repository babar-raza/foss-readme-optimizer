"""Load, checksum, normalize, and query verified Aspose link catalogs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import ValidationError

from readme_agent.errors import ConfigError
from readme_agent.links.catalog_models import (
    AsposeLinkCatalogSetV1,
    AsposeLinkCatalogV2,
    AsposeLinkRecordV2,
    AsposeLinkSurface,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASPOSE_COM_CATALOG_PATH = _PROJECT_ROOT / "data" / "aspose_com_links.json"
ASPOSE_ORG_CATALOG_PATH = _PROJECT_ROOT / "data" / "aspose_org_links.json"
_TRACKING_QUERY_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}


def canonical_catalog_payload_hash(payload: dict) -> str:
    """Hash one catalog with its output_hash field blanked."""

    hashable = json.loads(json.dumps(payload))
    hashable["provenance"]["output_hash"] = ""
    encoded = json.dumps(hashable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def normalize_target_url(url: str) -> str:
    """Normalize a target for exact catalog lookup without inventing a path."""

    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").casefold()
    scheme = parsed.scheme.casefold()
    if scheme != "https" or not hostname:
        return url.strip()
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in _TRACKING_QUERY_KEYS
        ]
    )
    path = parsed.path or "/"
    if "." not in path.rsplit("/", 1)[-1] and not path.endswith("/"):
        path += "/"
    return urlunparse(("https", hostname, path, "", query, ""))


def load_link_catalog(path: Path) -> AsposeLinkCatalogV2:
    """Load one V2 catalog and fail closed on schema or checksum disagreement."""

    if not path.is_file():
        raise ConfigError(f"link catalog not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    try:
        catalog = AsposeLinkCatalogV2.model_validate(payload)
    except ValidationError as exc:
        raise ConfigError(f"{path} is malformed: {exc}") from exc
    expected = canonical_catalog_payload_hash(payload)
    if catalog.provenance.output_hash != expected:
        raise ConfigError(
            f"{path} output_hash mismatch: expected {expected}, "
            f"found {catalog.provenance.output_hash}"
        )
    return catalog


def load_aspose_link_catalogs(
    *,
    com_path: Path = ASPOSE_COM_CATALOG_PATH,
    org_path: Path = ASPOSE_ORG_CATALOG_PATH,
) -> AsposeLinkCatalogSetV1:
    """Load the two catalogs through the sole runtime lookup seam."""

    return AsposeLinkCatalogSetV1(
        aspose_org=load_link_catalog(org_path),
        aspose_com=load_link_catalog(com_path),
    )


def lookup_verified_target(
    catalogs: AsposeLinkCatalogSetV1,
    url: str,
) -> AsposeLinkRecordV2 | None:
    """Return an exact verified record after removing tracking parameters."""

    normalized = normalize_target_url(url)
    for record in catalogs.records:
        if record.http_status == 200 and normalize_target_url(record.url) == normalized:
            return record
    return None


def query_linkable_targets(
    catalogs: AsposeLinkCatalogSetV1,
    *,
    family: str,
    platform: str,
    surfaces: set[AsposeLinkSurface] | None = None,
) -> list[AsposeLinkRecordV2]:
    """Return exact family/platform candidates in stable priority order."""

    family_key = family.casefold()
    platform_key = platform.casefold()
    surface_rank = {"docs": 0, "kb": 1, "reference": 2, "products": 3, "blog": 4}
    matches = [
        record
        for record in catalogs.records
        if record.linkable
        and record.family == family_key
        and (not record.platforms or platform_key in record.platforms)
        and (surfaces is None or record.surface in surfaces)
    ]
    return sorted(
        matches,
        key=lambda record: (
            surface_rank[record.surface],
            0 if record.platforms else 1,
            record.parent_domain != "aspose.org",
            record.title.casefold(),
            record.record_id,
        ),
    )
