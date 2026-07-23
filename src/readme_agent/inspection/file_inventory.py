"""File inventory scan: README / LICENSE / manifest presence, no LLM.

Case-insensitive matching is deliberate, not incidental: the real registry
repos disagree on casing (LICENSE in 3D/PDF, License in Cells) and NTFS's
case-insensitive filesystem would silently mask a bug here that surfaces the
moment this runs on a Linux CI runner.
"""

import fnmatch
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from readme_agent.ecosystems.registry import known_manifest_globs

_T = TypeVar("_T")

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

# Wave 8.6 (`ORC-003` reversal, `supervisor/specialist_selection.py`): public
# aliases of this module's own root-only name sets, so the specialist-skip
# diff heuristic can match against the same canonical names this scan
# already uses, rather than a second, independently-drifting hardcoded list.
README_FILENAMES: frozenset[str] = frozenset(_README_NAMES)
LICENSE_FILENAMES: frozenset[str] = frozenset(_LICENSE_NAMES)
COMMUNITY_FILENAMES: frozenset[str] = frozenset(
    name for names in _COMMUNITY_FILE_NAMES.values() for name in names
)

# Directories never worth descending into for manifest detection -- skipping
# them is both a correctness improvement (a vendored/build-output pom.xml or
# package.json is not the repo's own manifest) and the main performance lever
# for _find_manifest_paths() on a large real repo. Public (not module-private)
# since inspection/tree_paths.py's git-tree-API scan (decision #40/Part F)
# shares this exact set -- one definition of "noise," not two that could
# silently drift apart.
NOISE_DIRS = {
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

# Circuit breaker, not a correctness guarantee (decision #40/Part B): a
# single-ecosystem repo forces a full-tree walk since most registered
# ecosystems' patterns never resolve (measured ~258s on a real ~1GB/
# 2500-file registry repo, aspose-page-foss). Generous enough that no real
# registry repo observed so far comes close to it -- this only guards
# against a genuinely pathological tree. A walk that stops here is
# indistinguishable in output shape from one that legitimately found
# nothing more, so a genuinely multi-ecosystem *and* enormous repo could
# see a false negative on a secondary ecosystem past this ceiling -- an
# accepted, documented trade-off, not a silent one.
_MAX_FILES_SCANNED = 200_000


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


def resolve_manifest_candidates(filename_and_ref_pairs: Iterable[tuple[str, _T]]) -> dict[str, _T]:
    """One ref per ecosystem -- the first candidate pattern that matches, in
    `known_manifest_globs()` priority order (Wave 3: multi-ecosystem
    detection; a third platform later is a new registry entry, never a new
    branch here). `ref` is opaque to this function (a filesystem `Path` for
    `_find_manifest_paths()`'s `os.walk()`, a tree-relative path string for
    `inspection/tree_paths.py`'s git-tree-API scan, decision #40/Part F) --
    this is the single shared matching rule both traversal strategies call,
    so a manifest glob added to `ecosystems.registry` is honored identically
    by whichever one a caller happens to use, not two copies that could
    silently drift apart. Short-circuits the moment every ecosystem has a
    candidate; callers control how much of `filename_and_ref_pairs` to
    offer (`_find_manifest_paths()`'s own `_MAX_FILES_SCANNED` bound, or the
    git-tree API's own ~100k-entry cap)."""
    globs = known_manifest_globs()
    remaining = {
        (ecosystem, pattern) for ecosystem, patterns in globs.items() for pattern in patterns
    }
    candidates: dict[tuple[str, str], _T] = {}

    for filename, ref in filename_and_ref_pairs:
        for ecosystem, pattern in list(remaining):
            if fnmatch.fnmatch(filename, pattern):
                candidates[(ecosystem, pattern)] = ref
                remaining.discard((ecosystem, pattern))
        if not remaining:
            break

    found: dict[str, _T] = {}
    for ecosystem, patterns in globs.items():
        for pattern in patterns:
            if (ecosystem, pattern) in candidates:
                found[ecosystem] = candidates[(ecosystem, pattern)]
                break
    return found


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

    Also bounded by `_MAX_FILES_SCANNED` (decision #40/Part B): the
    single-walk redesign above still traverses the whole tree whenever most
    registered ecosystems' patterns never resolve, true of any
    single-ecosystem repo (measured ~258s on a real ~1GB/2500-file registry
    repo) -- see `_MAX_FILES_SCANNED`'s own comment for the trade-off.
    """
    if not repo_path.is_dir():
        return {}

    def _bounded_walk() -> Iterable[tuple[str, Path]]:
        files_scanned = 0
        for root, dirs, files in os.walk(repo_path):
            # Wave 13.6 (`DEP-004`): `os.walk()`'s own traversal order is
            # filesystem-dependent, never guaranteed -- found live via a
            # real `act` (Linux/Docker) run reordering this exact walk
            # relative to the same test's own Windows-local result,
            # silently changing which files a `_MAX_FILES_SCANNED`-bounded
            # scan reaches first. Sorting `dirs`/`files` in place makes
            # which manifest a bounded scan finds (or misses) identical
            # across every OS/filesystem this project's own CI or a real
            # pilot repo might be scanned from, not an accident of the host.
            dirs[:] = sorted(d for d in dirs if d not in NOISE_DIRS)
            for filename in sorted(files):
                files_scanned += 1
                yield filename, Path(root) / filename
            if files_scanned >= _MAX_FILES_SCANNED:
                return

    return resolve_manifest_candidates(_bounded_walk())


def find_all_manifest_roots(repo_path: Path) -> list[tuple[str, Path]]:
    """Wave 11.1 (`ECO-004`): every manifest match across the whole tree,
    not just the first per ecosystem -- `resolve_manifest_candidates()`'s
    own docstring already names this exact limitation ("one manifest path
    per ecosystem" as the extent of this project's monorepo support). A
    repository with N independently buildable modules (a multi-module
    Maven/Gradle tree, a multi-`.csproj` .NET solution, an npm/Yarn
    workspace) has N real package roots, not one flattened, potentially
    misleading one.

    Deliberately a separate function from `_find_manifest_paths()`/
    `resolve_manifest_candidates()`, not a change to either: those two stay
    exactly "first match per ecosystem wins" for every existing caller
    (`FileInventory.manifest_paths`, `profile/cached.py`'s git-tree-API
    path) -- changing their return shape would ripple into call sites this
    phase does not need to touch. Reuses the identical bounded-walk/
    `NOISE_DIRS` exclusion those functions already established -- a second,
    independently-drifting traversal rule is exactly what this module's own
    docstring warns against."""
    if not repo_path.is_dir():
        return []

    globs = known_manifest_globs()
    found: list[tuple[str, Path]] = []
    files_scanned = 0
    for root, dirs, files in os.walk(repo_path):
        # Same deterministic-ordering fix as `_find_manifest_paths()`'s own
        # `_bounded_walk()` above -- see that comment for why.
        dirs[:] = sorted(d for d in dirs if d not in NOISE_DIRS)
        for filename in sorted(files):
            files_scanned += 1
            for ecosystem, patterns in globs.items():
                if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns):
                    found.append((ecosystem, Path(root) / filename))
            if files_scanned >= _MAX_FILES_SCANNED:
                return found
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
