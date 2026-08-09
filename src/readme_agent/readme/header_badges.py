"""Render only factual, applicable README trust badges."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from readme_agent.facts.render_views import ecosystem_display_label
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.header_badge_targets import (
    badge_target_is_already_used,
    verified_compatibility_badge_signal,
)
from readme_agent.readme.header_visual_models import ReadmeBadgeV1, safe_mermaid_label
from readme_agent.readme.license_location import repository_license_path

_ACCEPTED_STATES = {"verified", "policy_approved"}


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    try:
        fact = facts.selected_fact(field)
    except KeyError:
        return None
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    return fact


def _shield(label: str, value: str, color: str) -> str:
    encoded_label = quote(label.replace("-", "--"), safe="")
    encoded_value = quote(value.replace("-", "--"), safe="")
    return f"https://img.shields.io/badge/{encoded_label}-{encoded_value}-{color}"


def _badge(
    badge_id: str,
    kind: Literal[
        "version",
        "package",
        "download",
        "platform",
        "build",
        "source",
        "license",
        "contributors",
    ],
    label: str,
    value: str,
    color: str,
    fact_ids: list[str],
    *,
    target_url: str | None = None,
    image_url: str | None = None,
    alt_text: str | None = None,
) -> ReadmeBadgeV1:
    return ReadmeBadgeV1(
        badge_id=badge_id,
        kind=kind,
        alt_text=alt_text or f"{label}: {value}",
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


def _source_build_manifest_coordinate(
    identity_value: dict,
    coordinate_rows: list[dict],
) -> dict | None:
    manifest_names = identity_value.get("manifest_names")
    if not isinstance(manifest_names, list):
        return None
    return next(
        (
            row
            for name in manifest_names
            for row in coordinate_rows
            if str(name).strip() and _coordinate_matches({"name": str(name).strip()}, row)
        ),
        None,
    )


def render_readme_badges(facts: ProductFactsV2) -> list[ReadmeBadgeV1]:
    """Return one consistent row of applicable, fact-backed trust badges."""

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

    identity = _accepted(facts, "product.identity")
    identity_value = identity.value if identity and isinstance(identity.value, dict) else {}
    coordinate_fact, coordinate_rows = _coordinate_rows(facts)
    if (
        acquisition is not None
        and method == "source_build"
        and value.get("outcome") == "SOURCE_BUILD_VERIFIED"
        and value.get("truth_eligible") is True
    ):
        manifest_coordinate = _source_build_manifest_coordinate(identity_value, coordinate_rows)
        version, version_fact_ids = (
            _verified_version(facts, manifest_coordinate)
            if manifest_coordinate is not None
            else (None, [])
        )
        if version and coordinate_fact is not None:
            repository = str(identity_value.get("repository") or facts.org_repo).strip()
            revision = str(value.get("source_revision") or acquisition.source.source_revision or "")
            target = (
                f"https://github.com/{repository}/tree/{quote(revision, safe='')}"
                if len(repository.split("/")) == 2 and revision
                else None
            )
            badges.append(
                _badge(
                    "version",
                    "version",
                    "Version",
                    version,
                    "blue",
                    [acquisition.fact_id, *version_fact_ids],
                    target_url=target,
                )
            )
    ecosystem = str(identity_value.get("ecosystem") or identity_value.get("platform") or "").strip()
    ecosystem_label = ecosystem_display_label(ecosystem)
    if identity is not None and ecosystem:
        if method == "pypi" and coordinate.get("name"):
            package = quote(str(coordinate["name"]), safe="")
            package_target = f"https://pypi.org/project/{package}/"
            badges.append(
                _badge(
                    "platform",
                    "platform",
                    "Python versions",
                    ecosystem_label,
                    "blue",
                    [identity.fact_id, acquisition.fact_id] if acquisition else [identity.fact_id],
                    target_url=(
                        None
                        if badge_target_is_already_used(
                            (badge.target_url for badge in badges), package_target
                        )
                        else package_target
                    ),
                    image_url=f"https://img.shields.io/pypi/pyversions/{package}.svg",
                    alt_text="Python versions",
                )
            )
        else:
            badges.append(
                _badge(
                    "platform",
                    "platform",
                    "Platform",
                    ecosystem_label,
                    "blue",
                    [identity.fact_id],
                )
            )

    compatibility = verified_compatibility_badge_signal(facts)
    if compatibility is not None:
        compatibility_value, compatibility_fact_ids = compatibility
        badges.append(
            _badge(
                "compatibility",
                "platform",
                "Requires",
                compatibility_value,
                "blue",
                compatibility_fact_ids,
            )
        )

    ci = _accepted(facts, "repository.ci")
    ci_value = ci.value if ci is not None and isinstance(ci.value, dict) else {}
    workflow_path = str(ci_value.get("path") or "").strip()
    repository = str(identity_value.get("repository") or facts.org_repo).strip()
    if (
        ci is not None
        and identity is not None
        and compatibility is None
        and workflow_path
        and len(repository.split("/")) == 2
    ):
        workflow_name = workflow_path.rsplit("/", 1)[-1]
        workflow_url = f"https://github.com/{repository}/actions/workflows/{quote(workflow_name)}"
        badges.append(
            _badge(
                "build",
                "build",
                "Build",
                "GitHub Actions",
                "blue",
                [identity.fact_id, ci.fact_id],
                target_url=workflow_url,
                image_url=workflow_url + "/badge.svg",
            )
        )
    elif (
        acquisition is not None
        and identity is not None
        and value.get("outcome") in {"REGISTRY_VERIFIED", "SOURCE_BUILD_VERIFIED"}
        and len(repository.split("/")) == 2
    ):
        revision = str(value.get("source_revision") or acquisition.source.source_revision or "")
        if revision:
            source_badge = _badge(
                "source",
                "source",
                "Repository",
                "Source",
                "blue",
                [identity.fact_id],
                target_url=f"https://github.com/{repository}/tree/{quote(revision, safe='')}",
            )
            if (
                not badge_target_is_already_used(
                    (badge.target_url for badge in badges), source_badge.target_url
                )
                and compatibility is None
            ):
                badges.append(source_badge)

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
                target_url=repository_license_path(license_fact),
            )
        )
    if identity is not None and len(repository.split("/")) == 2:
        badges.append(
            _badge(
                "contributors",
                "contributors",
                "Contributors",
                repository,
                "blue",
                [identity.fact_id],
                target_url=f"https://github.com/{repository}/graphs/contributors",
                image_url=f"https://img.shields.io/github/contributors/{repository}.svg",
            )
        )
    return badges


_BANNER_URL_PREFIX = "https://products.aspose.org/media/"
_BANNER_PROBE_CACHE: dict[str, bool] = {}


def _banner_url_exists(url: str) -> bool:
    """HEAD (GET fallback) the banner once per family/platform per process."""

    import os

    if os.environ.get("README_AGENT_BRAND_BANNER", "").casefold() == "off":
        return False
    cached = _BANNER_PROBE_CACHE.get(url)
    if cached is not None:
        return cached
    import requests

    exists = False
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            exists = True
        elif response.status_code in {403, 405, 501}:
            exists = requests.get(url, timeout=10, stream=True).status_code == 200
    except requests.RequestException:
        exists = False
    _BANNER_PROBE_CACHE[url] = exists
    return exists


def _family_slug_for_org(github_org: str) -> str | None:
    import json
    from pathlib import Path

    path = Path("data/families.json")
    if not path.is_file():
        return None
    for entry in json.loads(path.read_text(encoding="utf-8")):
        if isinstance(entry, dict) and entry.get("github_org") == github_org:
            slug = entry.get("family")
            return str(slug) if slug else None
    return None


def render_brand_banner(
    facts: ProductFactsV2,
    *,
    product_name: str,
    url_exists=None,
) -> str | None:
    """Render the portfolio brand banner only when its image verifiably exists."""

    identity = _accepted(facts, "product.identity")
    if identity is None or not isinstance(identity.value, dict):
        return None
    platform = str(identity.value.get("platform") or "").strip().casefold()
    family = _family_slug_for_org(facts.org_repo.split("/")[0])
    if not platform or not family:
        return None
    url = f"{_BANNER_URL_PREFIX}{family}/{platform}/banner-readme.png"
    probe = url_exists if url_exists is not None else _banner_url_exists
    if not probe(url):
        return None
    return f"![{product_name}]({url})"
