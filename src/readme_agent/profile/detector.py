"""build_profile() -- one file_inventory.scan() call, one DetectedEcosystem
per populated manifest_paths entry via the existing parse_manifest dispatch,
plus a separate glob for manifest-shaped files matching no registered
ecosystem (unresolved, recorded not guessed -- ECO-003). One scan, one
source of truth: this does not re-implement manifest detection, it reads
the same inspection/file_inventory.py + ecosystems/registry.py the shipped
pipeline already generalized in this wave.
"""

import fnmatch
from collections.abc import Iterable
from pathlib import Path

from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.inspection import file_inventory
from readme_agent.profile.schema import DetectedEcosystem, RepositoryProfile

# Broad, best-effort scan for "looks like it could be a manifest" -- some
# over-inclusion is expected and acceptable (e.g. tsconfig.json, a lockfile):
# ECO-003 asks for unresolved files to be *recorded*, not for this list to be
# a precise manifest classifier. Known non-manifest filenames are excluded
# explicitly rather than silently, so the exclusion itself is reviewable.
# Public (not module-private): profile/cached.py's git-tree-API path
# (decision #40/Part F) shares this exact rule via
# resolve_unresolved_manifests() below, so a real registry repo's exclusion
# list stays one list, not two that could drift apart.
MANIFEST_SHAPED_GLOBS = ("*.toml", "*.json", "*.xml")
KNOWN_NON_MANIFEST_FILENAMES = {
    "package-lock.json",
    "tsconfig.json",
    ".eslintrc.json",
    # CMake's own companion config file, not a manifest -- found unresolved
    # against a real registry repo by the full-registry survey (2026-07-19).
    "CMakePresets.json",
    "CMakeUserPresets.json",
}


def resolve_unresolved_manifests(
    filenames: Iterable[str], matched_filenames: set[str]
) -> list[str]:
    """Root-level, manifest-shaped filenames (`MANIFEST_SHAPED_GLOBS`) that
    matched no registered ecosystem -- recorded, not guessed (`ECO-003`).
    Shared by `build_profile()`'s filesystem glob and
    `profile/cached.py`'s git-tree-API path (decision #40/Part F) so both
    traversal strategies apply the identical over-inclusion/exclusion rule."""
    unresolved: set[str] = set()
    for filename in filenames:
        if filename in matched_filenames or filename in KNOWN_NON_MANIFEST_FILENAMES:
            continue
        if any(fnmatch.fnmatch(filename, pattern) for pattern in MANIFEST_SHAPED_GLOBS):
            unresolved.add(filename)
    return sorted(unresolved)


def build_profile(org_repo: str, repo_path: Path) -> RepositoryProfile:
    inventory = file_inventory.scan(repo_path)

    detected: list[DetectedEcosystem] = []
    for ecosystem, manifest_path in inventory.manifest_paths.items():
        facts = parse_manifest(ecosystem, repo_path)
        detected.append(
            DetectedEcosystem(
                ecosystem=ecosystem,
                manifest_path=str(manifest_path.relative_to(repo_path)),
                confidence=1.0 if facts else 0.5,
                evidence=(
                    f"found {manifest_path.name}; parsed {len(facts)} field(s)"
                    if facts
                    else f"found {manifest_path.name}; nothing parsed"
                ),
            )
        )

    matched_filenames = {path.name for path in inventory.manifest_paths.values()}
    root_candidates: list[str] = []
    if repo_path.is_dir():
        for pattern in MANIFEST_SHAPED_GLOBS:
            root_candidates.extend(candidate.name for candidate in repo_path.glob(pattern))
    unresolved = resolve_unresolved_manifests(root_candidates, matched_filenames)

    return RepositoryProfile(
        org_repo=org_repo,
        detected_ecosystems=detected,
        unresolved_manifests=unresolved,
    )
