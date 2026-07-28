"""Prove the paired Aspose link-catalog generator through its public CLI seam."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from readme_agent.links.catalog import load_aspose_link_catalogs, query_linkable_targets
from readme_agent.links.catalog_models import (
    AsposeLinkCatalogV2,
    AsposeLinkRecordV2,
    LinkCatalogSourceV2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "scripts/data-refresh/build_aspose_link_catalogs.py"
sys.path.insert(0, str(GENERATOR.parent))

from aspose_link_catalog_core import (  # noqa: E402
    build_catalog,
    merge_records,
    write_catalog_atomic,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit_fixture(root: Path) -> str:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Fixture"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "fixture@example.test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", "fixture"],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-07-28T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-07-28T00:00:00+00:00",
        },
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_generator_writes_domain_pure_registry_scoped_catalog_pair(tmp_path: Path) -> None:
    source_root = tmp_path / "aspose.org"
    products = tmp_path / "products.json"
    com_output = tmp_path / "aspose_com_links.json"
    org_output = tmp_path / "aspose_org_links.json"
    article_url = "https://docs.aspose.org/cells/python/workbook/"
    _write(
        source_root / "content/docs.aspose.org/en/cells/python/workbook/index.md",
        """---
title: Work with workbooks
description: Load and save a workbook with the Python API.
evidence:
  model_sha: abc123
  apis:
    - Workbook.load
  formats:
    - ext: xlsx
---

Verified article body.
""",
    )
    _write(
        source_root / "content/products.aspose.org/en/cells/_index.md",
        "---\ntitle: Aspose.Cells FOSS\n---\n",
    )
    _write(
        source_root / "content/products.aspose.org/en/cells/python/_index.md",
        "---\ntitle: Aspose.Cells FOSS for Python\n---\n",
    )
    _write(
        source_root / "data/aspose_com_targets.json",
        json.dumps(
            {
                "provenance": {"generated_at": "2026-07-27T00:00:00+00:00"},
                "all_urls": {
                    "https://products.aspose.com/cells/python-net/": {
                        "http_status": 200,
                        "platform": "python-net",
                    },
                    "https://docs.aspose.com/cells/python-net/workbook/": {
                        "http_status": 200,
                        "platform": "python-net",
                    },
                    "https://products.aspose.org/cells/python/": {
                        "http_status": 200,
                        "platform": "python",
                    },
                },
            },
            sort_keys=True,
        ),
    )
    _write(
        products,
        json.dumps(
            [
                {
                    "family": "cells",
                    "platform": "python",
                    "active": True,
                }
            ]
        ),
    )
    _write(
        org_output,
        json.dumps(
            {
                "provenance": {"generated_at": "2026-07-27T00:00:00+00:00"},
                "surfaces": {
                    "docs": {
                        "families": {
                            "workbook": {
                                "url": article_url,
                                "http_status": 200,
                            }
                        },
                        "platforms": {},
                    },
                    "products": {
                        "families": {
                            "cells": {
                                "url": "https://products.aspose.org/cells/",
                                "http_status": 200,
                            }
                        },
                        "platforms": {
                            "cells/python": {
                                "url": "https://products.aspose.org/cells/python/",
                                "http_status": 200,
                            }
                        },
                    },
                },
                "blog": {"categories": {}},
            }
        ),
    )
    revision = _commit_fixture(source_root)
    _write(
        source_root / "content/docs.aspose.org/en/cells/python/workbook/index.md",
        "---\ntitle: Dirty uncommitted article\n---\n",
    )
    _write(
        source_root / "data/aspose_com_targets.json",
        json.dumps(
            {
                "provenance": {"generated_at": "2099-01-01T00:00:00+00:00"},
                "all_urls": {
                    "https://products.aspose.com/dirty/uncommitted/": {
                        "http_status": 200,
                        "platform": "python-net",
                    }
                },
            }
        ),
    )

    command = [
        sys.executable,
        str(GENERATOR),
        "--aspose-org-root",
        str(source_root),
        "--products",
        str(products),
        "--com-output",
        str(com_output),
        "--org-output",
        str(org_output),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    catalogs = load_aspose_link_catalogs(com_path=com_output, org_path=org_output)
    assert catalogs.aspose_org.provenance.sources[0].revision_or_hash == revision
    assert all(
        record.parent_domain == "aspose.org" for record in catalogs.aspose_org.records.values()
    )
    assert all(
        record.parent_domain == "aspose.com" for record in catalogs.aspose_com.records.values()
    )
    targets = query_linkable_targets(catalogs, family="cells", platform="python")
    assert [target.url for target in targets] == [
        article_url,
        "https://products.aspose.org/cells/python/",
        "https://products.aspose.com/cells/python-net/",
        "https://products.aspose.org/cells/",
    ]
    assert targets[0].content_evidence == "source_body"
    assert targets[0].title == "Work with workbooks"
    assert all("dirty/uncommitted" not in target.url for target in catalogs.records)
    assert all(
        record.http_verification_source and record.http_verification_evidence
        for record in catalogs.records
        if record.http_status == 200
    )
    assert not list(tmp_path.glob("*.tmp"))

    before = (com_output.read_bytes(), org_output.read_bytes())
    repeated = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert repeated.returncode == 0, repeated.stderr
    assert (com_output.read_bytes(), org_output.read_bytes()) == before


def test_core_rejects_empty_disagreement_and_invalid_atomic_replacement(
    tmp_path: Path,
) -> None:
    source = LinkCatalogSourceV2(
        source_type="live_probe",
        location="fixture",
        revision_or_hash="sha256:fixture",
        retrieved_at="2026-07-28T00:00:00+00:00",
        http_status=200,
    )
    record = AsposeLinkRecordV2(
        record_id="org:docs:cells:python:fixture",
        parent_domain="aspose.org",
        surface="docs",
        url="https://docs.aspose.org/cells/python/workbook/",
        title="Workbook",
        family="cells",
        platforms=["python"],
        subject_terms=["workbook"],
        content_evidence="source_body",
        source_type="source_tree",
        source_location="fixture.md",
        source_revision_or_hash="abc",
        retrieved_at="2026-07-28T00:00:00+00:00",
        http_status=200,
        verified_at="2026-07-28T00:00:00+00:00",
        http_verification_source="live_probe",
        http_verification_evidence="fixture:HEAD_OR_GET",
    )

    with pytest.raises(ValueError, match="refusing empty"):
        build_catalog(parent_domain="aspose.org", records=[], sources=[source])
    with pytest.raises(ValueError, match="disagreement"):
        merge_records([record, record.model_copy(update={"title": "Different"})])

    catalog = build_catalog(
        parent_domain="aspose.org",
        records=[record],
        sources=[source],
        generated_at="2026-07-28T00:00:00+00:00",
    )
    output = tmp_path / "catalog.json"
    write_catalog_atomic(catalog, output)
    before = output.read_bytes()
    invalid: AsposeLinkCatalogV2 = catalog.model_copy(
        update={
            "provenance": catalog.provenance.model_copy(
                update={"output_hash": "sha256:" + ("0" * 64)}
            )
        }
    )
    with pytest.raises(ValueError, match="not self-consistent"):
        write_catalog_atomic(invalid, output)
    assert output.read_bytes() == before
