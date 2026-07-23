"""Repository-profile compatibility vocabulary and matching."""

from __future__ import annotations

from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.errors import ConfigError
from readme_agent.profile.schema import RepositoryProfile

_ECOSYSTEM_COMPATIBILITY: dict[str, dict[str, frozenset[str]]] = {
    "java": {
        "build_systems": frozenset({"maven"}),
        "package_managers": frozenset({"maven"}),
        "registries": frozenset({"maven_central"}),
    },
    "python": {
        "build_systems": frozenset({"pip"}),
        "package_managers": frozenset({"pip"}),
        "registries": frozenset({"pypi"}),
    },
    "typescript": {
        "build_systems": frozenset({"npm"}),
        "package_managers": frozenset({"npm"}),
        "registries": frozenset({"npm_registry"}),
    },
    "net": {
        "build_systems": frozenset({"msbuild"}),
        "package_managers": frozenset({"nuget"}),
        "registries": frozenset({"nuget"}),
    },
    "go": {
        "build_systems": frozenset({"go_modules"}),
        "package_managers": frozenset({"go_modules"}),
        "registries": frozenset({"go_proxy"}),
    },
    "cpp": {
        "build_systems": frozenset(),
        "package_managers": frozenset(),
        "registries": frozenset(),
    },
}


def _known_values(category: str) -> frozenset[str]:
    return frozenset(
        value for ecosystem in _ECOSYSTEM_COMPATIBILITY.values() for value in ecosystem[category]
    )


def validate_compatibility_declarations(manifest: CapabilityManifest) -> None:
    """Reject compatibility vocabulary that no repository profile can satisfy."""

    declarations = {
        "build_systems": manifest.supported_build_systems,
        "package_managers": manifest.supported_package_managers,
        "registries": manifest.supported_registries,
    }
    for category, values in declarations.items():
        unknown = set(values) - _known_values(category)
        if unknown:
            raise ConfigError(
                f"{manifest.capability_id!r} declares unknown supported_{category}: "
                f"{sorted(unknown)}"
            )


def is_compatible(manifest: CapabilityManifest, profile: RepositoryProfile) -> bool:
    """Return whether every declared compatibility axis matches the repository profile."""

    ecosystems = {detected.ecosystem for detected in profile.detected_ecosystems} | {
        root.ecosystem for root in profile.package_roots
    }
    available = {
        category: frozenset(
            value
            for ecosystem in ecosystems
            for value in _ECOSYSTEM_COMPATIBILITY.get(ecosystem, {}).get(category, ())
        )
        for category in ("build_systems", "package_managers", "registries")
    }
    declarations = {
        "build_systems": set(manifest.supported_build_systems),
        "package_managers": set(manifest.supported_package_managers),
        "registries": set(manifest.supported_registries),
    }
    return all(
        not declared or bool(declared & available[category])
        for category, declared in declarations.items()
    )
