"""Prove useful article selection, zero-link decisions, and final link validation."""

from __future__ import annotations

from typing import Literal

import pytest

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
)
from readme_agent.links.catalog import canonical_catalog_payload_hash
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1, AsposeLinkCatalogV2
from readme_agent.links.contextual_selection import select_contextual_links
from readme_agent.links.contextual_validation import validate_contextual_link_candidate
from readme_agent.registry.models import LinkAllocationPolicyV1

REVISION = "a" * 40


def _facts(platform: str, *, code: str) -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://fixture",
        source_revision=REVISION,
    )
    records: list[FactRecordV2] = []
    for field in REQUIRED_PRODUCT_FIELDS:
        if field == "product.identity":
            value = {"family": "cells", "platform": platform, "ecosystem": platform}
            state: Literal["verified", "missing"] = "verified"
        elif field == "example.minimal":
            value = {"language": platform, "code": code}
            state = "verified"
        else:
            value = None
            state = "missing"
        records.append(
            FactRecordV2(
                fact_id=f"{field}:fixture",
                field=field,
                value=value,
                source=source,
                verification_state=state,
                authoritative_owner="fixture-owner",
                confidence=1.0 if state == "verified" else 0.0,
                affected_surfaces=["readme"],
            )
        )
    return ProductFactsV2(
        org_repo="fixture/product",
        facts=records,
        selected_fact_ids={record.field: record.fact_id for record in records},
    )


def _catalog(
    parent: Literal["aspose.org", "aspose.com"],
    *,
    platform: str,
    surface: Literal["docs", "products"],
    terms: list[str],
    status: int = 200,
) -> AsposeLinkCatalogV2:
    host = f"{surface}.{parent}"
    url = f"https://{host}/cells/{platform}/workflow/"
    record_id = f"{parent.replace('.', '-')}:{surface}:cells:{platform}:workflow"
    payload = {
        "schema_version": "2.0",
        "parent_domain": parent,
        "provenance": {
            "generated_at": "2026-07-28T00:00:00+00:00",
            "generator": "fixture",
            "generator_version": "1",
            "sources": [
                {
                    "source_type": "live_probe",
                    "location": "fixture",
                    "revision_or_hash": "fixture",
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
                "surface": surface,
                "url": url,
                "title": "Verified workflow",
                "family": "cells",
                "platforms": [platform],
                "subject_terms": terms,
                "content_evidence": "source_body" if surface == "docs" else "landing",
                "source_type": "source_tree",
                "source_location": "fixture.md",
                "source_revision_or_hash": "fixture",
                "retrieved_at": "2026-07-28T00:00:00+00:00",
                "http_status": status,
                "verified_at": "2026-07-28T00:00:00+00:00" if status == 200 else None,
                "http_verification_source": "live_probe" if status == 200 else None,
                "http_verification_evidence": "fixture:HEAD_OR_GET" if status == 200 else None,
            }
        },
    }
    payload["provenance"]["output_hash"] = canonical_catalog_payload_hash(payload)
    return AsposeLinkCatalogV2.model_validate(payload)


def _catalogs(platform: str, terms: list[str], *, status: int = 200) -> AsposeLinkCatalogSetV1:
    return AsposeLinkCatalogSetV1(
        aspose_org=_catalog(
            "aspose.org",
            platform=platform,
            surface="docs",
            terms=terms,
            status=status,
        ),
        aspose_com=_catalog(
            "aspose.com",
            platform=platform,
            surface="products",
            terms=["cells", platform],
        ),
    )


def _markdown(code: str, *, existing: str = "") -> str:
    return f"# Product\n\nOpening.\n\n## Quick start\n\n```text\n{code}\n```\n{existing}"


@pytest.mark.parametrize(
    ("platform", "code", "terms"),
    [
        ("python", "scene = Scene()\nscene.open('model.obj')", ["scene", "scene.open"]),
        ("net", 'var scene = new Scene();\nscene.Open("model.obj");', ["scene", "scene.open"]),
        ("java", 'Workbook book = new Workbook();\nbook.save("out.xlsx");', ["workbook"]),
        ("cpp", 'Workbook book;\nbook.Save("out.xlsx");', ["workbook"]),
        ("typescript", "const scene = new Scene();\nscene.open('model.obj');", ["scene"]),
        ("rust", 'let book = Workbook::new();\nbook.save("out.xlsx");', ["workbook"]),
        ("go", 'document := NewDocument()\ndocument.Save("out.pdf")', ["newdocument"]),
    ],
)
def test_seven_prioritized_platforms_select_exact_article(
    platform: str,
    code: str,
    terms: list[str],
) -> None:
    plan = select_contextual_links(
        _facts(platform, code=code),
        _markdown(code),
        _catalogs(platform, terms),
        LinkAllocationPolicyV1(),
    )

    assert plan.omission_reason == "none"
    assert len(plan.bindings) == 1
    assert plan.bindings[0].surface == "docs"
    assert plan.bindings[0].accepted_fact_ids == [
        "product.identity:fixture",
        "example.minimal:fixture",
    ]


def test_weak_wrong_platform_unverified_and_zero_budget_targets_are_omitted() -> None:
    code = "scene = Scene()"
    facts = _facts("python", code=code)

    weak = select_contextual_links(
        facts,
        _markdown(code),
        _catalogs("python", ["guide"]),
        LinkAllocationPolicyV1(),
    )
    wrong_platform = select_contextual_links(
        facts,
        _markdown(code),
        _catalogs("java", ["scene"]),
        LinkAllocationPolicyV1(),
    )
    unverified = select_contextual_links(
        facts,
        _markdown(code),
        _catalogs("python", ["scene"], status=404),
        LinkAllocationPolicyV1(),
    )
    zero = select_contextual_links(
        facts,
        _markdown(code),
        _catalogs("python", ["scene"]),
        LinkAllocationPolicyV1.model_validate(
            {
                "mode": "configured",
                "max_total": 0,
                "domain_maxima": {"aspose.org": 0, "aspose.com": 0},
                "surface_maxima": {
                    "products": 0,
                    "docs": 0,
                    "kb": 0,
                    "blog": 0,
                    "reference": 0,
                },
            }
        ),
    )

    assert weak.omission_reason == "no_strong_context_match"
    assert wrong_platform.omission_reason == "no_strong_context_match"
    assert unverified.omission_reason == "no_strong_context_match"
    assert zero.omission_reason == "budget_exhausted"


def test_existing_target_is_not_duplicated_and_final_candidate_validates() -> None:
    code = "scene = Scene()"
    catalogs = _catalogs("python", ["scene"])
    target = next(iter(catalogs.aspose_org.records.values()))
    plain = _markdown(code)
    plan = select_contextual_links(
        _facts("python", code=code),
        plain,
        catalogs,
        LinkAllocationPolicyV1(),
    )
    candidate = plain + f"\nFor details, see [Verified workflow]({target.url}).\n"

    assert validate_contextual_link_candidate(
        plan,
        catalogs,
        candidate,
        _facts("python", code=code),
    ).valid
    rerun = select_contextual_links(
        _facts("python", code=code),
        candidate,
        catalogs,
        LinkAllocationPolicyV1(),
    )
    assert rerun.omission_reason == "target_already_present"
    assert rerun.bindings == []


def test_opening_link_and_repeated_target_fail_final_validation() -> None:
    code = "scene = Scene()"
    catalogs = _catalogs("python", ["scene"])
    target = next(iter(catalogs.aspose_org.records.values()))
    plan = select_contextual_links(
        _facts("python", code=code),
        _markdown(code),
        catalogs,
        LinkAllocationPolicyV1(),
    )
    bad = f"# Product\n\n[Docs]({target.url})\n\n## Quick start\n\n{target.url}\n"

    verdict = validate_contextual_link_candidate(
        plan,
        catalogs,
        bad,
        _facts("python", code=code),
    )

    assert not verdict.valid
    assert any("opening" in error for error in verdict.errors)
    assert any("repeats" in error for error in verdict.errors)
