"""`FACT-012` (Wave 11.3): `diff_product_facts()` -- a pure diff between two
`ProductFactsV1` snapshots."""

import pytest

from readme_agent.facts.changeset import diff_product_facts
from readme_agent.facts.schema import PackageCoordinateFactV1, ProductFactsV1


def _facts(**overrides) -> ProductFactsV1:
    base = dict(org_repo="acme/widget", family="widget", platform="java", ecosystem="java")
    return ProductFactsV1(**{**base, **overrides})


class TestDiffProductFacts:
    def test_identical_snapshots_have_no_changes(self):
        changeset = diff_product_facts(_facts(), _facts())
        assert not changeset.has_changes
        assert changeset.changed_fields == []
        assert changeset.package_coordinate_changes == []

    def test_scalar_field_change_is_reported(self):
        changeset = diff_product_facts(
            _facts(declared_license="MIT"), _facts(declared_license="Apache-2.0")
        )
        assert changeset.has_changes
        assert changeset.changed_fields == ["declared_license"]

    def test_different_org_repo_raises(self):
        with pytest.raises(ValueError):
            diff_product_facts(_facts(org_repo="acme/a"), _facts(org_repo="acme/b"))

    def test_new_package_root_is_reported(self):
        before = _facts()
        after = _facts(
            package_coordinates=[
                PackageCoordinateFactV1(path=".", ecosystem="java", manifest_path="pom.xml")
            ]
        )
        changeset = diff_product_facts(before, after)
        assert changeset.has_changes
        assert "new package root" in changeset.package_coordinate_changes[0]

    def test_removed_package_root_is_reported(self):
        before = _facts(
            package_coordinates=[
                PackageCoordinateFactV1(path=".", ecosystem="java", manifest_path="pom.xml")
            ]
        )
        after = _facts()
        changeset = diff_product_facts(before, after)
        assert "no longer detected" in changeset.package_coordinate_changes[0]

    def test_verification_outcome_flip_is_reported(self):
        """The concrete, load-bearing case: a package that resolved before
        (`REGISTRY_VERIFIED`) and no longer does (`NOT_PUBLISHED`) -- e.g.
        a real package removed/yanked from its registry."""
        before = _facts(
            package_coordinates=[
                PackageCoordinateFactV1(
                    path=".",
                    ecosystem="java",
                    manifest_path="pom.xml",
                    verification_outcome="REGISTRY_VERIFIED",
                )
            ]
        )
        after = _facts(
            package_coordinates=[
                PackageCoordinateFactV1(
                    path=".",
                    ecosystem="java",
                    manifest_path="pom.xml",
                    verification_outcome="NOT_PUBLISHED",
                )
            ]
        )
        changeset = diff_product_facts(before, after)
        assert changeset.has_changes
        assert "REGISTRY_VERIFIED -> NOT_PUBLISHED" in changeset.package_coordinate_changes[0]

    def test_unchanged_verification_outcome_is_not_reported(self):
        coord = PackageCoordinateFactV1(
            path=".",
            ecosystem="java",
            manifest_path="pom.xml",
            verification_outcome="REGISTRY_VERIFIED",
        )
        before = _facts(package_coordinates=[coord])
        after = _facts(package_coordinates=[coord.model_copy()])
        changeset = diff_product_facts(before, after)
        assert not changeset.has_changes
