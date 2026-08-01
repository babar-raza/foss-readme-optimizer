"""Repository-bound product identity canonicalization."""

from readme_agent.facts.product_identity import canonical_aspose_family_name


def test_hyphenated_aspose_repository_family_becomes_canonical_product_name() -> None:
    assert canonical_aspose_family_name("Aspose-PDF") == "Aspose.PDF"


def test_dotted_aspose_family_remains_canonical() -> None:
    assert canonical_aspose_family_name("Aspose.3D") == "Aspose.3D"


def test_repository_prefix_case_does_not_leak_into_product_branding() -> None:
    assert canonical_aspose_family_name("aspose-PDF") == "Aspose.PDF"


def test_non_aspose_identity_is_not_reclassified() -> None:
    assert canonical_aspose_family_name("Mesh-Toolkit") is None
