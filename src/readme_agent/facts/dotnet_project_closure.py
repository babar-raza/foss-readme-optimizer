"""Resolve the immutable .NET project-reference export closure."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

_ROOT_BUILD_FILES = (
    "Directory.Build.props",
    "Directory.Build.targets",
    "Directory.Packages.props",
    "global.json",
)


def dotnet_project_export_paths(root: Path, selected_project: Path) -> tuple[str, ...]:
    """Return projects, repository assemblies, and root metadata needed by MSBuild."""

    repository_root = root.resolve()
    pending = [selected_project.resolve()]
    visited: set[Path] = set()
    export_paths: set[str] = set()
    while pending:
        project = pending.pop()
        try:
            project.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(".NET project reference escapes the repository snapshot") from exc
        if project in visited:
            continue
        if not project.is_file() or project.suffix.casefold() != ".csproj":
            raise ValueError(f".NET project reference is unavailable: {project}")
        visited.add(project)
        parent = project.parent.relative_to(repository_root).as_posix() or "."
        export_paths.add(parent)
        try:
            document = ElementTree.parse(project)
        except ElementTree.ParseError as exc:
            raise ValueError(f".NET project XML is invalid: {project}") from exc
        for element in document.iter():
            element_name = element.tag.rsplit("}", 1)[-1]
            include = element.attrib.get("Include", "").strip()
            if element_name == "ProjectReference":
                if not include or any(marker in include for marker in ("$(", "*", "?")):
                    raise ValueError(".NET project reference must be a literal repository path")
                pending.append((project.parent / include.replace("\\", "/")).resolve())
                continue
            if (
                element_name != "Reference"
                or not include.casefold().endswith(".dll")
                or not ({"/", "\\"} & set(include))
            ):
                continue
            if any(marker in include for marker in ("$(", "*", "?")):
                raise ValueError(".NET assembly reference must be a literal repository path")
            assembly = (project.parent / include.replace("\\", "/")).resolve()
            try:
                relative_assembly = assembly.relative_to(repository_root)
            except ValueError as exc:
                raise ValueError(".NET assembly reference escapes the repository snapshot") from exc
            if not assembly.is_file():
                raise ValueError(f".NET repository assembly reference is unavailable: {include}")
            export_paths.add(relative_assembly.as_posix())

    for name in _ROOT_BUILD_FILES:
        if (repository_root / name).is_file():
            export_paths.add(name)
    return tuple(sorted(export_paths, key=lambda item: (item.casefold(), item)))
