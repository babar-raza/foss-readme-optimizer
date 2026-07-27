"""Unit tests for generated README-example public-API quality checks."""

import pytest

from readme_agent.facts.example_quality import (
    generated_example_quality_failures,
    strip_source_comments,
)


def test_python_private_attribute_is_rejected() -> None:
    failures = generated_example_quality_failures(
        "python",
        "mesh._control_points.append(point)",
    )

    assert len(failures) == 1
    assert "_control_points" in failures[0]


def test_python_public_attribute_and_dunder_are_allowed() -> None:
    source = (
        "from package import Mesh, Point\n"
        "mesh = Mesh()\n"
        "point = Point()\n"
        "mesh.control_points.append(point)\n"
        "name = mesh.__class__.__name__"
    )

    assert generated_example_quality_failures("python", source) == []


def test_python_example_over_eight_statements_is_rejected() -> None:
    source = "; ".join(f"value_{index} = {index}" for index in range(9))

    failures = generated_example_quality_failures("python", source)

    assert len(failures) == 1
    assert "9 executable statements" in failures[0]


def test_bounded_repository_example_with_eight_statements_is_allowed() -> None:
    source = (
        "from aspose.threed import Scene\n"
        "from aspose.threed.formats.obj import ObjLoadOptions\n"
        "scene = Scene()\n"
        "options = ObjLoadOptions()\n"
        "options.enable_materials = True\n"
        "options.flip_coordinate_system = False\n"
        "scene.open('model.obj', options)\n"
        "print(scene.root_node)\n"
    )

    assert generated_example_quality_failures("python", source) == []


def test_python_import_inventory_without_usage_is_rejected() -> None:
    source = "from aspose.threed import Scene, Node, Mesh, Vector3"

    failures = generated_example_quality_failures("python", source)

    assert any("imports 4 symbols" in failure for failure in failures)
    assert any("contains only imports" in failure for failure in failures)
    assert any("unused imported symbol" in failure for failure in failures)


def test_python_unused_import_is_rejected() -> None:
    source = "from package import Scene, Mesh\nscene = Scene()"

    failures = generated_example_quality_failures("python", source)

    assert len(failures) == 1
    assert "Mesh" in failures[0]


def test_other_languages_remain_compiler_owned() -> None:
    assert generated_example_quality_failures("dotnet", "value._private") == []


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("java", "var scene = new Scene(); // create scene"),
        ("dotnet", "var scene = new Scene(); /* create scene */"),
        ("python", "# create scene\nscene = Scene()"),
        ("typescript", "const scene = new Scene(); // create scene"),
        ("go", "scene := NewScene() // create scene"),
        ("cpp", "auto scene = Scene(); // create scene"),
        ("rust", "let scene = Scene::new(); // create scene"),
    ],
)
def test_comments_are_rejected_in_every_supported_example_language(
    language: str,
    source: str,
) -> None:
    failures = generated_example_quality_failures(language, source)

    assert any("contains a source comment" in failure for failure in failures)


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("java", 'var url = "https://example.test/path";'),
        ("dotnet", 'var url = "https://example.test/path";'),
        ("python", 'url = "https://example.test/path"'),
        ("typescript", 'const url = "https://example.test/path";'),
        ("go", 'url := "https://example.test/path"'),
        ("cpp", 'auto url = "https://example.test/path";'),
        ("rust", 'let url = "https://example.test/path";'),
    ],
)
def test_comment_like_text_inside_strings_is_allowed(language: str, source: str) -> None:
    assert generated_example_quality_failures(language, source) == []


def test_python_docstring_is_rejected_as_a_documentation_comment() -> None:
    failures = generated_example_quality_failures(
        "python",
        '"""Explain the example."""\nscene = Scene()',
    )

    assert any("documentation comment" in failure for failure in failures)


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        (
            "dotnet",
            'var url = "https://example.com"; // save output\nSave(url);\n',
            'var url = "https://example.com";\nSave(url);\n',
        ),
        (
            "cpp",
            'auto url = "https://example.com"; /* save output */\nSave(url);\n',
            'auto url = "https://example.com";\nSave(url);\n',
        ),
        (
            "go",
            'url := "https://example.com" // save output\nsave(url)\n',
            'url := "https://example.com"\nsave(url)\n',
        ),
        (
            "rust",
            'let url = "https://example.com"; // save output\nsave(url);\n',
            'let url = "https://example.com";\nsave(url);\n',
        ),
    ],
)
def test_comment_removal_preserves_comment_like_string_literals(
    language: str, source: str, expected: str
) -> None:
    normalized = strip_source_comments(language, source)

    assert normalized == expected
    assert generated_example_quality_failures(language, normalized) == []
