"""Prove Aspose-only Enterprise Edition correction and validation."""

from __future__ import annotations

import pytest

from readme_agent.links.terminology import (
    canonicalize_enterprise_edition,
    find_enterprise_terminology_findings,
)


@pytest.mark.parametrize(
    "legacy",
    [
        "full commercial edition",
        "commercial On-Premise edition",
        "full-featured commercial edition",
        "paid edition",
        "premium product",
        "On-Premise library",
    ],
)
def test_aspose_legacy_edition_labels_become_exact_enterprise_name(legacy: str) -> None:
    source = (
        "# Product\n\nAspose.3D FOSS can be upgraded to the "
        f"[{legacy}](https://products.aspose.com/3d/python-net/).\n"
    )

    rendered, corrections = canonicalize_enterprise_edition(
        source,
        enterprise_product_name="Aspose.3D for Python",
    )

    assert corrections
    assert "Aspose.3D for Python Enterprise Edition" in rendered
    assert find_enterprise_terminology_findings(rendered) == []


def test_commercial_aspose_on_premise_library_is_canonicalized() -> None:
    source = "Aspose.3D FOSS shares API design with the commercial Aspose.3D On-Premise library.\n"

    rendered, _ = canonicalize_enterprise_edition(
        source,
        enterprise_product_name="Aspose.3D",
    )

    assert rendered == "Aspose.3D FOSS shares API design with the Aspose.3D Enterprise Edition.\n"


def test_non_aspose_fixture_language_and_proprietary_formats_are_untouched() -> None:
    source = (
        "AcmeCells has a commercial edition.\n\n"
        "Aspose.3D Enterprise Edition supports proprietary formats.\n"
    )

    rendered, corrections = canonicalize_enterprise_edition(
        source,
        enterprise_product_name="Aspose.3D",
    )

    assert rendered == source
    assert corrections == []
    assert find_enterprise_terminology_findings(rendered) == []


def test_protected_code_is_not_rewritten() -> None:
    source = """Aspose.3D FOSS has an Enterprise Edition.

```python
label = "commercial edition"
```
"""

    rendered, corrections = canonicalize_enterprise_edition(
        source,
        enterprise_product_name="Aspose.3D",
    )

    assert rendered == source
    assert corrections == []


def test_products_aspose_com_link_requires_enterprise_edition_label() -> None:
    source = (
        "See [Aspose.3D for Java](https://products.aspose.com/3d/java/) for the broader product.\n"
    )

    findings = find_enterprise_terminology_findings(source)

    assert [(item.kind, item.excerpt) for item in findings] == [
        (
            "product_link_label",
            "[Aspose.3D for Java](https://products.aspose.com/3d/java/)",
        )
    ]
