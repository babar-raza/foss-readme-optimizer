"""C/C++ platform manifest parser: CMakeLists.txt. Adapted from aspose.org's
extraction/package_manifest.py (_parse_cpp_manifest), GOVERNANCE.md rule 8.

Known caveat, carried forward: only CMake is handled (the sprint's own
survey lists five plausible C/C++ build systems -- CMake, Meson, Make, Ninja,
Autotools -- and two package managers, Conan and vcpkg, with no single
dominant manifest format); only the *first* `add_library` call is read, not
every target in a multi-library CMakeLists.txt.
"""

import re
from pathlib import Path


def parse_cmakelists(cmakelists_path: Path) -> dict[str, str]:
    text = cmakelists_path.read_text(encoding="utf-8-sig", errors="replace")
    info: dict[str, str] = {}

    match = re.search(r"project\s*\(\s*(\S+)(?:\s+VERSION\s+(\S+))?", text, re.IGNORECASE)
    if match:
        info["name"] = match.group(1)
        if match.group(2):
            info["version"] = match.group(2).rstrip(")")

    match = re.search(r"cmake_minimum_required\s*\(\s*VERSION\s+([\d.]+)", text, re.IGNORECASE)
    if match:
        info["cmake_min_version"] = match.group(1)

    match = re.search(r"add_library\s*\(\s*([A-Za-z][A-Za-z0-9_.-]*)\s+", text, re.IGNORECASE)
    if match:
        info["library_target"] = match.group(1)

    match = re.search(
        r"set_property\s*\([^)]*CXX_STANDARD\s+(\d+)|CMAKE_CXX_STANDARD\s+(\d+)",
        text,
        re.IGNORECASE,
    )
    if match:
        std = match.group(1) or match.group(2)
        if std:
            info["cpp_standard"] = std

    return info


def parse(repo_root: Path) -> dict[str, str]:
    cmakelists_path = repo_root / "CMakeLists.txt"
    if not cmakelists_path.exists():
        return {}
    return parse_cmakelists(cmakelists_path)
