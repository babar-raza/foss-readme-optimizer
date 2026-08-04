"""Read-only adapter for Aspose.org's battle-tested .NET API extractor."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Literal

from readme_agent.facts.aspose_org_format_contract import canonical_dependency_sha256
from readme_agent.facts.dotnet_repository_evidence_schema import (
    ASPOSE_ORG_DOTNET_API_RELATIVE_PATH,
    AsposeOrgDotnetExtractionV1,
    DotnetApiMemberEvidenceV1,
    DotnetApiTypeEvidenceV1,
)
from readme_agent.facts.example_execution import secret_free_environment

_DEFAULT_ROOT = Path("D:/onedrive/Documents/GitHub/aspose.org")
_ENTRYPOINT = "extraction.api_surface"
_SCRIPT = r"""
import json, sys, types
from pathlib import Path
pipeline, repo, product_root, family = sys.argv[1:]
package = types.ModuleType("extraction")
package.__package__ = "extraction"
package.__path__ = [str(Path(pipeline) / "extraction")]
sys.modules["extraction"] = package
from extraction.api_surface import extract_api_surface
from extraction.tree_helpers import get_parser
classes, _claims, _scanned, _packages, report = extract_api_surface(
    get_parser("csharp"), "csharp", Path(product_root), Path(repo), family
)
print(json.dumps({"types": classes, "report": report}, sort_keys=True))
"""


def _module_path(pipeline: Path, module: str) -> Path:
    return pipeline.joinpath(*module.split(".")).with_suffix(".py")


def _dependency_snapshot(root: Path, pipeline: Path) -> dict[str, str]:
    pending = [_ENTRYPOINT, "extraction.tree_helpers"]
    visited: set[str] = set()
    files: dict[str, str] = {}
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        path = _module_path(pipeline, module)
        if not path.is_file():
            raise ValueError(f"extractor dependency is unavailable: {module}")
        visited.add(module)
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                candidate = node.module
                if node.level:
                    candidate = f"extraction.{node.module.rsplit('.', 1)[-1]}"
                if (
                    candidate.startswith("extraction.")
                    and _module_path(pipeline, candidate).is_file()
                ):
                    pending.append(candidate)
            elif isinstance(node, ast.Import):
                pending.extend(
                    alias.name
                    for alias in node.names
                    if alias.name.startswith("extraction.")
                    and _module_path(pipeline, alias.name).is_file()
                )
    return dict(sorted(files.items()))


def _revision(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=secret_free_environment(),
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _unavailable(detail: str, revision: str | None = None) -> AsposeOrgDotnetExtractionV1:
    return AsposeOrgDotnetExtractionV1(
        status="unavailable",
        completeness="unavailable",
        extractor_revision=revision,
        detail=detail,
    )


def extract_aspose_org_dotnet_api(
    repository_root: Path,
    *,
    product_root: Path,
    family: str,
) -> AsposeOrgDotnetExtractionV1:
    """Extract public .NET API records without importing sibling code in-process."""

    sibling = Path(os.environ.get("ASPOSE_ORG_ROOT", _DEFAULT_ROOT)).resolve()
    pipeline = sibling / "scripts" / "pipeline"
    interpreter = next(
        (
            path
            for path in (
                sibling / ".venv" / "Scripts" / "python.exe",
                sibling / ".venv" / "bin" / "python",
            )
            if path.is_file()
        ),
        None,
    )
    if not sibling.is_dir() or interpreter is None:
        return _unavailable("Aspose.org repository or virtualenv is unavailable")
    revision_before = _revision(sibling)
    try:
        before = _dependency_snapshot(sibling, pipeline)
    except (OSError, SyntaxError, ValueError) as exc:
        return _unavailable(str(exc), revision_before)
    environment = secret_free_environment()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [
                str(interpreter),
                "-B",
                "-c",
                _SCRIPT,
                str(pipeline),
                str(repository_root.resolve()),
                str(product_root.resolve()),
                family.casefold(),
            ],
            cwd=sibling,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return _unavailable("Aspose.org API extractor timed out", revision_before)
    try:
        after = _dependency_snapshot(sibling, pipeline)
    except (OSError, SyntaxError, ValueError) as exc:
        return _unavailable(f"extractor dependencies changed: {exc}", revision_before)
    if revision_before is None or revision_before != _revision(sibling) or before != after:
        return _unavailable("extractor revision or dependency bytes changed", revision_before)
    if result.returncode != 0:
        return _unavailable(
            (result.stderr or result.stdout or "extractor failed")[:1000], revision_before
        )
    try:
        payload = json.loads(result.stdout)
        records = payload["types"]
        report = payload.get("report", {})
        if not isinstance(records, list) or not isinstance(report, dict):
            raise TypeError("extractor output has an invalid shape")
        api_types = tuple(
            _normalize_type(record, repository_root)
            for record in records
            if record.get("visibility", "public") == "public"
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _unavailable(f"invalid extractor output: {exc}", revision_before)
    partial = bool(report.get("files_capped") or report.get("parse_errors"))
    dependency_sha = canonical_dependency_sha256(before)
    return AsposeOrgDotnetExtractionV1(
        status="available",
        completeness="partial" if partial else "complete",
        api_types=tuple(sorted(api_types, key=lambda item: item.qualified_name)),
        extractor_revision=revision_before,
        extractor_sha256=before[ASPOSE_ORG_DOTNET_API_RELATIVE_PATH],
        dependency_sha256=dependency_sha,
        dependency_files=before,
        detail=f"accepted {len(api_types)} public API types",
    )


def _normalize_type(record: dict[str, object], repository_root: Path) -> DotnetApiTypeEvidenceV1:
    source = Path(str(record["file"]))
    if not source.is_absolute():
        source = repository_root / source
    source = source.resolve()
    relative = source.relative_to(repository_root.resolve()).as_posix()
    name = str(record["name"])
    namespace = str(record.get("canonical_namespace") or record.get("namespace") or "")
    qualified = str(record.get("class_import") or f"{namespace}.{name}").strip(".")
    members: list[DotnetApiMemberEvidenceV1] = []
    member_groups: tuple[tuple[Literal["method", "property"], str], ...] = (
        ("method", "methods"),
        ("property", "properties"),
    )
    for kind, key in member_groups:
        raw_items = record.get(key, [])
        if not isinstance(raw_items, list):
            raise TypeError(f"{key} must be a list")
        for item in raw_items:
            if isinstance(item, dict) and item.get("name"):
                members.append(
                    DotnetApiMemberEvidenceV1(
                        name=str(item["name"]),
                        kind=kind,
                        summary=str(item.get("doc")) if item.get("doc") else None,
                    )
                )
    raw_line = record.get("line")
    line = int(raw_line) if isinstance(raw_line, int | str) else 1
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence_id = hashlib.sha256(f"{relative}:{line}:{qualified}".encode()).hexdigest()[:20]
    return DotnetApiTypeEvidenceV1(
        evidence_id=f"dotnet-api-{evidence_id}",
        origin="aspose_org",
        name=name,
        qualified_name=qualified,
        kind=str(record.get("kind") or "type"),
        summary=str(record.get("doc")) if record.get("doc") else None,
        source_path=relative,
        source_line=line,
        source_sha256=digest,
        members=tuple(sorted(members, key=lambda item: (item.kind, item.name))),
    )
