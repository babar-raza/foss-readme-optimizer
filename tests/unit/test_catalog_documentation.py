"""Verify exact governed catalog documentation facts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.facts.catalog_documentation import catalog_documentation_fact
from readme_agent.registry.models import ProductEntry


def _entry() -> ProductEntry:
    return ProductEntry(
        family="3d",
        platform="python",
        repo_name="Aspose.3D-FOSS-for-Python",
        repo_url="https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        clone_url="https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git",
        active=True,
        discovered_via="fixture",
        mode="disabled",
        ecosystem="python",
        policy_profile="fixture",
    )


def _catalog(path: Path, *, title: str = "Aspose.3D FOSS for Python") -> None:
    records = {}
    for surface in ("docs", "kb", "reference"):
        records[f"org:{surface}:3d:python:root"] = {
            "record_id": f"org:{surface}:3d:python:root",
            "surface": surface,
            "url": f"https://{surface}.aspose.org/3d/python/",
            "title": title,
            "family": "3d",
            "platforms": ["python"],
            "content_evidence": "source_body",
            "source_location": f"content/{surface}/3d/python/_index.md",
            "source_revision_or_hash": "a" * 40,
        }
    path.write_text(
        json.dumps({"parent_domain": "aspose.org", "records": records}), encoding="utf-8"
    )


def test_catalog_fact_binds_product_family_platform_and_content_hash(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    _catalog(catalog)

    fact = catalog_documentation_fact(_entry(), catalog_path=catalog)

    assert fact is not None
    assert [item["surface"] for item in fact.value] == ["docs", "kb", "reference"]
    assert all(item["family"] == "3d" for item in fact.value)
    assert all(item["platform"] == "python" for item in fact.value)
    assert all(item["product"] == "Aspose.3D-FOSS-for-Python" for item in fact.value)
    digest = hashlib.sha256(catalog.read_bytes()).hexdigest()
    assert fact.source.source_revision == f"sha256:{digest}"
    assert fact.verification_state == "verified"


def test_catalog_fact_rejects_cross_product_and_slug_only_records(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    _catalog(catalog, title="Aspose.Cells FOSS for Python")

    assert catalog_documentation_fact(_entry(), catalog_path=catalog) is None


def test_real_catalog_supplies_exact_three_surface_roots() -> None:
    fact = catalog_documentation_fact(_entry())

    assert fact is not None
    assert [item["url"] for item in fact.value] == [
        "https://docs.aspose.org/3d/python/",
        "https://kb.aspose.org/3d/python/",
        "https://reference.aspose.org/3d/python/",
    ]
