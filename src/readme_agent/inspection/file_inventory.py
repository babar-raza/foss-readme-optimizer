"""File inventory scan: README / LICENSE / manifest presence, no LLM.

Case-insensitive matching is deliberate, not incidental: the real registry
repos disagree on casing (LICENSE in 3D/PDF, License in Cells) and NTFS's
case-insensitive filesystem would silently mask a bug here that surfaces the
moment this runs on a Linux CI runner.
"""

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from readme_agent.ecosystems.registry import known_manifest_globs

_README_NAMES = {"readme.md", "readme", "readme.rst", "readme.txt"}
_LICENSE_NAMES = {"license", "license.txt", "license.md", "copying", "license.rst"}

# Community-file control class (decision #19: repository-file managed).
# Root-only, matching README/LICENSE's own base lookup -- a full presence/
# quality audit including .github/ subdirectory conventions is Phase 23's job,
# not this scan's. Populated here only so a content-level fingerprint
# (readme/facts.py::compute_tracked_content_hash) has something concrete and
# case-insensitive-safe to hash for each tracked surface.
_COMMUNITY_FILE_NAMES: dict[str, set[str]] = {
    "CONTRIBUTING": {"contributing.md", "contributing", "contributing.txt", "contributing.rst"},
    "CODE_OF_CONDUCT": {
        "code_of_conduct.md",
        "code_of_conduct",
        "code_of_conduct.txt",
        "code_of_conduct.rst",
    },
    "SECURITY": {"security.md", "security", "security.txt", "security.rst"},
    "SUPPORT": {"support.md", "support", "support.txt", "support.rst"},
}

# Directories never worth descending into for manifest detection -- skipping
# them is both a correctness improvement (a vendored/build-output pom.xml or
# package.json is not the repo's own manifest) and the main performance lever
# for _find_manifest_paths() on a large real repo.
_NOISE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
    "target",
}


@dataclass
class FileInventory:
    readme_path: Path | None
    license_path: Path | None
    manifest_paths: dict[str, Path] = field(default_factory=dict)
    community_paths: dict[str, Path] = field(default_factory=dict)


def _find_case_insensitive(directory: Path, candidate_names: set[str]) -> Path | None:
    if not directory.is_dir():
        return None
    for entry in directory.iterdir():
        if entry.is_file() and entry.name.lower() in candidate_names:
            return entry
    return None


def _find_manifest_paths(repo_path: Path) -> dict[str, Path]:
    """One path per platform -- the first candidate pattern that matches, in
    priority order (Wave 3: multi-ecosystem detection, data-driven from
    ecosystems.registry.known_manifest_globs() -- a third platform later is a
    new registry entry, never a new branch here).

    Hardened by the full-registry survey (Wave 3 follow-up, 2026-07-19): a
    root-only check missed every real repo whose manifest lives in a
    subdirectory (`src/Foo/Foo.csproj`, `Aspose.Cells.Foss.Cpp/CMakeLists.txt`
    -- a common, not edge-case, layout in this project's own registry, not
    just for .NET). Searches the whole tree in **one** bounded `os.walk`
    (not one `rglob` per pattern -- N separate full-tree walks on a large
    repo, most of which don't match, was measured taking 173s on one real
    repo during the survey) skipping common noise directories. Not
    necessarily the *shallowest* match for a given pattern -- the first one
    `os.walk` encounters -- an accepted, documented simplification; the
    ecosystem parser that actually reads the file (e.g. `dotnet.py`'s own
    shallowest-of-up-to-20 selection) remains the source of truth for which
    exact file gets parsed when more precision matters there.
    """
    if not repo_path.is_dir():
        return {}
    globs = known_manifest_globs()
    remaining = {
        (ecosystem, pattern) for ecosystem, patterns in globs.items() for pattern in patterns
    }
    candidates: dict[tuple[str, str], Path] = {}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _NOISE_DIRS]
        for filename in files:
            for ecosystem, pattern in list(remaining):
                if fnmatch.fnmatch(filename, pattern):
                    candidates[(ecosystem, pattern)] = Path(root) / filename
                    remaining.discard((ecosystem, pattern))
        if not remaining:
            break

    found: dict[str, Path] = {}
    for ecosystem, patterns in globs.items():
        for pattern in patterns:
            if (ecosystem, pattern) in candidates:
                found[ecosystem] = candidates[(ecosystem, pattern)]
                break
    return found


def scan(repo_path: Path) -> FileInventory:
    readme_path = _find_case_insensitive(repo_path, _README_NAMES)

    license_path = _find_case_insensitive(repo_path, _LICENSE_NAMES)
    if license_path is None:
        # e.g. aspose-cells-foss's real repos: License/LICENSE.txt
        for entry in repo_path.iterdir() if repo_path.is_dir() else []:
            if entry.is_dir() and entry.name.lower() == "license":
                license_path = _find_case_insensitive(entry, _LICENSE_NAMES)
                if license_path:
                    break

    manifest_paths = _find_manifest_paths(repo_path)

    community_paths: dict[str, Path] = {}
    for canonical_name, candidate_names in _COMMUNITY_FILE_NAMES.items():
        found = _find_case_insensitive(repo_path, candidate_names)
        if found is not None:
            community_paths[canonical_name] = found

    return FileInventory(
        readme_path=readme_path,
        license_path=license_path,
        manifest_paths=manifest_paths,
        community_paths=community_paths,
    )
