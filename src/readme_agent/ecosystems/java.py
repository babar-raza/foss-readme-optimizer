"""Java platform manifest parser: pom.xml (Maven) primary, build.gradle fallback.
Renamed from maven.py (Wave 3) -- pom.xml extraction adapted from aspose.org's
extraction/package_manifest.py, kept byte-identical to the original adaptation;
the build.gradle fallback and runtime_min_version extraction are Wave 3
additions, ported from that same source's `_parse_java_manifest` (which this
project's original maven.py adaptation only partially ported).

Known caveat carried forward explicitly, unchanged (GOVERNANCE.md rule 8: this
matches the actual proven, in-production reference, which has the same
limitation -- not reopened this wave): parse_pom() is a first-match regex over
the *entire* pom.xml file, not scoped to the top-level <project> element. On a
pom.xml with a <parent> section listing its own groupId/version before the
project's own, this can grab the parent's value instead. Fine for the simple,
single-module root pom.xml files the three real pilots actually have.
"""

import re
from pathlib import Path

_COMPILER_PROPERTY_TAGS = (
    "maven.compiler.release",
    "maven.compiler.target",
    "maven.compiler.source",
)
_GRADLE_VERSION_PATTERNS = (
    r"targetCompatibility\s*=\s*['\"]?(\d+)['\"]?",
    r"sourceCompatibility\s*=\s*['\"]?(\d+)['\"]?",
    r"languageVersion\.of\((\d+)\)",
)


def parse_pom(pom_path: Path) -> dict[str, str]:
    text = pom_path.read_text(encoding="utf-8-sig", errors="replace")
    info: dict[str, str] = {}
    for tag, key in [
        ("groupId", "group_id"),
        ("artifactId", "artifact_id"),
        ("version", "version"),
        ("name", "name"),
    ]:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        if match:
            info[key] = match.group(1).strip()

    license_match = re.search(r"<license>.*?<name>(.*?)</name>", text, re.DOTALL)
    if license_match:
        info["license"] = license_match.group(1).strip()

    for prop_tag in _COMPILER_PROPERTY_TAGS:
        match = re.search(rf"<{re.escape(prop_tag)}>(.*?)</{re.escape(prop_tag)}>", text, re.DOTALL)
        if match:
            info["runtime_min_version"] = match.group(1).strip()
            break

    return info


def parse_gradle(gradle_path: Path) -> dict[str, str]:
    text = gradle_path.read_text(encoding="utf-8-sig", errors="replace")
    info: dict[str, str] = {}
    match = re.search(r"group\s*=\s*['\"]([^'\"]+)", text)
    if match:
        info["group_id"] = match.group(1)
    match = re.search(r"version\s*=\s*['\"]([^'\"]+)", text)
    if match:
        info["version"] = match.group(1)
    for pattern in _GRADLE_VERSION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            info["runtime_min_version"] = match.group(1).strip()
            break
    return info


def parse(repo_root: Path) -> dict[str, str]:
    """pom.xml is authoritative when present; build.gradle only fills in
    fields pom.xml didn't provide (matches aspose.org's own merge order)."""
    info: dict[str, str] = {}
    pom_path = repo_root / "pom.xml"
    if pom_path.exists():
        info.update(parse_pom(pom_path))

    gradle_path = repo_root / "build.gradle"
    if gradle_path.exists():
        gradle_info = parse_gradle(gradle_path)
        for key, value in gradle_info.items():
            info.setdefault(key, value)

    return info
