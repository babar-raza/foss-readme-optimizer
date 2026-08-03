"""Full-product display-name normalization for verified examples."""

from readme_agent.facts.example_branding import (
    full_product_display_name,
    normalize_example_display_literals,
)
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2


def _facts() -> ProductFactsV2:
    identity = FactRecordV2(
        fact_id="product.identity:verified",
        field="product.identity",
        value={
            "product_name": "Aspose.PDF",
            "family": "pdf",
            "platform": "python",
            "ecosystem": "python",
        },
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="pyproject.toml",
            source_revision="a" * 40,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    return ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo="aspose-pdf-foss/Aspose-PDF-FOSS-for-Python",
        facts=[identity],
        selected_fact_ids={"product.identity": identity.fact_id},
        package_root_roles=None,
    )


def test_expands_abbreviated_name_only_in_natural_display_literals():
    code = """from aspose_pdf import Document
package_name = "aspose-pdf-foss-for-python"
api_identifier = "Aspose.PDF FOSS"
print("Hello from Aspose.PDF FOSS!")
label = 'Try Aspose.PDF FOSS today.'
"""

    normalized = normalize_example_display_literals(
        code,
        product_name="Aspose.PDF",
        full_display_name="Aspose.PDF FOSS for Python",
    )

    assert "from aspose_pdf import Document" in normalized
    assert 'package_name = "aspose-pdf-foss-for-python"' in normalized
    assert 'api_identifier = "Aspose.PDF FOSS"' in normalized
    assert 'print("Hello from Aspose.PDF FOSS for Python!")' in normalized
    assert "label = 'Try Aspose.PDF FOSS for Python today.'" in normalized


def test_normalization_is_idempotent_and_unrelated_examples_are_byte_identical():
    already_full = 'print("Hello from Aspose.PDF FOSS for Python!")\n'
    unrelated = 'print("Hello from another project!")\n'

    assert (
        normalize_example_display_literals(
            already_full,
            product_name="Aspose.PDF",
            full_display_name="Aspose.PDF FOSS for Python",
        )
        == already_full
    )
    assert (
        normalize_example_display_literals(
            unrelated,
            product_name="Aspose.PDF",
            full_display_name="Aspose.PDF FOSS for Python",
        )
        == unrelated
    )


def test_full_display_name_comes_from_verified_identity():
    assert full_product_display_name(_facts()) == "Aspose.PDF FOSS for Python"
