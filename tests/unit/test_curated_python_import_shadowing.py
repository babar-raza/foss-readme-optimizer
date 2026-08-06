"""Prove duplicate Python package-export inheritance evidence."""

from pathlib import Path

from readme_agent.facts.curated_python_import_shadowing import python_import_shadowing


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_collects_final_duplicate_binding_when_inheritance_changes(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/real/Options.py", "class Options(BaseOptions):\n    pass\n")
    _write(tmp_path, "pkg/Options.py", "class Options:\n    pass\n")
    _write(
        tmp_path,
        "pkg/__init__.py",
        "from .real.Options import Options\nfrom .Options import Options\n",
    )

    result = python_import_shadowing(tmp_path)

    assert result is not None
    value, locations = result
    assert locations == ["pkg/Options.py", "pkg/__init__.py", "pkg/real/Options.py"]
    assert value["entries"] == [
        {
            "package_initializer": "pkg/__init__.py",
            "package_initializer_sha256": value["entries"][0]["package_initializer_sha256"],
            "symbol": "Options",
            "binding_history": value["entries"][0]["binding_history"],
            "final_source_path": "pkg/Options.py",
            "final_bases": [],
            "inheritance_changed": True,
        }
    ]
    assert value["entries"][0]["binding_history"][0]["bases"] == ["BaseOptions"]


def test_ignores_duplicate_binding_with_equivalent_inheritance(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/one/Options.py", "class Options(BaseOptions):\n    pass\n")
    _write(tmp_path, "pkg/two/Options.py", "class Options(BaseOptions):\n    pass\n")
    _write(
        tmp_path,
        "pkg/__init__.py",
        "from .one.Options import Options\nfrom .two.Options import Options\n",
    )

    assert python_import_shadowing(tmp_path) is None
