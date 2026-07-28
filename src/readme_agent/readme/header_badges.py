"""Render only factual, applicable README trust badges."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.header_visual_models import ReadmeBadgeV1, safe_mermaid_label

_ACCEPTED_STATES = {"verified", "policy_approved"}


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact = facts.selected_fact(field)
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    return fact


def _shield(label: str, value: str, color: str) -> str:
    encoded_label = quote(label.replace("-", "--"), safe="")
    encoded_value = quote(value.replace("-", "--"), safe="")
    return f"https://img.shields.io/badge/{encoded_label}-{encoded_value}-{color}"


def _badge(
    badge_id: str,
    kind: Literal["version", "package", "download", "license"],
    label: str,
    value: str,
    color: str,
    fact_ids: list[str],
    *,
    target_url: str | None = None,
    image_url: str | None = None,
) -> ReadmeBadgeV1:
    return ReadmeBadgeV1(
        badge_id=badge_id,
        kind=kind,
        alt_text=f"{label}: {value}",
        image_url=image_url or _shield(label, value, color),
        target_url=target_url,
        fact_ids=fact_ids,
    )


def _coordinate_rows(facts: ProductFactsV2) -> tuple[FactRecordV2 | None, list[dict]]:
    coordinate_fact = _accepted(facts, "installation.coordinates")
    if coordinate_fact is None:
        return None, []
    value = coordinate_fact.value
    rows = value if isinstance(value, list) else [value]
    return coordinate_fact, [row for row in rows if isinstance(row, dict)]


def _coordinate_matches(acquired: dict, manifest: dict) -> bool:
    acquired_name = str(acquired.get("name") or "").strip().casefold()
    manifest_name = str(manifest.get("name") or "").strip().casefold()
    if acquired_name and manifest_name:
        return acquired_name == manifest_name
    acquired_group = str(acquired.get("group_id") or "").strip().casefold()
    acquired_artifact = str(acquired.get("artifact_id") or "").strip().casefold()
    manifest_group = str(manifest.get("group_id") or "").strip().casefold()
    manifest_artifact = str(manifest.get("artifact_id") or "").strip().casefold()
    return bool(
        acquired_group
        and acquired_artifact
        and acquired_group == manifest_group
        and acquired_artifact == manifest_artifact
    )


def _verified_version(
    facts: ProductFactsV2,
    acquired_coordinate: dict,
) -> tuple[str | None, list[str]]:
    coordinate_fact, coordinate_rows = _coordinate_rows(facts)
    matched_coordinate = next(
        (row for row in coordinate_rows if _coordinate_matches(acquired_coordinate, row)),
        None,
    )
    if coordinate_fact is None or matched_coordinate is None:
        return None, []
    release = _accepted(facts, "release.state")
    if release is None:
        return None, []
    release_rows = release.value if isinstance(release.value, list) else [release.value]
    coordinate_path = str(matched_coordinate.get("path") or "")
    matched_release = next(
        (
            row
            for row in release_rows
            if isinstance(row, dict)
            and (
                not coordinate_path
                or str(row.get("path") or "") == coordinate_path
                or len(release_rows) == 1
            )
        ),
        None,
    )
    version = str((matched_release or {}).get("version") or "").strip()
    if not version or version.casefold() == "unknown":
        return None, []
    return version, [coordinate_fact.fact_id, release.fact_id]


def _package_details(method: str, coordinate: dict) -> tuple[str, str, str] | None:
    name = str(coordinate.get("name") or "").strip()
    if method == "nuget" and name:
        return (
            "NuGet",
            f"https://img.shields.io/nuget/v/{quote(name, safe='')}.svg?label=NuGet",
            f"https://www.nuget.org/packages/{quote(name, safe='')}",
        )
    if method == "pypi" and name:
        return (
            "PyPI",
            f"https://img.shields.io/pypi/v/{quote(name, safe='')}.svg?label=PyPI",
            f"https://pypi.org/project/{quote(name, safe='')}/",
        )
    if method == "npm" and name:
        return (
            "npm",
            f"https://img.shields.io/npm/v/{quote(name, safe='@/')}.svg?label=npm",
            f"https://www.npmjs.com/package/{quote(name, safe='@/')}",
        )
    if method == "crates_io" and name:
        return (
            "crates.io",
            f"https://img.shields.io/crates/v/{quote(name, safe='')}.svg",
            f"https://crates.io/crates/{quote(name, safe='')}",
        )
    if method == "go_proxy" and name:
        return (
            "Go Reference",
            f"https://pkg.go.dev/badge/{quote(name, safe='/')}.svg",
            f"https://pkg.go.dev/{quote(name, safe='/')}",
        )
    group = str(coordinate.get("group_id") or "").strip()
    artifact = str(coordinate.get("artifact_id") or "").strip()
    if method == "maven_central" and group and artifact:
        return (
            "Maven Central",
            (
                f"https://img.shields.io/maven-central/v/{quote(group, safe='.')}/"
                f"{quote(artifact, safe='')}.svg?label=Maven%20Central"
            ),
            (
                f"https://central.sonatype.com/artifact/{quote(group, safe='.')}/"
                f"{quote(artifact, safe='')}"
            ),
        )
    return None


def _package_label(method: str, coordinate: dict) -> str | None:
    if method == "maven_central":
        group = str(coordinate.get("group_id") or "").strip()
        artifact = str(coordinate.get("artifact_id") or "").strip()
        return f"{group}:{artifact}" if group and artifact else None
    name = str(coordinate.get("name") or "").strip()
    return name or None


def render_readme_badges(facts: ProductFactsV2) -> list[ReadmeBadgeV1]:
    """Return only applicable package/version and license badges."""

    badges: list[ReadmeBadgeV1] = []
    acquisition = _accepted(facts, "installation.verified_acquisition")
    value = acquisition.value if acquisition and isinstance(acquisition.value, dict) else {}
    method = str(value.get("method") or "")
    coordinate = value.get("coordinate")
    coordinate = coordinate if isinstance(coordinate, dict) else {}
    package_name = _package_label(method, coordinate)
    package_details = _package_details(method, coordinate)
    if (
        acquisition is not None
        and value.get("outcome") == "REGISTRY_VERIFIED"
        and package_name
        and package_details
    ):
        package_label, package_image, package_target = package_details
        badges.append(
            _badge(
                "package",
                "package",
                package_label,
                package_name,
                "brightgreen",
                [acquisition.fact_id],
                target_url=package_target,
                image_url=package_image,
            )
        )
        version, version_fact_ids = _verified_version(facts, coordinate)
        if version is not None:
            badges.append(
                _badge(
                    "version",
                    "version",
                    "Version",
                    version,
                    "blue",
                    [acquisition.fact_id, *version_fact_ids],
                    target_url=package_target,
                )
            )

    license_fact = _accepted(facts, "product.license")
    license_name = safe_mermaid_label(license_fact.value) if license_fact is not None else None
    if license_fact is not None and license_name:
        badges.append(
            _badge(
                "license",
                "license",
                "License",
                license_name,
                "blue",
                [license_fact.fact_id],
                target_url="LICENSE",
            )
        )
    return badges
