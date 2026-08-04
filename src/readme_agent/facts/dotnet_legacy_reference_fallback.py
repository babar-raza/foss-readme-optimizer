"""Normalize repository-local assembly paths for modern isolated MSBuild."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree


def apply_repository_assembly_reference_fallback(repository_root: Path) -> tuple[str, ...]:
    """Convert path-valued Reference Include attributes into equivalent HintPath elements."""

    transformations: list[str] = []
    for project in sorted(repository_root.rglob("*.csproj")):
        try:
            document = ElementTree.parse(project)
        except ElementTree.ParseError as exc:
            raise ValueError(f".NET project XML is invalid: {project}") from exc
        changed = 0
        for reference in document.getroot().iter():
            if reference.tag.rsplit("}", 1)[-1] != "Reference":
                continue
            include = reference.attrib.get("Include", "").strip()
            if (
                not include.casefold().endswith(".dll")
                or not ({"/", "\\"} & set(include))
                or any(marker in include for marker in ("$(", "*", "?"))
            ):
                continue
            target = (project.parent / include.replace("\\", "/")).resolve()
            try:
                target.relative_to(repository_root.resolve())
            except ValueError as exc:
                raise ValueError(".NET assembly reference escapes the repository snapshot") from exc
            if not target.is_file():
                raise ValueError(f".NET repository assembly reference is unavailable: {include}")
            reference.attrib["Include"] = target.stem
            hint_path = ElementTree.SubElement(reference, "HintPath")
            hint_path.text = include
            changed += 1
        if changed:
            ElementTree.indent(document, space="  ")
            document.write(project, encoding="utf-8", xml_declaration=True)
            transformations.append(
                project.relative_to(repository_root).as_posix()
                + f":repository-assembly-reference-hint-paths={changed}"
            )
    return tuple(transformations)
