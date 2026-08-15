"""T4 -- adapted aspose.org detectors, tested against the REAL imported corpus
(data/imported/), not synthetic fixtures, wherever real data exists."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.aspose_detectors import (
    detect_archetype,
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
