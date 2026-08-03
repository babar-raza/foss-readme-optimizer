"""Discover and hash the selected Aspose.org extractor import closure."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_org_format_contract import canonical_dependency_sha256

_ENTRYPOINT_MODULES = (
    "extraction.formats",
    "extraction.package_root",
    "extraction.tree_helpers",
)


class AsposeOrgDependencySnapshotV1(BaseModel):
    """Exact selected upstream file identities for one extractor invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    files: dict[str, str]
    canonical_sha256: str


def _module_path(pipeline: Path, module: str) -> Path:
    return pipeline.joinpath(*module.split(".")).with_suffix(".py")


def _local_imports(path: Path, *, module: str, pipeline: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ValueError(f"cannot parse extractor dependency {path}: {exc}") from exc
    imported: set[str] = set()
    for node in ast.walk(tree):
        candidates: list[str] = []
        if isinstance(node, ast.Import):
            candidates.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = module.split(".")[:-1]
                if node.level > 1:
                    package = package[: -(node.level - 1)]
                suffix = node.module.split(".") if node.module else []
                candidates.append(".".join([*package, *suffix]))
            elif node.module:
                candidates.append(node.module)
        for candidate in candidates:
            if candidate.startswith("extraction.") and _module_path(pipeline, candidate).is_file():
                imported.add(candidate)
    return imported


def snapshot_aspose_org_dependencies(root: Path, pipeline: Path) -> AsposeOrgDependencySnapshotV1:
    """Hash the complete local import closure selected by the adapter."""

    pending = list(_ENTRYPOINT_MODULES)
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
        relative = path.relative_to(root).as_posix()
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        pending.extend(sorted(_local_imports(path, module=module, pipeline=pipeline) - visited))
    ordered = dict(sorted(files.items()))
    return AsposeOrgDependencySnapshotV1(
        files=ordered,
        canonical_sha256=canonical_dependency_sha256(ordered),
    )
