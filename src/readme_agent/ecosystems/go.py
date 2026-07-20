"""Go platform manifest parser: go.mod. Adapted from aspose.org's
extraction/package_manifest.py (_parse_go_manifest/_extract_go_package_name),
GOVERNANCE.md rule 8.

Parses go.mod directly with stdlib regex rather than shelling out to the real
`go` toolchain's own `go mod edit -json` -- that would require Go installed
in every environment this ever runs in (dev machine, CI runner), an
environmental dependency this project's git-binary precedent doesn't actually
share (git is already required everywhere this runs; a Go toolchain is not).
"""

import re
from pathlib import Path


def _extract_package_name(repo_root: Path) -> str:
    """Declared `package` name from the first non-test .go file at repo root
    (excludes *_test.go and subdirectories, skips `package main`)."""
    for go_file in sorted(repo_root.glob("*.go")):
        if go_file.name.endswith("_test.go"):
            continue
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = re.search(r"^package\s+(\w+)", text, re.MULTILINE)
        if match and match.group(1) != "main":
            return match.group(1)
    return ""


def parse_go_mod(go_mod_path: Path) -> dict[str, str]:
    text = go_mod_path.read_text(encoding="utf-8", errors="replace")
    info: dict[str, str] = {}
    match = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
    if match:
        info["name"] = match.group(1)
    match = re.search(r"^go\s+([\d.]+)", text, re.MULTILINE)
    if match:
        info["go_version"] = match.group(1)
        info["runtime_min_version"] = f"Go {match.group(1)}+"
    return info


def parse(repo_root: Path) -> dict[str, str]:
    go_mod_path = repo_root / "go.mod"
    if not go_mod_path.exists():
        return {}
    info = parse_go_mod(go_mod_path)
    package_name = _extract_package_name(repo_root)
    if package_name:
        info["package_name"] = package_name
    return info
