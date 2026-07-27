"""Unit tests for Python README-example public consumer selection."""

import pytest

from readme_agent.facts.python_example_verifier import selected_python_consumer_imports


def test_consumer_selection_uses_actual_imports_not_repository_evidence_anchors() -> None:
    code = (
        "from aspose.threed import Scene\n"
        "from aspose.threed.formats.obj import ObjLoadOptions\n"
        "scene = Scene()\n"
        "options = ObjLoadOptions()\n"
    )
    public_names = {
        "aspose.threed.Scene",
        "aspose.threed.FileFormat.WAVEFRONT_OBJ",
        "aspose.threed.formats.obj.ObjLoadOptions",
    }

    selected = selected_python_consumer_imports(code, public_names, "aspose")

    assert selected == [
        "aspose.threed.Scene",
        "aspose.threed.formats.obj.ObjLoadOptions",
    ]


def test_consumer_selection_rejects_a_non_public_import() -> None:
    code = "from aspose.threed import _PrivateScene\nscene = _PrivateScene()\n"

    with pytest.raises(ValueError, match="non-public"):
        selected_python_consumer_imports(code, {"aspose.threed.Scene"}, "aspose")


def test_consumer_selection_requires_a_distributed_package_import() -> None:
    with pytest.raises(ValueError, match="imports no symbol"):
        selected_python_consumer_imports("value = 1\n", {"aspose.threed.Scene"}, "aspose")
