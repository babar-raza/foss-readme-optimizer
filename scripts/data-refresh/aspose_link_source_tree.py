"""Discover article-level Aspose.org targets from the sibling source tree."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from readme_agent.links.catalog_models import AsposeLinkRecordV2, HttpVerificationSource

StatusEvidence = tuple[
    int,
    str | None,
    HttpVerificationSource | None,
    str | None,
]

_SURFACE_ROOTS = {
    "products": Path("content/products.aspose.org/en"),
    "docs": Path("content/docs.aspose.org/en"),
    "kb": Path("content/kb.aspose.org/en"),
    "reference": Path("content/reference.aspose.org/en"),
}
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.+#-]{1,63}")
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _front_matter(text: str) -> dict[str, Any]:
    match = _FRONT_MATTER.match(text)
    if match is None:
        return {}
    loaded = yaml.safe_load(match.group(1))
    return loaded if isinstance(loaded, dict) else {}


def _title(metadata: dict[str, Any], path: Path) -> str:
    for key in ("title", "linkTitle"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    stem = path.parent.name if path.name == "index.md" else path.stem
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", stem) if part)


def _subject_terms(metadata: dict[str, Any], title: str) -> list[str]:
    terms: set[str] = {token.casefold() for token in _TOKEN.findall(title)}
    description = metadata.get("description")
    if isinstance(description, str):
        terms.update(token.casefold() for token in _TOKEN.findall(description))
    evidence = metadata.get("evidence")
    if isinstance(evidence, dict):
        for api in evidence.get("apis", []):
            if isinstance(api, str):
                terms.add(api.casefold())
                terms.update(token.casefold() for token in _TOKEN.findall(api))
        for format_record in evidence.get("formats", []):
            if isinstance(format_record, dict) and isinstance(format_record.get("ext"), str):
                terms.add(format_record["ext"].casefold())
    return sorted(terms)[:96]


def _has_body_evidence(metadata: dict[str, Any]) -> bool:
    evidence = metadata.get("evidence")
    if not isinstance(evidence, dict) or not evidence.get("model_sha"):
        return False
    return any(evidence.get(key) for key in ("apis", "formats", "claims"))


def _record_id(surface: str, family: str, platform: str | None, url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"org:{surface}:{family}:{platform or 'all'}:{digest}"


def _public_url(surface: str, relative: Path) -> str:
    parts = list(relative.parts)
    filename = parts.pop()
    if filename not in {"_index.md", "index.md"}:
        parts.append(Path(filename).stem)
    elif filename == "index.md" and parts:
        pass
    path = "/".join(part.casefold() for part in parts)
    return f"https://{surface}.aspose.org/{path}/"


def _source_record(
    *,
    source_root: Path,
    source_revision: str,
    retrieved_at: str,
    surface: str,
    relative: Path,
    family: str,
    platform: str | None,
    status_by_url: dict[str, StatusEvidence],
) -> AsposeLinkRecordV2:
    surface_root = (
        _SURFACE_ROOTS[surface] if surface in _SURFACE_ROOTS else Path("content/blog.aspose.org")
    )
    path = source_root / surface_root / relative
    text = path.read_text(encoding="utf-8")
    metadata = _front_matter(text)
    url = _public_url(surface, relative)
    status, verified_at, verification_source, verification_evidence = status_by_url.get(
        url,
        (-1, None, None, None),
    )
    landing = path.name == "_index.md" and len(relative.parts) <= 3
    return AsposeLinkRecordV2(
        record_id=_record_id(surface, family, platform, url),
        parent_domain="aspose.org",
        surface=surface,
        url=url,
        title=_title(metadata, path),
        family=family,
        platforms=[platform] if platform else [],
        subject_terms=_subject_terms(metadata, _title(metadata, path)),
        content_evidence="landing"
        if surface == "products" and landing
        else ("source_body" if _has_body_evidence(metadata) else "slug_only"),
        source_type="source_tree",
        source_location=path.relative_to(source_root).as_posix(),
        source_revision_or_hash=source_revision,
        retrieved_at=retrieved_at,
        http_status=status,
        verified_at=verified_at,
        http_verification_source=verification_source,
        http_verification_evidence=verification_evidence,
    )


def discover_org_records(
    *,
    source_root: Path,
    source_revision: str,
    retrieved_at: str,
    registry_scope: set[tuple[str, str]],
    status_by_url: dict[str, StatusEvidence],
) -> list[AsposeLinkRecordV2]:
    """Discover current-registry English pages without treating existence as HTTP proof."""

    records: list[AsposeLinkRecordV2] = []
    families = {family for family, _ in registry_scope}
    for surface, relative_root in _SURFACE_ROOTS.items():
        root = source_root / relative_root
        for path in sorted(root.rglob("*.md")):
            relative = path.relative_to(root)
            directory_parts = relative.parent.parts
            if not directory_parts or directory_parts[0] not in families:
                continue
            family = directory_parts[0]
            platform = directory_parts[1] if len(directory_parts) >= 2 else None
            if platform is not None and (family, platform) not in registry_scope:
                continue
            records.append(
                _source_record(
                    source_root=source_root,
                    source_revision=source_revision,
                    retrieved_at=retrieved_at,
                    surface=surface,
                    relative=relative,
                    family=family,
                    platform=platform,
                    status_by_url=status_by_url,
                )
            )
    blog_root = source_root / "content/blog.aspose.org"
    for path in sorted(blog_root.glob("*/*/*/index.md")):
        relative = path.relative_to(blog_root)
        family, platform = relative.parts[:2]
        if (family, platform) not in registry_scope:
            continue
        records.append(
            _source_record(
                source_root=source_root,
                source_revision=source_revision,
                retrieved_at=retrieved_at,
                surface="blog",
                relative=relative,
                family=family,
                platform=platform,
                status_by_url=status_by_url,
            )
        )
    return records
