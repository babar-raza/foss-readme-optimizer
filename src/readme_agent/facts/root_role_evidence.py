"""Extract deterministic role and dependency evidence from package manifests."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.facts.root_role_schema import (
    PackageRootRole,
    filesystem_repository_path,
)
from readme_agent.profile.schema import PackageRoot
from readme_agent.registry.models import ProductEntry

_SECONDARY_ROLE_TOKENS: tuple[tuple[PackageRootRole, frozenset[str]], ...] = (
    ("test", frozenset({"test", "tests", "testing", "spec", "specs"})),
    ("benchmark", frozenset({"benchmark", "benchmarks", "bench", "perf", "performance"})),
    ("sample", frozenset({"sample", "samples", "example", "examples", "demo", "demos"})),
    ("converter", frozenset({"converter", "converters", "convert"})),
    ("generator", frozenset({"generator", "generators", "codegen"})),
    ("build_tool", frozenset({"tool", "tools", "tooling", "buildtool", "buildtools"})),
)
PRODUCT_PATH_TOKENS = frozenset({"main", "lib", "library", "package", "packages"})
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class PackageRootEvidence:
    package_root: PackageRoot
    parsed: dict[str, str]
    references: tuple[str, ...]
    secondary_role: PackageRootRole | None
    rationale: tuple[str, ...]


def evidence_tokens(*values: str) -> set[str]:
    return {
        token for value in values for token in _TOKEN_RE.findall(value.casefold().replace("_", ""))
    }


def _manifest_text(root: Path, package_root: PackageRoot) -> str:
    path = root / filesystem_repository_path(package_root.manifest_path)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _xml_values(text: str) -> dict[str, list[str]]:
    if not text.strip().startswith("<"):
        return {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return {}
    values: dict[str, list[str]] = {}
    for element in root.iter():
        tag = element.tag.rsplit("}", maxsplit=1)[-1]
        if element.text and element.text.strip():
            values.setdefault(tag, []).append(element.text.strip())
    return values


def _project_references(
    repository_root: Path,
    package_root: PackageRoot,
    text: str,
) -> tuple[str, ...]:
    if not package_root.manifest_path.casefold().endswith(".csproj") or not text:
        return ()
    try:
        xml_root = ET.fromstring(text)
    except ET.ParseError:
        return ()
    resolved_root = repository_root.resolve()
    package_dir = (resolved_root / filesystem_repository_path(package_root.path)).resolve()
    references: set[str] = set()
    for element in xml_root.iter():
        if element.tag.rsplit("}", maxsplit=1)[-1] != "ProjectReference":
            continue
        include = element.attrib.get("Include")
        if not include:
            continue
        candidate = (package_dir / filesystem_repository_path(include)).resolve()
        try:
            relative = candidate.relative_to(resolved_root)
        except ValueError:
            continue
        references.add(relative.as_posix())
    return tuple(sorted(references))


def _secondary_role(
    package_root: PackageRoot,
    parsed: dict[str, str],
    text: str,
) -> tuple[PackageRootRole | None, tuple[str, ...]]:
    path_tokens = evidence_tokens(package_root.path, package_root.manifest_path)
    identity_tokens = evidence_tokens(
        parsed.get("name", ""),
        parsed.get("artifact_id", ""),
        parsed.get("group_id", ""),
    )
    xml_values = _xml_values(text)
    if any(value.casefold() == "true" for value in xml_values.get("IsTestProject", [])):
        return "test", ("manifest declares IsTestProject=true",)

    for role, markers in _SECONDARY_ROLE_TOKENS:
        path_matches = sorted(path_tokens & markers)
        identity_matches = sorted(identity_tokens & markers)
        if path_matches:
            return role, (f"path token(s) identify {role}: {', '.join(path_matches)}",)
        if identity_matches:
            return role, (
                f"manifest identity token(s) identify {role}: {', '.join(identity_matches)}",
            )
    return None, ()


def inspect_package_root(repository_root: Path, package_root: PackageRoot) -> PackageRootEvidence:
    package_dir = (
        repository_root
        if package_root.path == "."
        else repository_root / filesystem_repository_path(package_root.path)
    )
    parsed = parse_manifest(package_root.ecosystem, package_dir)
    text = _manifest_text(repository_root, package_root)
    role, rationale = _secondary_role(package_root, parsed, text)
    return PackageRootEvidence(
        package_root=package_root,
        parsed=parsed,
        references=_project_references(repository_root, package_root, text),
        secondary_role=role,
        rationale=rationale,
    )


def identity_score(entry: ProductEntry, parsed: dict[str, str]) -> tuple[int, list[str]]:
    name = " ".join(
        value
        for value in (
            parsed.get("name"),
            parsed.get("artifact_id"),
            parsed.get("group_id"),
        )
        if value
    )
    name_tokens = evidence_tokens(name)
    family_tokens = evidence_tokens(entry.family)
    score = 0
    reasons: list[str] = []
    if family_tokens and family_tokens <= name_tokens:
        score += 30
        reasons.append("manifest identity matches registry product family")
    if "foss" in name_tokens:
        score += 20
        reasons.append("manifest identity declares the FOSS package")
    if name.strip():
        score += 5
        reasons.append("manifest declares a distributable package identity")
    return score, reasons
