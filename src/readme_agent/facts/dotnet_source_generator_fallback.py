"""Use checked-in .NET generator output only under a proven project contract."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

_GENERATOR_PACKAGE = "Aspose.EnumExtensionsGenerator"


def apply_checked_in_generator_fallback(repository_root: Path) -> tuple[str, ...]:
    """Normalize copied projects that retain exact generated source for offline builds."""

    transformations: list[str] = []
    for project in sorted(repository_root.rglob("*.csproj")):
        generated = project.parent / "Generated"
        if not generated.is_dir() or not any(generated.rglob("*.cs")):
            continue
        try:
            document = ElementTree.parse(project)
        except ElementTree.ParseError as exc:
            raise ValueError(f".NET project XML is invalid: {project}") from exc
        root = document.getroot()
        parents = {child: parent for parent in root.iter() for child in parent}
        references = [
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "PackageReference"
            and element.attrib.get("Include", "").casefold() == _GENERATOR_PACKAGE.casefold()
        ]
        if not references:
            continue
        if any(
            reference.attrib.get("PrivateAssets", "").casefold() != "all"
            or reference.attrib.get("ExcludeAssets", "").casefold() != "runtime"
            for reference in references
        ):
            raise ValueError("source-generator fallback requires a private analyzer-only package")
        for reference in references:
            parents[reference].remove(reference)
        property_group = next(
            (element for element in root if element.tag.rsplit("}", 1)[-1] == "PropertyGroup"),
            None,
        )
        if property_group is None:
            property_group = ElementTree.SubElement(root, "PropertyGroup")
        include_generated = next(
            (
                element
                for element in property_group
                if element.tag.rsplit("}", 1)[-1] == "IncludeGenerated"
            ),
            None,
        )
        if include_generated is None:
            include_generated = ElementTree.SubElement(property_group, "IncludeGenerated")
        include_generated.text = "true"
        ElementTree.indent(document, space="  ")
        document.write(project, encoding="utf-8", xml_declaration=True)
        transformations.append(
            project.relative_to(repository_root).as_posix()
            + ":Aspose.EnumExtensionsGenerator->checked-in-generated-source"
        )
    return tuple(transformations)
