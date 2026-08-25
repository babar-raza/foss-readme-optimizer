"""Collect source-derived CMake configure, build, and test commands."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_PROJECT = re.compile(r"(?m)^\s*project\s*\(\s*([A-Za-z0-9_.\-]+)", re.IGNORECASE)
_ENABLE_TESTING = re.compile(r"(?m)^\s*enable_testing\s*\(\s*\)", re.IGNORECASE)
_ADD_TEST = re.compile(r"(?m)^\s*(?:add_test|gtest_discover_tests)\s*\(", re.IGNORECASE)
_ADD_EXECUTABLE = re.compile(r"(?m)^\s*add_executable\s*\(", re.IGNORECASE)
# A target name may be a literal or a variable reference such as
# `add_executable(${PROJECT_NAME} ...)`; only a literal (or `${PROJECT_NAME}`
# resolved from this manifest's own `project()` call) is reported by name.
_ADD_EXECUTABLE_NAME = re.compile(
    r"(?m)^\s*add_executable\s*\(\s*(\$\{PROJECT_NAME\}|[A-Za-z0-9_.\-]+)", re.IGNORECASE
)
_MINIMUM_REQUIRED = re.compile(
    r"(?m)^\s*cmake_minimum_required\s*\(\s*VERSION\s+([0-9][0-9.]*)", re.IGNORECASE
)
_OPTION = re.compile(
    r"(?m)^\s*option\s*\(\s*([A-Za-z0-9_]+)\s+\"[^\"]*\"\s+(ON|OFF)", re.IGNORECASE
)
_FETCHCONTENT_URL = re.compile(
    # The URL may close the call directly (`URL https://...zip)`), so stop
    # before a closing paren rather than consuming it as part of the URL.
    r"FetchContent_Declare\s*\(\s*([A-Za-z0-9_.\-]+)(?:[^)]*?)URL\s+([^\s)]+)",
    re.IGNORECASE | re.DOTALL,
)
_VERSION_TAG = re.compile(r"/(?:refs/tags/)?(v?[0-9][0-9A-Za-z.\-]*)\.(?:zip|tar\.gz)$")
# A CMake project directory this deep is a vendored/third-party build, not a
# development entry point a repository visitor is expected to run.
_MAX_DEPTH = 2


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_record(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}


def _fetched_dependencies(text: str) -> list[dict[str, str]]:
    """Return each FetchContent dependency whose URL pins an exact version."""

    dependencies: list[dict[str, str]] = []
    for name, url in _FETCHCONTENT_URL.findall(text):
        version = _VERSION_TAG.search(url)
        if version is None:
            continue
        dependencies.append({"name": name, "version": version.group(1), "url": url})
    return sorted(dependencies, key=lambda item: item["name"])


def _project_entry(root: Path, manifest: Path) -> dict[str, object] | None:
    """Describe one CMake project purely from its own manifest text."""

    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    project = _PROJECT.search(text)
    if project is None:
        return None
    directory = manifest.parent
    relative_dir = directory.relative_to(root).as_posix()
    builds_executable = bool(_ADD_EXECUTABLE.search(text))
    executables = sorted(
        {
            project.group(1) if name == "${PROJECT_NAME}" else name
            for name in _ADD_EXECUTABLE_NAME.findall(text)
        }
    )
    # `enable_testing()` alone only turns CTest on; a project without any
    # registered test is not proven to have anything for `ctest` to run.
    runs_tests = bool(_ENABLE_TESTING.search(text)) and bool(_ADD_TEST.search(text))
    if not builds_executable and not runs_tests:
        return None
    minimum = _MINIMUM_REQUIRED.search(text)
    commands = ["cmake -S . -B build", "cmake --build build"]
    if runs_tests:
        commands.append("ctest --test-dir build --output-on-failure")
    entry: dict[str, object] = {
        "kind": "cmake_test_project" if runs_tests else "cmake_build_project",
        "working_directory": relative_dir or ".",
        "commands": commands,
        "command": commands[-1],
        "sources": [_source_record(root, manifest)],
        "evidence_kind": "source_derived",
        "execution_verified": False,
    }
    if minimum is not None:
        entry["cmake_minimum_version"] = minimum.group(1)
    if executables:
        entry["executables"] = executables
    if dependencies := _fetched_dependencies(text):
        entry["fetched_dependencies"] = dependencies
    if options := sorted({name for name, _default in _OPTION.findall(text)}):
        entry["options"] = options
    return entry


def repository_cmake_development_commands(root: Path) -> tuple[object, list[str]] | None:
    """Return exact CMake-derived development commands without executing them.

    Each entry is proven only by the manifest bytes it cites: a `ctest`
    command appears solely for a project that both enables testing and
    registers at least one test, and a pinned `FetchContent` dependency is
    reported only when its URL carries an exact version tag. Nothing here is
    executed -- every entry stays `execution_verified: False`, matching
    `curated_python_development.repository_development_commands()`.
    """

    manifests = sorted(
        path
        for path in root.rglob("CMakeLists.txt")
        if path.is_file() and len(path.relative_to(root).parts) <= _MAX_DEPTH
    )
    entries: list[dict[str, object]] = []
    locations: list[str] = []
    for manifest in manifests:
        entry = _project_entry(root, manifest)
        if entry is None:
            continue
        entries.append(entry)
        # Each entry cites exactly one manifest -- the file just parsed.
        locations.append(manifest.relative_to(root).as_posix())
    if not entries:
        return None
    return {"entries": entries}, sorted(set(locations))


__all__ = ["repository_cmake_development_commands"]
