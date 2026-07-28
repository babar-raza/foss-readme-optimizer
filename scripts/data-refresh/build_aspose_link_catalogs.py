#!/usr/bin/env python3
"""Build the domain-pure Aspose.com and Aspose.org link catalogs together."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests
from aspose_link_catalog_core import build_catalog, write_catalog_atomic
from aspose_link_source_db import discover_com_records
from aspose_link_source_tree import discover_org_records

from readme_agent.links.catalog_models import (
    AsposeLinkCatalogV2,
    AsposeLinkRecordV2,
    HttpVerificationSource,
    LinkCatalogSourceV2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASPOSE_ORG_ROOT = Path(r"D:\onedrive\Documents\GitHub\aspose.org")
DEFAULT_COM_OUTPUT = REPO_ROOT / "data/aspose_com_links.json"
DEFAULT_ORG_OUTPUT = REPO_ROOT / "data/aspose_org_links.json"
DEFAULT_PRODUCTS = REPO_ROOT / "data/products.json"


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _git_value(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _registry_scope(products_path: Path) -> set[tuple[str, str]]:
    payload = json.loads(products_path.read_text(encoding="utf-8"))
    return {
        (str(entry["family"]).casefold(), str(entry["platform"]).casefold())
        for entry in payload
        if entry.get("active", True)
    }


def _legacy_statuses(
    path: Path,
) -> dict[
    str,
    tuple[int, str | None, HttpVerificationSource | None, str | None],
]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    catalog_hash = _sha256(path)
    verified_at = payload.get("provenance", {}).get("generated_at")
    statuses: dict[
        str,
        tuple[int, str | None, HttpVerificationSource | None, str | None],
    ] = {}
    if payload.get("schema_version") == "2.0":
        for record in payload.get("records", {}).values():
            status = int(record["http_status"])
            statuses[record["url"]] = (
                status,
                record.get("verified_at"),
                (
                    record.get("http_verification_source") or "prior_catalog"
                    if status == 200
                    else None
                ),
                (
                    record.get("http_verification_evidence") or catalog_hash
                    if status == 200
                    else None
                ),
            )
        return statuses
    for surface in payload.get("surfaces", {}).values():
        for bucket in ("families", "platforms"):
            for record in surface.get(bucket, {}).values():
                status = int(record.get("http_status", -1))
                statuses[record["url"]] = (
                    status,
                    verified_at if status == 200 else None,
                    "prior_catalog" if status == 200 else None,
                    catalog_hash if status == 200 else None,
                )
    for record in payload.get("blog", {}).get("categories", {}).values():
        status = int(record.get("http_status", -1))
        statuses[record["url"]] = (
            status,
            verified_at if status == 200 else None,
            "prior_catalog" if status == 200 else None,
            catalog_hash if status == 200 else None,
        )
    return statuses


def _legacy_landing_records(
    path: Path,
    *,
    parent_domain: str,
) -> list[AsposeLinkRecordV2]:
    """Migrate verified V1 roots that source-tree discovery cannot rediscover."""

    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") == "2.0":
        catalog_hash = _sha256(path)
        return [
            AsposeLinkRecordV2.model_validate(
                {
                    **record,
                    "http_verification_source": (
                        record.get("http_verification_source") or "prior_catalog"
                    ),
                    "http_verification_evidence": (
                        record.get("http_verification_evidence") or catalog_hash
                    ),
                }
            )
            for record in payload.get("records", {}).values()
            if record.get("surface") == "products"
            and record.get("http_status") == 200
            and record.get("content_evidence") == "landing"
        ]
    verified_at = payload.get("provenance", {}).get("generated_at")
    source_hash = _sha256(path)
    records: list[AsposeLinkRecordV2] = []
    for hostname, surface in payload.get("surfaces", {}).items():
        if hostname != f"products.{parent_domain}":
            continue
        for bucket in ("families", "platforms"):
            for key, raw in surface.get(bucket, {}).items():
                if raw.get("http_status") != 200:
                    continue
                family, _, platform = key.partition("/")
                url = raw["url"]
                digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
                prefix = "org" if parent_domain == "aspose.org" else "com"
                title_parts = [family, platform] if platform else [family]
                records.append(
                    AsposeLinkRecordV2(
                        record_id=(f"{prefix}:products:{family}:{platform or 'all'}:{digest}"),
                        parent_domain=parent_domain,
                        surface="products",
                        url=url,
                        title="Aspose " + " ".join(part.title() for part in title_parts),
                        family=family,
                        platforms=[platform] if platform else [],
                        subject_terms=sorted(
                            {
                                token.casefold()
                                for token in re.findall(r"[A-Za-z0-9.+#-]+", " ".join(title_parts))
                            }
                        ),
                        content_evidence="landing",
                        source_type="live_probe",
                        source_location=_display_path(path),
                        source_revision_or_hash=source_hash,
                        retrieved_at=verified_at,
                        http_status=200,
                        verified_at=verified_at,
                        http_verification_source="prior_catalog",
                        http_verification_evidence=source_hash,
                    )
                )
    return records


def _probe(url: str) -> int:
    session = requests.Session()
    session.headers["User-Agent"] = "foss-readme-optimizer-link-catalog/2.0"
    try:
        response = session.head(url, allow_redirects=True, timeout=20)
        if response.status_code not in {403, 405}:
            return response.status_code
    except requests.RequestException:
        pass
    try:
        response = session.get(url, allow_redirects=True, timeout=30, stream=True)
        response.close()
        return response.status_code
    except requests.RequestException:
        return 0


def _apply_live_patterns(
    records: list[AsposeLinkRecordV2],
    patterns: list[str],
    *,
    verified_at: str,
) -> list[AsposeLinkRecordV2]:
    if not patterns:
        return records
    matched = {pattern: 0 for pattern in patterns}
    output: list[AsposeLinkRecordV2] = []
    for record in records:
        selected = [pattern for pattern in patterns if pattern.casefold() in record.url.casefold()]
        if not selected:
            output.append(record)
            continue
        for pattern in selected:
            matched[pattern] += 1
        status = _probe(record.url)
        output.append(
            record.model_copy(
                update={
                    "http_status": status,
                    "verified_at": verified_at if status == 200 else None,
                    "http_verification_source": "live_probe" if status == 200 else None,
                    "http_verification_evidence": (
                        f"HEAD_OR_GET:{record.url}" if status == 200 else None
                    ),
                }
            )
        )
    missing = [pattern for pattern, count in matched.items() if count == 0]
    if missing:
        raise ValueError(f"live verification patterns matched no discovered record: {missing}")
    return output


def _relevant_terms(
    records: list[AsposeLinkRecordV2],
) -> dict[tuple[str, str], set[str]]:
    terms: dict[tuple[str, str], set[str]] = {}
    for record in records:
        for platform in record.platforms:
            terms.setdefault((record.family, platform), set()).update(record.subject_terms)
    return terms


def _source_generated_at(target_map: dict) -> str:
    value = target_map.get("provenance", {}).get("generated_at")
    if not isinstance(value, str) or not value:
        raise ValueError("Aspose.com target map lacks provenance.generated_at")
    return value


def _latest_catalog_time(
    records: list[AsposeLinkRecordV2],
    source_time: str,
) -> str:
    """Keep output stable after live verification by retaining its latest proof time."""

    return max(
        [source_time, *(record.verified_at for record in records if record.verified_at)],
    )


def _live_probe_source(
    records: list[AsposeLinkRecordV2],
) -> LinkCatalogSourceV2 | None:
    verified_records = [
        record for record in records if record.http_verification_source == "live_probe"
    ]
    if not verified_records:
        return None
    verified = sorted((record.url, record.http_status) for record in verified_records)
    digest = hashlib.sha256(
        json.dumps(verified, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    retrieved_at = max(record.verified_at for record in verified_records if record.verified_at)
    return LinkCatalogSourceV2(
        source_type="live_probe",
        location="selected HTTPS targets",
        revision_or_hash=f"sha256:{digest}",
        retrieved_at=retrieved_at,
        http_status=200,
    )


def build_catalog_pair(
    args: argparse.Namespace,
) -> tuple[AsposeLinkCatalogV2, AsposeLinkCatalogV2]:
    """Build both catalogs from one registry scope and one deterministic core."""

    root = args.aspose_org_root.resolve()
    target_path = (args.aspose_com_source or root / "data/aspose_com_targets.json").resolve()
    target_map = json.loads(target_path.read_text(encoding="utf-8"))
    scope = _registry_scope(args.products)
    org_revision = _git_value(root, "rev-parse", "HEAD")
    org_retrieved_at = _git_value(root, "show", "-s", "--format=%cI", org_revision)
    live_at = datetime.now(UTC).isoformat()
    org_records = discover_org_records(
        source_root=root,
        source_revision=org_revision,
        retrieved_at=org_retrieved_at,
        registry_scope=scope,
        status_by_url=_legacy_statuses(args.org_output),
    )
    discovered_org_urls = {record.url for record in org_records}
    org_records.extend(
        record
        for record in _legacy_landing_records(
            args.org_output,
            parent_domain="aspose.org",
        )
        if record.url not in discovered_org_urls
    )
    org_records = _apply_live_patterns(
        org_records,
        args.verify_org_pattern,
        verified_at=live_at,
    )
    target_hash = _sha256(target_path)
    com_retrieved_at = _source_generated_at(target_map)
    com_records = discover_com_records(
        target_map=target_map,
        source_location=Path("aspose.org/data/aspose_com_targets.json"),
        source_revision_or_hash=target_hash,
        retrieved_at=com_retrieved_at,
        registry_scope=scope,
        relevant_terms=_relevant_terms(org_records),
    )
    com_records = _apply_live_patterns(
        com_records,
        args.verify_com_pattern,
        verified_at=live_at,
    )
    org_source = LinkCatalogSourceV2(
        source_type="source_tree",
        location="aspose.org/content",
        revision_or_hash=org_revision,
        retrieved_at=org_retrieved_at,
    )
    com_source = LinkCatalogSourceV2(
        source_type="source_db",
        location="aspose.org/data/aspose_com_targets.json",
        revision_or_hash=target_hash,
        retrieved_at=com_retrieved_at,
    )
    org_sources = [org_source]
    if live_source := _live_probe_source(org_records):
        org_sources.append(live_source)
    com_sources = [com_source]
    if live_source := _live_probe_source(com_records):
        com_sources.append(live_source)
    org_catalog = build_catalog(
        parent_domain="aspose.org",
        records=org_records,
        sources=org_sources,
        generated_at=_latest_catalog_time(org_records, org_retrieved_at),
    )
    com_catalog = build_catalog(
        parent_domain="aspose.com",
        records=com_records,
        sources=com_sources,
        generated_at=_latest_catalog_time(com_records, com_retrieved_at),
    )
    return com_catalog, org_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aspose-org-root", type=Path, default=DEFAULT_ASPOSE_ORG_ROOT)
    parser.add_argument("--aspose-com-source", type=Path)
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--com-output", type=Path, default=DEFAULT_COM_OUTPUT)
    parser.add_argument("--org-output", type=Path, default=DEFAULT_ORG_OUTPUT)
    parser.add_argument("--verify-org-pattern", action="append", default=[])
    parser.add_argument("--verify-com-pattern", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        com_catalog, org_catalog = build_catalog_pair(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"aspose.com records={com_catalog.provenance.total_records} "
        f"verified={com_catalog.provenance.verified_records}",
        file=sys.stderr,
    )
    print(
        f"aspose.org records={org_catalog.provenance.total_records} "
        f"verified={org_catalog.provenance.verified_records}",
        file=sys.stderr,
    )
    if args.dry_run:
        return 0
    write_catalog_atomic(com_catalog, args.com_output)
    write_catalog_atomic(org_catalog, args.org_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
