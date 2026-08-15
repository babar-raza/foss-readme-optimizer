"""T4 -- adapted detector logic from the vendored aspose.org factpack builder.

Per this plan's own capability-reuse table (Annex A / §3): the run/state-
machine orchestration in `readme_refresh_run.py` (locking, session identity,
atomic writes) is explicitly **not ported** -- this repo owns its own
equivalent state machinery. Only the individual, mostly-pure `_detect_*`
helper functions are reused, and only by extracting their logic into
standalone functions that take an explicit `data_root: Path` rather than
depending on that module's global, test-injection-only `_repo_root` state
(discovered while probing T4: importing the whole orchestration module pulls
in `session_identity`/`advisory_lock`/`core.fs`, none of which belong here).

**Honest scope**: this covers 4 of the vendored module's 11 `_detect_*`
functions (archetype, SEO keywords, install info, license file) -- the ones
verified self-contained (pure path/JSON logic, no dependency on run-level
orchestration state). The remaining 7
(`_detect_capability_dependencies`, `_detect_enterprise_link`,
`_detect_homepage_link`, `_detect_available_badges`,
`_detect_dependency_claims`, `_detect_dev_test_artifacts`,
`_detect_archetype_entry_raw`) were not extracted this session.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ArchetypeDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    archetype: str
    archetype_basis: str


def detect_archetype(family: str, platform: str, *, data_root: Path) -> ArchetypeDetectionV1:
    """Adapted from `_detect_archetype` (readme_refresh_run.py)."""

    path = data_root / "data" / "diagram_archetypes.json"
    if not path.is_file():
        return ArchetypeDetectionV1(
            archetype="transform", archetype_basis="default (no override entry)"
        )
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        if row.get("family") == family and row.get("platform") == platform:
            return ArchetypeDetectionV1(
                archetype=row["archetype"], archetype_basis=row.get("evidence", "")
            )
    return ArchetypeDetectionV1(
        archetype="transform", archetype_basis="default (no override entry)"
    )


class SeoKeywordsDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    keywords: tuple[str, ...]
    source_path: str | None
    entry_found: bool


def detect_seo_keywords(family: str, platform: str, *, data_root: Path) -> SeoKeywordsDetectionV1:
    """Adapted from `_detect_seo_keywords` (readme_refresh_run.py)."""

    path = data_root / "keywords" / f"{family}.json"
    if not path.is_file():
        return SeoKeywordsDetectionV1(keywords=(), source_path=None, entry_found=False)
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return SeoKeywordsDetectionV1(keywords=(), source_path=None, entry_found=False)
    platform_source = f"content/products.aspose.org/en/{family}/{platform}/_index.md"
    family_source = f"content/products.aspose.org/en/{family}/_index.md"
    platform_entry = None
    family_entry = None
    for entry in entries:
        source_path = entry.get("sourcePath")
        if source_path == platform_source:
            platform_entry = entry
        elif source_path == family_source:
            family_entry = entry
    chosen = platform_entry or family_entry
    if chosen is None:
        return SeoKeywordsDetectionV1(keywords=(), source_path=None, entry_found=False)
    return SeoKeywordsDetectionV1(
        keywords=tuple(chosen.get("keywords", [])),
        source_path=chosen.get("sourcePath"),
        entry_found=True,
    )


class InstallInfoDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    registry_type: str | None = None
    # The real data (verified against data/imported/data/package_registry.json,
    # not assumed from the vendored code's untyped dict) is itself a structured
    # object (group_id/artifact_id/version/repo_sha for Maven, etc.), not a
    # scalar -- kept as dict[str, Any] rather than over-fitting one registry
    # type's shape.
    candidate: dict | None = None
    published: bool = False
    fallback_text_required: bool = False


def detect_install_info(family: str, platform: str, *, data_root: Path) -> InstallInfoDetectionV1:
    """Adapted from `_detect_install_info` (readme_refresh_run.py)."""

    path = data_root / "data" / "package_registry.json"
    if not path.is_file():
        return InstallInfoDetectionV1(source="package_registry_missing")
    registry = json.loads(path.read_text(encoding="utf-8"))
    family_entry = registry.get(family, {})
    platform_entry = family_entry.get(platform) if isinstance(family_entry, dict) else None
    if not platform_entry:
        return InstallInfoDetectionV1(
            source="no_package_registry_entry", fallback_text_required=True
        )
    verification = platform_entry.get("verification", {})
    published = bool(verification.get("published", False))
    return InstallInfoDetectionV1(
        source="package_registry.json",
        registry_type=platform_entry.get("registry_type"),
        candidate=platform_entry.get("candidate"),
        published=published,
        fallback_text_required=not published,
    )


class LicenseFileDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str


def detect_license_file(clone_cache: Path) -> LicenseFileDetectionV1 | None:
    """Adapted from `_detect_license_file` (readme_refresh_run.py). Widened
    match (200-char case-insensitive substring, not a 20-char exact prefix)
    is preserved verbatim from the vendored logic -- it fixed a real
    confirmed defect (TC-HARDEN-20) and this adaptation must not regress it.
    """

    if not clone_cache.is_dir():
        return None
    candidates = (
        list(clone_cache.glob("LICENSE*"))
        + list(clone_cache.glob("*/LICENSE*"))
        + list(clone_cache.glob("license/LICENSE*"))
    )
    for candidate in candidates:
        if candidate.is_file():
            try:
                head = candidate.read_text(encoding="utf-8", errors="ignore")[:200]
            except OSError:
                continue
            if "mit license" in head.lower():
                return LicenseFileDetectionV1(
                    relative_path=str(candidate.relative_to(clone_cache)).replace("\\", "/")
                )
    return None


__all__ = [
    "ArchetypeDetectionV1",
    "InstallInfoDetectionV1",
    "LicenseFileDetectionV1",
    "SeoKeywordsDetectionV1",
    "detect_archetype",
    "detect_install_info",
    "detect_license_file",
    "detect_seo_keywords",
]
