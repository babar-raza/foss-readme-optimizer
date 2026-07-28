"""Discover bounded Aspose.com targets from aspose.org's verified target map."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

from readme_agent.links.catalog_models import AsposeLinkRecordV2

_HOST_SURFACES = {
    "products.aspose.com": "products",
    "docs.aspose.com": "docs",
    "kb.aspose.com": "kb",
    "blog.aspose.com": "blog",
    "reference.aspose.com": "reference",
}
_PLATFORM_ALIASES = {
    "python-net": "python",
    "python-java": "python",
    "nodejs-net": "typescript",
    "nodejs": "typescript",
    "c-plus-plus": "cpp",
    "go-cpp": "go",
}
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.+#-]{1,63}")
_MAX_DEEP_RECORDS_PER_SCOPE_SURFACE = 20


def _record_id(surface: str, family: str, platform: str | None, url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"com:{surface}:{family}:{platform or 'all'}:{digest}"


def _title(parts: list[str]) -> str:
    slug = parts[-1] if parts else "Aspose"
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", slug) if part)


def _platform(raw: str | None) -> str | None:
    if raw is None:
        return None
    return _PLATFORM_ALIASES.get(raw, raw)


def discover_com_records(
    *,
    target_map: dict,
    source_location: Path,
    source_revision_or_hash: str,
    retrieved_at: str,
    registry_scope: set[tuple[str, str]],
    relevant_terms: dict[tuple[str, str], set[str]],
) -> list[AsposeLinkRecordV2]:
    """Keep roots plus deep targets whose slugs match source-backed API terms."""

    records: list[AsposeLinkRecordV2] = []
    deep_candidates: dict[
        tuple[str, str | None, str],
        list[tuple[int, AsposeLinkRecordV2]],
    ] = {}
    families = {family for family, _ in registry_scope}
    for url, raw in sorted(target_map.get("all_urls", {}).items()):
        if raw.get("http_status") != 200:
            continue
        parsed = urlparse(url)
        surface = _HOST_SURFACES.get((parsed.hostname or "").casefold())
        if surface is None:
            continue
        parts = [part.casefold() for part in parsed.path.strip("/").split("/") if part]
        if not parts or parts[0] not in families:
            continue
        family = parts[0]
        platform = _platform(raw.get("platform") or (parts[1] if len(parts) >= 2 else None))
        exact_scopes = (
            {(family, platform)}
            if platform is not None
            else {item for item in registry_scope if item[0] == family}
        )
        if not exact_scopes & registry_scope:
            continue
        depth = len(parts)
        landing = surface == "products" and depth <= 2
        if depth > 2 and not landing:
            slug_terms = {token.casefold() for token in _TOKEN.findall(" ".join(parts[2:]))}
            allowed_terms = set().union(
                *(relevant_terms.get(scope, set()) for scope in exact_scopes)
            )
            if not slug_terms & allowed_terms:
                continue
        title = _title(parts)
        normalized_url = url if url.endswith("/") else url + "/"
        record = AsposeLinkRecordV2(
            record_id=_record_id(surface, family, platform, normalized_url),
            parent_domain="aspose.com",
            surface=surface,
            url=normalized_url,
            title=title,
            family=family,
            platforms=[platform] if platform else [],
            subject_terms=sorted({token.casefold() for token in _TOKEN.findall(" ".join(parts))})[
                :96
            ],
            content_evidence="landing" if landing else "slug_only",
            source_type="source_db",
            source_location=source_location.as_posix(),
            source_revision_or_hash=source_revision_or_hash,
            retrieved_at=retrieved_at,
            http_status=200,
            verified_at=retrieved_at,
            http_verification_source="source_db",
            http_verification_evidence=source_revision_or_hash,
        )
        if depth <= 2 or landing:
            records.append(record)
            continue
        overlap = len(set(record.subject_terms) & allowed_terms)
        deep_candidates.setdefault((family, platform, surface), []).append((overlap, record))
    for candidates in deep_candidates.values():
        ranked = sorted(
            candidates,
            key=lambda item: (-item[0], len(item[1].url), item[1].url),
        )
        records.extend(record for _, record in ranked[:_MAX_DEEP_RECORDS_PER_SCOPE_SURFACE])
    return records
