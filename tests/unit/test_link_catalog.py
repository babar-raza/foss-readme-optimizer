"""Prove typed, domain-pure, checksum-validated Aspose catalog lookup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.errors import ConfigError
from readme_agent.links.catalog import (
    canonical_catalog_payload_hash,
    load_aspose_link_catalogs,
    load_link_catalog,
    lookup_verified_target,
    query_linkable_targets,
)


def _payload(parent: str, *, status: int = 200, evidence: str = "source_body") -> dict:
    host = f"docs.{parent}"
    record_id = f"{parent.replace('.', '-')}:docs:cells:python:workbook"
    payload = {
        "schema_version": "2.0",
        "parent_domain": parent,
        "provenance": {
            "generated_at": "2026-07-28T00:00:00+00:00",
            "generator": "fixture",
            "generator_version": "1",
            "sources": [
                {
                    "source_type": "source_tree",
                    "location": "fixture",
                    "revision_or_hash": "abc",
                    "retrieved_at": "2026-07-28T00:00:00+00:00",
                    "http_status": 200,
                }
            ],
            "total_records": 1,
            "verified_records": int(status == 200),
            "output_hash": "",
        },
        "records": {
            record_id: {
                "record_id": record_id,
                "parent_domain": parent,
                "surface": "docs",
                "url": f"https://{host}/cells/python/workbook/",
                "title": "Work with workbooks",
                "family": "cells",
                "platforms": ["python"],
                "subject_terms": ["workbook", "save"],
                "content_evidence": evidence,
                "source_type": "source_tree",
                "source_location": "fixture.md",
                "source_revision_or_hash": "abc",
                "retrieved_at": "2026-07-28T00:00:00+00:00",
                "http_status": status,
                "verified_at": "2026-07-28T00:00:00+00:00" if status == 200 else None,
                "http_verification_source": "live_probe" if status == 200 else None,
                "http_verification_evidence": "fixture:HEAD_OR_GET" if status == 200 else None,
            }
        },
    }
    payload["provenance"]["output_hash"] = canonical_catalog_payload_hash(payload)
    return payload


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_load_and_exact_lookup_remove_tracking_only(tmp_path: Path) -> None:
    com_path = tmp_path / "com.json"
    org_path = tmp_path / "org.json"
    _write(com_path, _payload("aspose.com"))
    _write(org_path, _payload("aspose.org"))

    catalogs = load_aspose_link_catalogs(com_path=com_path, org_path=org_path)
    record = lookup_verified_target(
        catalogs,
        "https://docs.aspose.org/cells/python/workbook/?utm_source=github",
    )

    assert record is not None
    assert record.parent_domain == "aspose.org"
    assert [
        item.parent_domain
        for item in query_linkable_targets(
            catalogs,
            family="cells",
            platform="python",
        )
    ] == ["aspose.org", "aspose.com"]


def test_slug_only_article_is_verified_but_not_linkable(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    _write(path, _payload("aspose.com", evidence="slug_only"))

    catalog = load_link_catalog(path)

    assert next(iter(catalog.records.values())).http_status == 200
    assert not next(iter(catalog.records.values())).linkable


def test_checksum_domain_and_status_disagreement_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    payload = _payload("aspose.org")
    payload["records"][next(iter(payload["records"]))]["url"] = (
        "https://docs.aspose.com/cells/python/workbook/"
    )
    _write(path, payload)

    with pytest.raises(ConfigError):
        load_link_catalog(path)

    payload = _payload("aspose.org")
    payload["provenance"]["output_hash"] = "sha256:" + ("0" * 64)
    _write(path, payload)
    with pytest.raises(ConfigError, match="output_hash mismatch"):
        load_link_catalog(path)
