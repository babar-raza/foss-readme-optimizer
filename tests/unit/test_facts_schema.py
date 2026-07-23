"""`FACT-010` (Wave 11.3): `ProductFactsV1`/`PackageCoordinateFactV1` --
a typed, honestly-scoped subset of `capabilities/get_product_facts.py`'s
own dict output, combined with an optional
`verify_package_acquisition.py` result."""

from readme_agent.facts.schema import PackageCoordinateFactV1, ProductFactsV1

_FACTS_RESULT = {
    "org_repo": "acme/widget",
    "family": "widget",
    "platform": "java",
    "ecosystem": "java",
    "declared_license": "MIT",
    "relationship_talking_points": ["open_source_scope"],
    "secondary_links": [],
    "unresolved_manifests": [],
    "package_roots": [
        {
            "path": ".",
            "ecosystem": "java",
            "manifest_path": "pom.xml",
            "confidence": 1.0,
            "evidence": "found pom.xml",
        }
    ],
}


class TestPackageCoordinateFactV1:
    def test_verification_fields_default_to_none(self):
        fact = PackageCoordinateFactV1(path=".", ecosystem="java", manifest_path="pom.xml")
        assert fact.verification_outcome is None
        assert fact.verification_detail is None


class TestFromCapabilityResults:
    def test_without_acquisition_results_leaves_verification_fields_none(self):
        facts = ProductFactsV1.from_capability_results(_FACTS_RESULT)

        assert facts.org_repo == "acme/widget"
        assert facts.declared_license == "MIT"
        assert len(facts.package_coordinates) == 1
        coord = facts.package_coordinates[0]
        assert coord.path == "."
        assert coord.ecosystem == "java"
        assert coord.verification_outcome is None

    def test_with_acquisition_results_merges_by_path(self):
        acquisition_results = [
            {"path": ".", "ecosystem": "java", "outcome": "REGISTRY_VERIFIED", "detail": "found"}
        ]

        facts = ProductFactsV1.from_capability_results(
            _FACTS_RESULT, acquisition_results=acquisition_results
        )

        coord = facts.package_coordinates[0]
        assert coord.verification_outcome == "REGISTRY_VERIFIED"
        assert coord.verification_detail == "found"

    def test_acquisition_results_not_covering_every_root_leaves_others_none(self):
        multi_root_facts = {
            **_FACTS_RESULT,
            "package_roots": [
                *_FACTS_RESULT["package_roots"],
                {
                    "path": "module-a",
                    "ecosystem": "java",
                    "manifest_path": "module-a/pom.xml",
                    "confidence": 1.0,
                    "evidence": "found pom.xml",
                },
            ],
        }
        acquisition_results = [
            {"path": ".", "ecosystem": "java", "outcome": "REGISTRY_VERIFIED", "detail": "found"}
        ]

        facts = ProductFactsV1.from_capability_results(
            multi_root_facts, acquisition_results=acquisition_results
        )

        by_path = {c.path: c for c in facts.package_coordinates}
        assert by_path["."].verification_outcome == "REGISTRY_VERIFIED"
        assert by_path["module-a"].verification_outcome is None

    def test_missing_optional_fields_default_safely(self):
        minimal = {"org_repo": "acme/widget"}
        facts = ProductFactsV1.from_capability_results(minimal)
        assert facts.package_coordinates == []
        assert facts.relationship_talking_points == []
        assert facts.declared_license is None
