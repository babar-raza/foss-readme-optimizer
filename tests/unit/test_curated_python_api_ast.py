"""Public reachability versus real implementation: `curated_python_api_ast.py`'s
`member_is_implemented` and its wiring into the full `python_public_surface`
projection (`curated_python_public_surface.py`)."""

from __future__ import annotations

from pathlib import Path

from readme_agent.ecosystems.python_api_schema import PublicSymbolV1
from readme_agent.facts.curated_python_api_ast import member_is_implemented
from readme_agent.facts.curated_python_public_surface import python_public_surface


def _write_widget_package(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "widget-foss"\nversion = "1.0.0"\n'
        'requires-python = ">=3.11"\n'
        '[tool.setuptools.package-dir]\n"" = "src"\n'
        "[tool.setuptools.packages.find]\n"
        'where = ["src"]\ninclude = ["aspose.widget", "aspose.widget.*"]\n',
        encoding="utf-8",
    )
    package = root / "src" / "aspose" / "widget"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from .surfaces import NurbsSurface\n__all__ = ['NurbsSurface']\n", encoding="utf-8"
    )
    (package / "surfaces.py").write_text(
        "class NurbsSurface:\n"
        "    def __init__(self, name=None):\n"
        "        self._name = name\n\n"
        "    def control_points(self):\n"
        "        return []\n\n"
        "    def to_mesh(self):\n"
        '        raise NotImplementedError("NURBS surface to mesh conversion is '
        'not implemented")\n',
        encoding="utf-8",
    )


def test_member_is_implemented_true_for_a_real_method_body(tmp_path: Path):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n    def render(self):\n        return b'ok'\n", encoding="utf-8"
    )
    symbol = PublicSymbolV1(
        qualified_name="widget.Widget.render",
        import_module="widget",
        name="Widget.render",
        kind="method",
        source_path="widget.py",
        source_line=2,
        public_by="name",
    )

    assert member_is_implemented(tmp_path, symbol) is True


def test_member_is_implemented_false_for_a_notimplementederror_stub(tmp_path: Path):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n    def render(self):\n        raise NotImplementedError\n",
        encoding="utf-8",
    )
    symbol = PublicSymbolV1(
        qualified_name="widget.Widget.render",
        import_module="widget",
        name="Widget.render",
        kind="method",
        source_path="widget.py",
        source_line=2,
        public_by="name",
    )

    assert member_is_implemented(tmp_path, symbol) is False


def test_member_is_implemented_none_for_a_non_callable_symbol(tmp_path: Path):
    (tmp_path / "widget.py").write_text("class Widget:\n    field: int = 0\n", encoding="utf-8")
    symbol = PublicSymbolV1(
        qualified_name="widget.Widget",
        import_module="widget",
        name="Widget",
        kind="class",
        source_path="widget.py",
        source_line=1,
        public_by="name",
    )

    assert member_is_implemented(tmp_path, symbol) is None


def test_python_public_surface_marks_nurbs_style_stub_method_unimplemented(tmp_path: Path):
    """K2 mandatory red/green: a real-shaped `NurbsSurface.to_mesh` stub
    method remains discoverable in the projected public API surface (a
    public signature with its exact line/source), but is explicitly
    recorded as `implemented: False` rather than silently indistinguishable
    from a real method."""

    _write_widget_package(tmp_path)

    result = python_public_surface(tmp_path)

    assert result is not None
    value, _locations = result
    nurbs = next(row for row in value["classes"] if row["name"] == "NurbsSurface")
    members_by_name = {member["name"]: member for member in nurbs["members"]}

    assert "to_mesh" in members_by_name
    to_mesh = members_by_name["to_mesh"]
    assert to_mesh["implemented"] is False
    assert to_mesh["source_path"] == "src/aspose/widget/surfaces.py"

    control_points = members_by_name["control_points"]
    assert control_points["implemented"] is True


def test_python_public_surface_is_deterministic_for_implemented_field(tmp_path: Path):
    _write_widget_package(tmp_path)

    first = python_public_surface(tmp_path)
    second = python_public_surface(tmp_path)

    assert first is not None
    assert first == second
