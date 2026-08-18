"""T10 -- anchor text naming one platform must not link to another's destination."""

from __future__ import annotations

from readme_agent.links.anchor_destination_consistency import (
    find_anchor_destination_mismatches,
    find_via_anchor_findings,
)
from readme_agent.links.catalog_models import (
    AsposeLinkCatalogProvenanceV2,
    AsposeLinkCatalogSetV1,
    AsposeLinkCatalogV2,
    AsposeLinkRecordV2,
    LinkCatalogSourceV2,
)

_SOURCE = LinkCatalogSourceV2(
    source_type="live_probe",
    location="fixture",
    revision_or_hash="sha256:fixture",
    retrieved_at="2026-07-28T00:00:00+00:00",
    http_status=200,
)


def _record(
    record_id: str,
    url: str,
    platforms: list[str],
    parent_domain: str = "aspose.org",
) -> AsposeLinkRecordV2:
    return AsposeLinkRecordV2(
        record_id=record_id,
        parent_domain=parent_domain,
        surface="docs",
        url=url,
        title="Docs",
        family="pdf",
        platforms=platforms,
        subject_terms=["fixture"],
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


def _catalog_set(*records: AsposeLinkRecordV2) -> AsposeLinkCatalogSetV1:
    provenance = AsposeLinkCatalogProvenanceV2(
        generated_at="2026-07-28T00:00:00+00:00",
        generator="test_anchor_destination_consistency",
        generator_version="1",
        sources=[_SOURCE],
        total_records=max(len(records), 1),
        verified_records=len(records),
        output_hash="sha256:" + "0" * 64,
    )
    return AsposeLinkCatalogSetV1(
        aspose_org=AsposeLinkCatalogV2(
            parent_domain="aspose.org",
            provenance=provenance,
            records={record.record_id: record for record in records},
        ),
        aspose_com=AsposeLinkCatalogV2(
            parent_domain="aspose.com",
            provenance=provenance,
            records={"com:products:pdf:unused": _com_placeholder},
        ),
    )


_com_placeholder = _record(
    "com:products:pdf:unused",
    "https://products.aspose.com/pdf/unused/",
    platforms=["java"],
    parent_domain="aspose.com",
)


def test_flags_an_anchor_naming_a_platform_the_destination_does_not_serve() -> None:
    java_docs = _record(
        "org:docs:pdf:java:workbook",
        "https://docs.aspose.org/pdf/java/workbook/",
        platforms=["java"],
    )
    catalogs = _catalog_set(java_docs)
    markdown = (
        "See the [Aspose.PDF for .NET documentation](https://docs.aspose.org/pdf/java/workbook/)."
    )

    findings = find_anchor_destination_mismatches(markdown, catalogs)

    assert len(findings) == 1
    assert findings[0].claimed_platform == "net"
    assert findings[0].destination_platforms == ("java",)


def test_does_not_flag_a_correctly_matched_anchor() -> None:
    java_docs = _record(
        "org:docs:pdf:java:workbook",
        "https://docs.aspose.org/pdf/java/workbook/",
        platforms=["java"],
    )
    catalogs = _catalog_set(java_docs)
    markdown = (
        "See the [Aspose.PDF for Java documentation](https://docs.aspose.org/pdf/java/workbook/)."
    )

    assert find_anchor_destination_mismatches(markdown, catalogs) == []


def test_does_not_flag_an_anchor_with_no_platform_claim() -> None:
    java_docs = _record(
        "org:docs:pdf:java:workbook",
        "https://docs.aspose.org/pdf/java/workbook/",
        platforms=["java"],
    )
    catalogs = _catalog_set(java_docs)
    markdown = "See the [workbook documentation](https://docs.aspose.org/pdf/java/workbook/)."

    assert find_anchor_destination_mismatches(markdown, catalogs) == []


def test_does_not_flag_a_destination_absent_from_the_catalog() -> None:
    catalogs = _catalog_set(
        _record(
            "org:docs:pdf:java:other",
            "https://docs.aspose.org/pdf/java/other/",
            platforms=["java"],
        )
    )
    markdown = (
        "See the [Aspose.PDF for .NET documentation](https://docs.aspose.org/pdf/net/unlisted/)."
    )

    assert find_anchor_destination_mismatches(markdown, catalogs) == []


def test_multi_platform_destinations_accept_any_listed_claim() -> None:
    shared_docs = _record(
        "org:docs:pdf:shared:workbook",
        "https://docs.aspose.org/pdf/shared/workbook/",
        platforms=["java", "net"],
    )
    catalogs = _catalog_set(shared_docs)
    markdown = (
        "[Aspose.PDF for .NET](https://docs.aspose.org/pdf/shared/workbook/) and "
        "[Aspose.PDF for Java](https://docs.aspose.org/pdf/shared/workbook/) share this page."
    )

    assert find_anchor_destination_mismatches(markdown, catalogs) == []


def test_does_not_flag_via_in_surrounding_prose_outside_the_anchor() -> None:
    markdown = "Convert PDFs via [Aspose.PDF for Java](https://docs.aspose.org/pdf/java/workbook/)."

    assert find_via_anchor_findings(markdown) == []


def test_flags_via_inside_the_anchor_text_itself() -> None:
    markdown = "[Convert via Aspose.PDF for Java](https://docs.aspose.org/pdf/java/workbook/)."

    findings = find_via_anchor_findings(markdown)

    assert len(findings) == 1
    assert findings[0].anchor_text == "Convert via Aspose.PDF for Java"


def test_does_not_flag_a_non_aspose_via_anchor() -> None:
    markdown = "[Convert via other tool](https://example.com/tool)."

    assert find_via_anchor_findings(markdown) == []
