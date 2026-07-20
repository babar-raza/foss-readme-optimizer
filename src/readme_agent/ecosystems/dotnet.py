""" ".NET platform manifest parser: *.csproj. Adapted from aspose.org's
extraction/package_manifest.py (_parse_dotnet_manifest), GOVERNANCE.md rule 8.

Known caveat, carried forward: takes the *first* of up to 20 .csproj files
found under the repo root (shallowest path first), not a solution-wide
(.sln) resolution across every project. Matches the proven reference's own
documented bound -- fine for a single-package repo, would need a real .sln
parse for a genuine multi-project solution.
"""

import re
from pathlib import Path

_MAX_CSPROJ_FILES = 20

# Lower rank = broader runtime compatibility.
_FRAMEWORK_RANK: dict[str, int] = {
    "netstandard1.0": 10,
    "netstandard1.1": 11,
    "netstandard1.2": 12,
    "netstandard1.3": 13,
    "netstandard1.4": 14,
    "netstandard1.5": 15,
    "netstandard1.6": 16,
    "netstandard2.0": 20,
    "netstandard2.1": 21,
    "net5.0": 50,
    "net6.0": 60,
    "net7.0": 70,
    "net8.0": 80,
    "net9.0": 90,
}


def _lowest_framework(targets: list[str]) -> str:
    if not targets:
        return ""
    return sorted(targets, key=lambda t: _FRAMEWORK_RANK.get(t, 100))[0]


def parse_csproj(csproj_path: Path) -> dict[str, str]:
    text = csproj_path.read_text(encoding="utf-8-sig", errors="replace")
    info: dict[str, str] = {}
    for tag, key in [("PackageId", "name"), ("AssemblyName", "name"), ("Version", "version")]:
        if info.get(key):
            continue
        match = re.search(rf"<{tag}>(.*?)</{tag}>", text)
        if match:
            info[key] = match.group(1)

    plural_match = re.search(r"<TargetFrameworks>(.*?)</TargetFrameworks>", text)
    single_match = re.search(r"<TargetFramework>(.*?)</TargetFramework>", text)
    if plural_match:
        targets = [t.strip() for t in plural_match.group(1).split(";") if t.strip()]
        info["target_framework"] = targets[0] if targets else ""
        info["min_framework"] = _lowest_framework(targets)
    elif single_match:
        target = single_match.group(1).strip()
        info["target_framework"] = target
        info["min_framework"] = target

    return info


def parse(repo_root: Path) -> dict[str, str]:
    csproj_files = list(repo_root.rglob("*.csproj"))[:_MAX_CSPROJ_FILES]
    if not csproj_files:
        return {}
    csproj_files.sort(key=lambda p: len(p.parts))
    return parse_csproj(csproj_files[0])
