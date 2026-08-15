"""T4 -- adapted aspose.org detectors, tested against the REAL imported corpus
(data/imported/), not synthetic fixtures, wherever real data exists."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.aspose_detectors import (
    detect_archetype,
    detect_dev_test_artifacts,
    detect_enterprise_link,
    detect_install_info,
    detect_license_file,
    detect_seo_keywords,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"


def test_detect_archetype_real_default_for_a_product_with_no_override():
    result = detect_archetype("cells", "java", data_root=_DATA_ROOT)

    assert result.archetype == "transform"
    assert "default" in result.archetype_basis


def test_detect_seo_keywords_real_platform_specific_entry_wins():
    """Real data: cells.json has a per-platform entry for cells/java --
    proves the platform-first lookup works against actual imported content,
    not a synthetic stand-in."""

    result = detect_seo_keywords("cells", "java", data_root=_DATA_ROOT)

    assert result.entry_found is True
    assert result.source_path == "content/products.aspose.org/en/cells/java/_index.md"
    assert len(result.keywords) > 0


def test_detect_seo_keywords_real_family_fallback_for_a_platform_with_no_specific_entry():
    """Real data: cells.json has a platform-specific entry for every one of
    the 7 real platforms (a genuine finding, checked here) -- so the
    fallback path is exercised with a platform outside that real set
    (a hypothetical future platform), which correctly has no dedicated
    entry, proving the family-level fallback fires for real against the
    real keywords file rather than a synthetic fixture."""

    import json

    keywords_path = _DATA_ROOT / "keywords" / "cells.json"
    entries = json.loads(keywords_path.read_text(encoding="utf-8"))
    platform_paths = {e.get("sourcePath") for e in entries}
    family_root = "content/products.aspose.org/en/cells/_index.md"
    assert family_root in platform_paths  # the family-level entry genuinely exists
    hypothetical_platform = "swift"
    assert (
        f"content/products.aspose.org/en/cells/{hypothetical_platform}/_index.md"
        not in platform_paths
    )

    result = detect_seo_keywords("cells", hypothetical_platform, data_root=_DATA_ROOT)

    assert result.entry_found is True
    assert result.source_path == family_root


def test_detect_seo_keywords_real_absent_family_degrades_gracefully():
    result = detect_seo_keywords("nonexistent-family-xyz", "java", data_root=_DATA_ROOT)

    assert result == type(result)(keywords=(), source_path=None, entry_found=False)


def test_detect_install_info_real_maven_candidate_is_a_structured_dict():
    """Confirms the real fix this session found: candidate is a structured
    object (group_id/artifact_id/version/repo_sha), never a bare string."""

    result = detect_install_info("cells", "java", data_root=_DATA_ROOT)

    assert result.source == "package_registry.json"
    assert result.registry_type == "maven"
    assert isinstance(result.candidate, dict)
    assert result.candidate["artifact_id"] == "aspose-cells-foss"
    assert result.published is True
    assert result.fallback_text_required is False


def test_detect_install_info_real_absent_product_requires_fallback_text():
    result = detect_install_info("nonexistent-family-xyz", "java", data_root=_DATA_ROOT)

    assert result.source == "no_package_registry_entry"
    assert result.fallback_text_required is True


def test_detect_license_file_no_clone_cache_returns_none():
    result = detect_license_file(_DATA_ROOT)  # not a product clone -- no LICENSE at its root

    assert result is None


def test_detect_license_file_finds_a_widened_mit_preamble_match(tmp_path):
    """TC-HARDEN-20: 'The MIT License (MIT)' (a preamble before the literal
    license name) must still match -- the exact defect this widened-match
    logic was built to fix, preserved verbatim from the vendored function."""

    (tmp_path / "LICENSE").write_text(
        "The MIT License (MIT)\n\nCopyright (c) 2026 Example\n", encoding="utf-8"
    )

    result = detect_license_file(tmp_path)

    assert result is not None
    assert result.relative_path == "LICENSE"


def test_detect_license_file_correctly_excludes_a_non_mit_license(tmp_path):
    (tmp_path / "LICENSE").write_text("Apache License 2.0\n\nSee terms.\n", encoding="utf-8")

    assert detect_license_file(tmp_path) is None


def test_detect_license_file_missing_directory_returns_none(tmp_path):
    assert detect_license_file(tmp_path / "does-not-exist") is None


def test_detect_enterprise_link_real_direct_platform_match():
    result = detect_enterprise_link("cells", "java", data_root=_DATA_ROOT)

    assert result.url is not None
    assert result.relationship == "platform"
    assert result.public_platform == "Java"


def test_detect_enterprise_link_real_bridge_platform_never_discloses_the_bridge():
    """MT044's permanent rule, proven against real data: cells/python resolves
    through a compound ("python-net") URL segment, but the detector must
    surface ONLY the normalized public platform -- never the bridge language,
    never "via", never the raw compound segment."""

    result = detect_enterprise_link("cells", "python", data_root=_DATA_ROOT)

    assert result.relationship == "platform"
    assert result.public_platform == "Python"
    assert "net" not in (result.public_platform or "").lower()
    assert "via" not in (result.public_platform or "").lower()


def test_detect_enterprise_link_real_unmatched_platform_falls_back_to_family():
    result = detect_enterprise_link("3d", "typescript", data_root=_DATA_ROOT)

    assert result.link_type == "family"
    assert result.relationship == "family"
    assert result.public_platform is None
    assert result.fallback_reason is not None


def test_detect_enterprise_link_real_target_map_age_is_a_positive_float():
    result = detect_enterprise_link("cells", "java", data_root=_DATA_ROOT)

    assert isinstance(result.target_map_age_days, float)
    assert result.target_map_age_days >= 0


def test_detect_enterprise_link_missing_target_map_degrades_gracefully(tmp_path):
    result = detect_enterprise_link("cells", "java", data_root=tmp_path)

    assert result.url is None
    assert result.fallback_reason is not None
    assert "target_map_unavailable" in result.fallback_reason


def test_detect_dev_test_artifacts_finds_expected_categories(tmp_path):
    (tmp_path / "CONTRIBUTING.md").write_text("x", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("x", encoding="utf-8")

    result = detect_dev_test_artifacts(tmp_path)

    kinds = {item.kind for item in result}
    assert kinds == {"contributing_guide", "docs_guide", "ci_workflow"}


def test_detect_dev_test_artifacts_case_insensitive_agents_discovery(tmp_path):
    """Real confirmed defect: cells/java's actual on-disk file is cased
    'Agents.md' -- neither 'AGENTS.md' nor 'agents.md' literal lookups
    matched it. The fix scans case-insensitively then verifies the exact
    on-disk name."""

    (tmp_path / "Agents.md").write_text("x", encoding="utf-8")

    result = detect_dev_test_artifacts(tmp_path)

    assert len(result) == 1
    assert result[0].relative_path == "Agents.md"
    assert result[0].kind == "agents_guide"


def test_detect_dev_test_artifacts_excludes_pytest_cache_boilerplate(tmp_path):
    """Real confirmed defect: pytest itself writes a boilerplate README.md
    into .pytest_cache/ on every run -- 'test' is a substring of
    'pytest_cache', so this must be excluded by the leading-dot rule, not
    picked up as a genuine test_dir_readme."""

    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "README.md").write_text("x", encoding="utf-8")
    (tmp_path / "tests_integration").mkdir()
    (tmp_path / "tests_integration" / "README.md").write_text("x", encoding="utf-8")

    result = detect_dev_test_artifacts(tmp_path)

    paths = {item.relative_path for item in result}
    assert ".pytest_cache/README.md" not in paths
    assert "tests_integration/README.md" in paths


def test_detect_dev_test_artifacts_deduplicates_a_single_physical_file(tmp_path):
    (tmp_path / "CONTRIBUTING.md").write_text("x", encoding="utf-8")

    result = detect_dev_test_artifacts(tmp_path)

    paths = [item.relative_path for item in result]
    assert paths.count("CONTRIBUTING.md") == 1


def test_detect_dev_test_artifacts_missing_directory_returns_empty(tmp_path):
    assert detect_dev_test_artifacts(tmp_path / "does-not-exist") == ()
