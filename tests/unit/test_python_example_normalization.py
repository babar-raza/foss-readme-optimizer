"""Tests for source-proven repair of pathological Python import inventories."""

from pathlib import Path

from readme_agent.facts.python_example_normalization import (
    normalize_python_import_inventory,
)
from readme_agent.registry.models import MinimalExamplePolicy


def _python_repo(root: Path) -> None:
    (root / "aspose" / "threed").mkdir(parents=True)
    (root / "setup.py").write_text(
        "from setuptools import setup\n"
        "setup(name='widget', version='1.0', packages=['aspose', 'aspose.threed'])\n",
        encoding="utf-8",
    )
    (root / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (root / "aspose" / "threed" / "__init__.py").write_text(
        "from .Scene import Scene\nfrom .Required import Required\n",
        encoding="utf-8",
    )
    (root / "aspose" / "threed" / "Scene.py").write_text(
        "class Scene:\n    def __init__(self, name=None):\n        self.name = name\n",
        encoding="utf-8",
    )
    (root / "aspose" / "threed" / "Required.py").write_text(
        "class Required:\n    def __init__(self, value):\n        self.value = value\n",
        encoding="utf-8",
    )


def _example(code: str) -> MinimalExamplePolicy:
    return MinimalExamplePolicy(
        language="python",
        class_name="Inventory",
        code=code,
        evidence_paths=["README.md"],
        required_symbols=["Scene"],
    )


def test_import_inventory_becomes_one_source_proven_construction(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    original = _example("from aspose.threed import Required, Scene, Missing, Other\n")

    normalized = normalize_python_import_inventory(tmp_path, original)

    assert normalized.code == "from aspose.threed import Scene\n\nscene = Scene()\n"
    assert normalized.class_name == "Scene"
    assert normalized.evidence_paths == ["aspose/threed/Scene.py"]
    assert normalized.required_symbols == ["Scene"]


def test_working_example_is_never_rewritten(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    original = _example("from aspose.threed import Scene\n\nscene = Scene()\n")

    assert normalize_python_import_inventory(tmp_path, original) == original
