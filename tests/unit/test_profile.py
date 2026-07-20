import pytest
from pydantic import ValidationError

from readme_agent.profile.detector import build_profile
from readme_agent.profile.schema import DetectedEcosystem, RepositoryProfile


class TestSchema:
    def test_repository_profile_defaults(self):
        profile = RepositoryProfile(org_repo="acme/widget")
        assert profile.detected_ecosystems == []
        assert profile.unresolved_manifests == []

    def test_detected_ecosystem_requires_all_fields(self):
        with pytest.raises(ValidationError):
            DetectedEcosystem(ecosystem="java")


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
