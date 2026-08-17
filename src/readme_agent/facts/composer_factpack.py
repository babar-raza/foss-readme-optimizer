"""T4 -- ComposerFactpack: merges this repo's authoritative ProductFactsV2
with the T4-adapted aspose.org detector evidence, plus per-source
staleness/coverage finding surfaces (U7).

`ProductFactsV2` (schema_v2.py) remains the sole authority for every field
in `REQUIRED_PRODUCT_FIELDS`; nothing here re-derives or overrides a
selected fact. `AsposeDetectionBundleV1` supplies additional evidence this
repo's own fact pipeline does not (yet) produce -- archetype, SEO
keywords, enterprise-link classification, dev/test artifacts, capability
dependencies, homepage-link status, and dependency claims -- covering 9 of
the vendored module's 11 `_detect_*` functions (see aspose_detectors.py's
module docstring for the 2 not yet extracted: `_detect_available_badges`,
`_detect_archetype_entry_raw`).

U7 (upstream-defect register): aspose.org worked around unreliable/stale
source data ad hoc, with no systematic per-source staleness or coverage
signal. `assess_source_staleness` gives every consumed source an explicit,
structured finding instead of silent trust. This is advisory only -- per
this plan's freshness model (identity-based, never wall-clock; U11), a
stale-but-content-unchanged source produces the same finding every cycle
and is never itself a regeneration trigger.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_detectors import (
    ArchetypeDetectionV1,
    DependencyClaimsDetectionV1,
    DevTestArtifactV1,
    EnterpriseLinkDetectionV1,
    HomepageLinkDetectionV1,
    InstallInfoDetectionV1,
    LicenseFileDetectionV1,
    SeoKeywordsDetectionV1,
    detect_archetype,
    detect_capability_dependencies,
    detect_dependency_claims,
    detect_dev_test_artifacts,
    detect_enterprise_link,
    detect_homepage_link,
    detect_install_info,
    detect_license_file,
    detect_seo_keywords,
)
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)

# Shared with backlink_targets.STALE_WARN_DAYS (the one existing staleness
# threshold in this codebase, content-provenance-based rather than file-
# mtime-based) so every source in this finding surface is judged against
# one documented, consistent bar rather than several invented ones.
STALE_WARN_DAYS = 14.0


class AsposeDetectionBundleV1(BaseModel):
    """All 9 currently-adapted aspose.org detector outputs for one
    family/platform pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    archetype: ArchetypeDetectionV1
    seo_keywords: SeoKeywordsDetectionV1
    install_info: InstallInfoDetectionV1
    license_file: LicenseFileDetectionV1 | None
    enterprise_link: EnterpriseLinkDetectionV1
    dev_test_artifacts: tuple[DevTestArtifactV1, ...]
    capability_dependencies: tuple[str, ...] | None
    homepage_link: HomepageLinkDetectionV1
    dependency_claims: DependencyClaimsDetectionV1


def build_aspose_detection_bundle(
    family: str, platform: str, *, data_root: Path, clone_cache: Path
) -> AsposeDetectionBundleV1:
    """Run all 9 adapted detectors for one product and aggregate their
    outputs. Each detector already degrades gracefully on missing/absent
    source data (see their individual docstrings); this function adds no
    further fallback logic of its own."""

    return AsposeDetectionBundleV1(
        archetype=detect_archetype(family, platform, data_root=data_root),
        seo_keywords=detect_seo_keywords(family, platform, data_root=data_root),
        install_info=detect_install_info(family, platform, data_root=data_root),
        license_file=detect_license_file(clone_cache),
        enterprise_link=detect_enterprise_link(family, platform, data_root=data_root),
        dev_test_artifacts=detect_dev_test_artifacts(clone_cache),
        capability_dependencies=detect_capability_dependencies(
            family, platform, data_root=data_root
        ),
        homepage_link=detect_homepage_link(family, platform, data_root=data_root),
        dependency_claims=detect_dependency_claims(family, platform, data_root=data_root),
    )


class ComposerFactpack(BaseModel):
    """Merged input for future composition work (T5+): this repo's
    authoritative ProductFactsV2 alongside the T4 aspose.org detector
    evidence, scoped to one family/platform pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str
    platform: str
    product_facts: ProductFactsV2
    aspose_detections: AsposeDetectionBundleV1


def build_composer_factpack(
    family: str,
    platform: str,
    *,
    data_root: Path,
    clone_cache: Path,
    product_facts: ProductFactsV2,
) -> ComposerFactpack:
    """Build a ComposerFactpack for one product, merging the caller-supplied
    (already-resolved) ProductFactsV2 with a fresh run of all 9 adapted
    aspose.org detectors."""

    return ComposerFactpack(
        family=family,
        platform=platform,
        product_facts=product_facts,
        aspose_detections=build_aspose_detection_bundle(
            family, platform, data_root=data_root, clone_cache=clone_cache
        ),
    )


def aspose_fact_records(
    bundle: AsposeDetectionBundleV1, *, family: str, platform: str
) -> list[FactRecordV2]:
    """Project an AsposeDetectionBundleV1 into additional, non-mandatory
    ProductFactsV2 fields (the "aspose.*" namespace), using the extension
    seam `resolution.py::resolve_product_facts()` already documents:
    non-mandatory field families are preserved and selected without
    requiring a schema rewrite. Never overrides a REQUIRED_PRODUCT_FIELDS
    field -- these are supplementary evidence this repo's own fact
    pipeline does not otherwise produce.

    Each detector already degrades gracefully on missing/absent source
    data (see aspose_detectors.py); a field with nothing genuine to say
    (no real data found) is simply omitted here rather than recorded with
    a hollow or default value.
    """

    source = FactSourceV2(
        source_type="approved_documentation",
        location=f"data/imported:{family}/{platform}",
        retrieved_at=datetime.now(UTC).isoformat(),
    )
    records: list[FactRecordV2] = []

    def add(field: str, value, *, verified: bool, surfaces: list[str]) -> None:
        records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field, "aspose-detection"),
                field=field,
                value=value,
                source=source,
                verification_state="verified" if verified else "unverified",
                authoritative_owner="aspose.org",
                confidence=1.0 if verified else 0.4,
                affected_surfaces=surfaces,
            )
        )

    archetype = bundle.archetype
    add(
        "aspose.archetype",
        archetype.archetype,
        verified=not archetype.archetype_basis.startswith("default"),
        surfaces=["readme.header"],
    )

    if bundle.seo_keywords.entry_found and bundle.seo_keywords.keywords:
        add(
            "aspose.seo_keywords",
            list(bundle.seo_keywords.keywords),
            verified=True,
            surfaces=["metadata.topics", "readme.opening"],
        )

    # These three store the detection model's FULL model_dump() (not a
    # hand-picked subset) -- src/readme_agent/validation/aspose_checks_bridge.py
    # (T3) reads these exact fact values back out to feed the vendored check
    # battery, whose functions were extracted directly against this same
    # shape (e.g. install_info["fallback_text_required"],
    # license_file["relative_path"], enterprise_link["relationship"]); a
    # narrower value here would silently starve those checks of real fields.
    install_info = bundle.install_info
    if install_info.source != "package_registry_missing":
        add(
            "aspose.install_info",
            install_info.model_dump(mode="json"),
            verified=install_info.published,
            surfaces=["readme.installation"],
        )

    if bundle.license_file is not None:
        add(
            "aspose.license_file",
            bundle.license_file.model_dump(mode="json"),
            verified=True,
            surfaces=["readme.license"],
        )

    link = bundle.enterprise_link
    if link.url is not None:
        add(
            "aspose.enterprise_link",
            link.model_dump(mode="json"),
            verified=not bool(link.target_map_stale),
            surfaces=["readme.limitations"],
        )

    if bundle.dev_test_artifacts:
        add(
            "aspose.dev_test_artifacts",
            [
                {
                    "relative_path": artifact.relative_path,
                    "kind": artifact.kind,
                    "section": artifact.section,
                }
                for artifact in bundle.dev_test_artifacts
            ],
            verified=True,
            surfaces=["readme.development"],
        )

    if bundle.capability_dependencies:
        add(
            "aspose.capability_dependencies",
            list(bundle.capability_dependencies),
            verified=True,
            surfaces=["readme.api_reference", "readme.capabilities"],
        )

    claims = bundle.dependency_claims
    if claims.claims:
        add(
            "aspose.dependency_claims",
            [dict(claim) for claim in claims.claims],
            verified=claims.repo_sha is not None,
            surfaces=["readme.capabilities"],
        )

    # homepage_link is intentionally never injected: aspose_detectors.py's own
    # docstring documents it always returns verified=False in this repo (the
    # website-content tree was never imported), so it never has anything
    # genuine to contribute.

    return records


class SourceStalenessFindingV1(BaseModel):
    """U7: an informational finding for one source consumed while building
    an AsposeDetectionBundleV1. Advisory only -- never a regeneration
    trigger by itself (see module docstring)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    present: bool
    age_days: float | None
    stale: bool | None
    coverage: Literal["full", "partial", "absent"]
    note: str | None = None


def _file_age_days(path: Path) -> float | None:
    if not path.is_file():
        return None
    return max(0.0, (time.time() - path.stat().st_mtime) / 86400.0)


def _staleness(age_days: float | None) -> bool | None:
    if age_days is None:
        return None
    return age_days > STALE_WARN_DAYS


def assess_source_staleness(
    bundle: AsposeDetectionBundleV1, *, family: str, platform: str, data_root: Path
) -> tuple[SourceStalenessFindingV1, ...]:
    """U7: one finding per source the T4 detector bundle consumes.
    Coverage is derived from each detector's own already-computed result
    (never re-parsed independently), so a finding can never disagree with
    what the detector actually found."""

    findings: list[SourceStalenessFindingV1] = []

    seo_path = data_root / "keywords" / f"{family}.json"
    seo_age = _file_age_days(seo_path)
    findings.append(
        SourceStalenessFindingV1(
            source_id=f"keywords/{family}.json",
            present=seo_path.is_file(),
            age_days=seo_age,
            stale=_staleness(seo_age),
            coverage="full"
            if bundle.seo_keywords.entry_found
            else ("absent" if not seo_path.is_file() else "partial"),
        )
    )

    archetype_path = data_root / "data" / "diagram_archetypes.json"
    archetype_age = _file_age_days(archetype_path)
    is_default = bundle.archetype.archetype_basis.startswith("default")
    findings.append(
        SourceStalenessFindingV1(
            source_id="data/diagram_archetypes.json",
            present=archetype_path.is_file(),
            age_days=archetype_age,
            stale=_staleness(archetype_age),
            coverage="absent"
            if not archetype_path.is_file()
            else ("partial" if is_default else "full"),
        )
    )

    registry_path = data_root / "data" / "package_registry.json"
    registry_age = _file_age_days(registry_path)
    install_source = bundle.install_info.source
    findings.append(
        SourceStalenessFindingV1(
            source_id="data/package_registry.json",
            present=registry_path.is_file(),
            age_days=registry_age,
            stale=_staleness(registry_age),
            coverage="full"
            if install_source == "package_registry.json"
            else ("absent" if install_source == "package_registry_missing" else "partial"),
        )
    )

    link = bundle.enterprise_link
    target_map_missing = bool(
        link.fallback_reason and link.fallback_reason.startswith("target_map_unavailable")
    )
    findings.append(
        SourceStalenessFindingV1(
            source_id="data/aspose_com_targets.json",
            present=not target_map_missing,
            age_days=link.target_map_age_days,
            stale=link.target_map_stale,
            coverage="absent"
            if target_map_missing
            else ("full" if link.url is not None else "partial"),
            note=link.fallback_reason,
        )
    )

    capdep_path = data_root / "data" / "diagram_capability_dependencies.json"
    capdep_age = _file_age_days(capdep_path)
    findings.append(
        SourceStalenessFindingV1(
            source_id="data/diagram_capability_dependencies.json",
            present=capdep_path.is_file(),
            age_days=capdep_age,
            stale=_staleness(capdep_age),
            coverage="absent"
            if not capdep_path.is_file()
            else ("full" if bundle.capability_dependencies is not None else "partial"),
        )
    )

    homepage_path = (
        data_root / "content" / "products.aspose.org" / "en" / family / platform / "_index.md"
    )
    homepage_age = _file_age_days(homepage_path)
    findings.append(
        SourceStalenessFindingV1(
            source_id="content/products.aspose.org/",
            present=bundle.homepage_link.verified,
            age_days=homepage_age,
            stale=_staleness(homepage_age),
            coverage="full" if bundle.homepage_link.verified else "absent",
            note=None
            if bundle.homepage_link.verified
            else "website-content tree not in TD-01's lean-import scope",
        )
    )

    merged_dir = data_root / "knowledge" / family / platform / "merged"
    claims_path = merged_dir / "claims.json"
    claims_age = _file_age_days(claims_path)
    claims = bundle.dependency_claims
    findings.append(
        SourceStalenessFindingV1(
            source_id=f"knowledge/{family}/{platform}/merged/claims.json",
            present=merged_dir.is_dir(),
            age_days=claims_age,
            stale=_staleness(claims_age),
            coverage="absent"
            if not merged_dir.is_dir()
            else ("full" if claims.claims and claims.repo_sha else "partial"),
        )
    )

    return tuple(findings)
