from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent.profile.detector import build_profile
from readme_agent.profile.schema import DetectedEcosystem, PackageRoot, RepositoryProfile


class TestSchema:
    def test_repository_profile_defaults(self):
        profile = RepositoryProfile(org_repo="acme/widget")
        assert profile.detected_ecosystems == []
        assert profile.unresolved_manifests == []
        assert profile.package_roots == []

    def test_detected_ecosystem_requires_all_fields(self):
        with pytest.raises(ValidationError):
            DetectedEcosystem(ecosystem="java")

    def test_package_root_requires_all_fields(self):
        with pytest.raises(ValidationError):
            PackageRoot(ecosystem="java")


class TestBuildProfile:
    def test_single_ecosystem(self, tmp_path):
        (tmp_path / "pom.xml").write_text(
            "<project><groupId>com.acme</groupId><artifactId>widget</artifactId></project>",
            encoding="utf-8",
        )

        profile = build_profile("acme/widget", tmp_path)

        assert profile.org_repo == "acme/widget"
        assert len(profile.detected_ecosystems) == 1
        detected = profile.detected_ecosystems[0]
        assert detected.ecosystem == "java"
        assert detected.manifest_path == "pom.xml"
        assert detected.confidence == 1.0
        assert "parsed" in detected.evidence

    def test_synthetic_multi_ecosystem_fixture(self, tmp_path):
        """ECO-001's own stated acceptance evidence: array, not scalar."""
        (tmp_path / "pom.xml").write_text(
            "<project><groupId>com.acme</groupId></project>", encoding="utf-8"
        )
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "widget"\n', encoding="utf-8")

        profile = build_profile("acme/widget", tmp_path)

        ecosystems = {d.ecosystem for d in profile.detected_ecosystems}
        assert ecosystems == {"java", "python"}

    def test_unresolved_manifest_recorded_not_guessed(self, tmp_path):
        """ECO-003: a manifest-shaped file matching no registered ecosystem
        is recorded, never silently dropped."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "widget"\n', encoding="utf-8")

        profile = build_profile("acme/widget", tmp_path)

        assert profile.detected_ecosystems == []
        assert "Cargo.toml" in profile.unresolved_manifests

    def test_known_non_manifest_files_excluded_from_unresolved(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

        profile = build_profile("acme/widget", tmp_path)

        assert profile.unresolved_manifests == []

    def test_no_manifests_at_all(self, tmp_path):
        profile = build_profile("acme/widget", tmp_path)

        assert profile.detected_ecosystems == []
        assert profile.unresolved_manifests == []

    def test_low_confidence_when_manifest_found_but_nothing_parsed(self, tmp_path):
        (tmp_path / "pom.xml").write_text("not real xml at all", encoding="utf-8")

        profile = build_profile("acme/widget", tmp_path)

        detected = profile.detected_ecosystems[0]
        assert detected.confidence == 0.5
        assert "nothing parsed" in detected.evidence


class TestBuildProfilePackageRoots:
    """Wave 11.1 (`ECO-004`): `package_roots` is the additive, multi-root-
    aware view -- `detected_ecosystems` above stays exactly "first match
    per ecosystem," unaffected."""

    def test_single_root_repo_has_exactly_one_package_root(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")

        profile = build_profile("acme/widget", tmp_path)

        assert len(profile.package_roots) == 1
        root = profile.package_roots[0]
        assert root.path == "."
        assert root.ecosystem == "java"
        assert root.manifest_path == "pom.xml"

    def test_multi_csproj_dotnet_solution_yields_one_root_per_project(self, tmp_path):
        (tmp_path / "src" / "Widget.Core").mkdir(parents=True)
        (tmp_path / "src" / "Widget.Core" / "Widget.Core.csproj").write_text(
            "<Project/>", encoding="utf-8"
        )
        (tmp_path / "src" / "Widget.Cli").mkdir(parents=True)
        (tmp_path / "src" / "Widget.Cli" / "Widget.Cli.csproj").write_text(
            "<Project/>", encoding="utf-8"
        )

        profile = build_profile("acme/widget", tmp_path)

        paths = {root.path for root in profile.package_roots}
        assert paths == {
            str(Path("src") / "Widget.Core"),
            str(Path("src") / "Widget.Cli"),
        }
        assert all(root.ecosystem == "net" for root in profile.package_roots)

    def test_multi_module_maven_yields_one_root_per_module(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "module-a").mkdir()
        (tmp_path / "module-a" / "pom.xml").write_text("<project/>", encoding="utf-8")

        profile = build_profile("acme/widget", tmp_path)

        assert len(profile.package_roots) == 2
        paths = {root.path for root in profile.package_roots}
        assert paths == {".", "module-a"}

    def test_no_manifests_yields_no_package_roots(self, tmp_path):
        profile = build_profile("acme/widget", tmp_path)
        assert profile.package_roots == []
