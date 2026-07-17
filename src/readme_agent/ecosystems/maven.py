"""Regex-based pom.xml parser, adapted from aspose.org's extraction/package_manifest.py.

Known caveat carried forward explicitly (not silently inherited): this is a
first-match regex over the *entire* file, not scoped to the top-level
<project> element. On a pom.xml with a <parent> section listing its own
groupId/version before the project's own, this can grab the parent's value
instead. Fine for the simple, single-module root pom.xml files the three
in-scope repos actually have; would need hardening (e.g. xml.etree) before
depending on it for a pom.xml with a non-trivial <parent> block.
"""

import re
from pathlib import Path


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

    return info
