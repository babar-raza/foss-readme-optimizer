"""Unit tests for generated README-example public-API quality checks."""

from readme_agent.facts.example_quality import generated_example_quality_failures


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


def test_python_example_over_six_statements_is_rejected() -> None:
    source = "; ".join(f"value_{index} = {index}" for index in range(7))

    failures = generated_example_quality_failures("python", source)

    assert len(failures) == 1
    assert "7 executable statements" in failures[0]


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
