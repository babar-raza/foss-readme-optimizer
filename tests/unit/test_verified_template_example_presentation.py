"""Visitor-facing example titles remain meaningful and unique."""

from readme_agent.presentation.verified_template_example_presentation import (
    public_example_title,
    public_examples_introduction,
)
from readme_agent.readme.document_structure import heading_identity


def test_generic_dotnet_example_names_become_distinct_verified_workflows() -> None:
    examples = [
        'var scene = Scene.FromFile("input.gltf");\nscene.Save("output.obj");',
        (
            'var lambert = new LambertMaterial("Body");\n'
            "var pbr = PbrMaterial.FromMaterial(lambert);"
        ),
        'scene.Open("mesh.obj", new ObjLoadOptions());\nscene.Save("mesh.stl");',
        "using var stream = new MemoryStream();\nvar options = new ColladaSaveOptions();",
        'try { scene.Open("unknown.xyz"); } catch (ArgumentException) { }',
    ]
    used: set[str] = set()

    titles = []
    for code in examples:
        title = public_example_title("ReadmeExample", code, "dotnet", used)
        used.add(heading_identity(title))
        titles.append(title)

    assert titles == [
        "Convert GLTF files to OBJ",
        "Convert Lambert materials to PBR",
        "Convert OBJ files to STL",
        "Save COLLADA scenes to memory",
        "Handle unsupported XYZ files",
    ]


def test_negative_workflow_is_separated_from_positive_format_examples() -> None:
    introduction = public_examples_introduction(
        [
            "Convert Lambert materials to PBR",
            "Convert OBJ files to STL",
            "Save COLLADA scenes to memory",
            "Handle unsupported XYZ files",
        ],
        has_repository_files=False,
        has_result_assets=False,
    )

    positive, negative = introduction.split("\n\n")
    assert "COLLADA" in positive
    assert "unsupported" not in positive.casefold()
    assert negative == "Error-handling coverage includes handling unsupported XYZ files."
    assert "COLLADA" not in negative
