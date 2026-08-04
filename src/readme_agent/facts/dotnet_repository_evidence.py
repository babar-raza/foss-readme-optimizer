"""Assemble current-revision .NET repository evidence for truth selection."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from readme_agent.ecosystems.dotnet_public_types import public_dotnet_type_index
from readme_agent.facts.aspose_org_dotnet_adapter import extract_aspose_org_dotnet_api
from readme_agent.facts.aspose_org_format_adapter import extract_aspose_org_formats
from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatExtractionV1
from readme_agent.facts.dotnet_repository_evidence_schema import (
    AsposeOrgDotnetExtractionV1,
    DotnetApiTypeEvidenceV1,
    DotnetBoundaryEvidenceV1,
    DotnetExampleEvidenceV1,
    DotnetFormatEvidenceV1,
    DotnetRepositoryEvidenceCatalogV1,
)
from readme_agent.facts.repository_examples import (
    repository_readme_example_candidates,
    repository_source_example_candidates,
)
from readme_agent.facts.root_role_schema import (
    PackageRootRoleInventoryV1,
    filesystem_repository_path,
    portable_repository_path,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

ApiExtractor = Callable[..., AsposeOrgDotnetExtractionV1]
FormatExtractor = Callable[..., AsposeOrgFormatExtractionV1]
BoundaryKind = Literal["not_implemented", "not_supported", "obsolete"]
Readiness = Literal["ready", "partial", "blocked"]
_BOUNDARIES: dict[BoundaryKind, re.Pattern[str]] = {
    "not_implemented": re.compile(r"\bNotImplementedException\b"),
    "not_supported": re.compile(r"\bNotSupportedException\b"),
    "obsolete": re.compile(r"\[\s*Obsolete(?:Attribute)?\b"),
}
_EXCLUDED_PARTS = {"bin", "obj", "generated", "sample", "samples", "test", "tests"}
_MAX_BOUNDARIES = 200


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_id(prefix: str, identity: str) -> str:
    return f"{prefix}-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"


def _relative_source(root: Path, raw: str) -> tuple[str, Path]:
    candidate = Path(raw)
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    relative = path.relative_to(root.resolve()).as_posix()
    if not path.is_file():
        raise ValueError(f"evidence source is unavailable: {relative}")
    return relative, path


def _local_api_types(root: Path, product_root: Path) -> tuple[DotnetApiTypeEvidenceV1, ...]:
    records: list[DotnetApiTypeEvidenceV1] = []
    for declaration in public_dotnet_type_index(product_root).values():
        relative = declaration.source_path.relative_to(root).as_posix()
        text = declaration.source_path.read_text(encoding="utf-8-sig", errors="replace")
        match = re.search(rf"\b{re.escape(declaration.name)}\b", text)
        line = text.count("\n", 0, match.start()) + 1 if match else 1
        records.append(
            DotnetApiTypeEvidenceV1(
                evidence_id=_stable_id(
                    "dotnet-api", f"{relative}:{line}:{declaration.qualified_name}"
                ),
                origin="local_lexer",
                name=declaration.name,
                qualified_name=declaration.qualified_name,
                kind="type",
                source_path=relative,
                source_line=line,
                source_sha256=_sha256(declaration.source_path),
            )
        )
    return tuple(sorted(records, key=lambda item: item.qualified_name))


def _examples(root: Path) -> tuple[DotnetExampleEvidenceV1, ...]:
    candidates = [
        *repository_readme_example_candidates(root, "dotnet"),
        *repository_source_example_candidates(root, "dotnet"),
    ]
    unique: dict[str, DotnetExampleEvidenceV1] = {}
    for candidate in candidates:
        code_sha = hashlib.sha256(candidate.code.encode("utf-8")).hexdigest()
        record = DotnetExampleEvidenceV1(
            evidence_id=_stable_id("dotnet-example", code_sha),
            class_name=candidate.class_name,
            code=candidate.code,
            code_sha256=code_sha,
            evidence_paths=tuple(
                portable_repository_path(path) for path in candidate.evidence_paths
            ),
            required_symbols=tuple(candidate.required_symbols),
        )
        unique[record.evidence_id] = record
    return tuple(sorted(unique.values(), key=lambda item: item.evidence_id))


def _boundaries(
    root: Path, product_root: Path
) -> tuple[tuple[DotnetBoundaryEvidenceV1, ...], bool]:
    records: list[DotnetBoundaryEvidenceV1] = []
    truncated = False
    for path in sorted(product_root.rglob("*.cs")):
        if _EXCLUDED_PARTS & {part.casefold() for part in path.relative_to(product_root).parts}:
            continue
        relative = path.relative_to(root).as_posix()
        digest = _sha256(path)
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1
        ):
            for kind, pattern in _BOUNDARIES.items():
                if not pattern.search(line):
                    continue
                if len(records) >= _MAX_BOUNDARIES:
                    truncated = True
                    return tuple(records), truncated
                records.append(
                    DotnetBoundaryEvidenceV1(
                        evidence_id=_stable_id(
                            "dotnet-boundary", f"{relative}:{line_number}:{kind}"
                        ),
                        kind=kind,
                        source_path=relative,
                        source_line=line_number,
                        source_sha256=digest,
                        source_text=line.strip(),
                    )
                )
    return tuple(records), truncated


def build_dotnet_repository_evidence(
    snapshot: RepositorySnapshotV1,
    root_roles: PackageRootRoleInventoryV1,
    *,
    family: str,
    api_extractor: ApiExtractor = extract_aspose_org_dotnet_api,
    format_extractor: FormatExtractor = extract_aspose_org_formats,
) -> DotnetRepositoryEvidenceCatalogV1:
    """Build one immutable .NET evidence catalog from the selected product root."""

    verify_repository_snapshot(snapshot)
    if (
        root_roles.org_repo != snapshot.org_repo
        or root_roles.source_revision != snapshot.source_revision
    ):
        raise ValueError("package-root roles do not match the immutable repository snapshot")
    manifest = root_roles.selected_product_manifest_path
    if root_roles.selection_state != "selected" or manifest is None:
        raise ValueError(".NET evidence requires one selected product package root")
    root = snapshot.root_path.resolve()
    manifest_path = root / filesystem_repository_path(manifest)
    if not manifest_path.is_file():
        raise ValueError(f"selected product manifest is unavailable: {manifest}")
    product_root = manifest_path.parent

    api_result = api_extractor(root, product_root=product_root, family=family)
    api_types = api_result.api_types or _local_api_types(root, product_root)
    format_result = format_extractor(
        root,
        platform="dotnet",
        family=family,
        source_revision=snapshot.source_revision,
    )
    formats: list[DotnetFormatEvidenceV1] = []
    for item in format_result.formats:
        if item.functional is not True or item.direction not in {"import", "export", "both"}:
            continue
        relative, path = _relative_source(root, item.file)
        formats.append(
            DotnetFormatEvidenceV1(
                evidence_id=_stable_id(
                    "dotnet-format", f"{item.format}:{item.direction}:{relative}:{item.line}"
                ),
                format=item.format,
                direction=item.direction,
                source_path=relative,
                source_line=item.line,
                source_sha256=_sha256(path),
            )
        )
    examples = _examples(root)
    boundaries, boundaries_truncated = _boundaries(root, product_root)
    observations: list[str] = []
    if api_result.status == "unavailable":
        observations.append(f"Aspose.org API extraction unavailable: {api_result.detail}")
    elif api_result.completeness == "partial":
        observations.append("Aspose.org API extraction reported partial coverage")
    if format_result.status == "unavailable":
        observations.append(f"Aspose.org format extraction unavailable: {format_result.detail}")
    if boundaries_truncated:
        observations.append(f"implementation-boundary evidence truncated at {_MAX_BOUNDARIES}")
    readiness: Readiness = (
        "ready" if api_types and examples else "partial" if api_types else "blocked"
    )
    result = DotnetRepositoryEvidenceCatalogV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        inventory_sha256=snapshot.inventory_sha256,
        selected_manifest_path=portable_repository_path(manifest),
        selected_product_root=product_root.relative_to(root).as_posix() or ".",
        root_role_sha256=root_roles.canonical_hash(),
        api_extraction=api_result,
        api_types=api_types,
        format_extraction=format_result,
        formats=tuple(sorted(formats, key=lambda item: item.evidence_id)),
        examples=examples,
        boundaries=boundaries,
        readiness=readiness,
        observations=tuple(observations),
    )
    verify_repository_snapshot(snapshot)
    return result
