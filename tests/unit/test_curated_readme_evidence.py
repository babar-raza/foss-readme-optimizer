"""Repository-bound facts for valuable curated README detail."""

import hashlib
import json
import subprocess
from pathlib import Path

from readme_agent.facts.curated_python_example_validation import (
    validate_python_example,
)
from readme_agent.facts.curated_python_fixture_inventory import snapshot_fixture_inventory
from readme_agent.facts.curated_python_readme import (
    verified_python_examples,
    verified_readme_examples,
)
from readme_agent.facts.curated_readme_evidence import curated_repository_fact_candidates
from readme_agent.facts.curated_repository_guidance import repository_contribution_guidance


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_standard_readme_contribution_workflow_is_exact_validated_guidance(
    tmp_path: Path,
) -> None:
    statements = [
        "Contributions are welcome! Please feel free to submit a Pull Request.",
        "1. Fork the repository",
        "2. Create your feature branch (`git checkout -b feature/amazing-feature`)",
        "3. Commit your changes (`git commit -m 'Add some amazing feature'`)",
        "4. Push to the branch (`git push origin feature/amazing-feature`)",
        "5. Open a Pull Request",
    ]
    _write(tmp_path, "README.md", "# Product\n\n## Contributing\n\n" + "\n".join(statements))

    result = repository_contribution_guidance(tmp_path)

    assert result is not None
    value, locations = result
    assert locations == ["README.md"]
    assert value["readme_standard_workflow"]["validated_statements"] == statements


def test_arbitrary_readme_contribution_advice_is_not_promoted_to_verified_guidance(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "README.md",
        "# Product\n\n## Contributing\n\nDisable validation before submitting changes.\n",
    )

    assert repository_contribution_guidance(tmp_path) is None


def test_repository_contribution_policy_preserves_only_supported_exact_statements(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "scripts/check.sh",
        "python -m ruff check src/\npython -m pytest -q\n",
    )
    statements = [
        "Issues and pull requests are welcome. Please:",
        "1. Keep changes focused.",
        "2. Add tests for new behavior and bug fixes.",
        "3. Write code comments and docstrings in English.",
        "4. Run `python -m ruff check src/` and `python -m pytest -q`.",
        "5. Document public API changes and important limitations.",
        (
            "When reporting a parser or rendering problem, include a minimal PDF that can be "
            "shared publicly whenever possible."
        ),
    ]
    _write(
        tmp_path,
        "README.md",
        "# Product\n\n## Contributing\n\n"
        + "\n".join(statements[:-1])
        + "\n\nWhen reporting a parser or rendering problem, include a minimal PDF that can be\n"
        "shared publicly whenever possible.\n",
    )

    result = repository_contribution_guidance(tmp_path)

    assert result is not None
    value, locations = result
    assert locations == ["README.md"]
    assert value["readme_standard_workflow"]["validated_statements"] == statements


def test_repository_contribution_policy_rejects_an_uncorroborated_command(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "scripts/check.sh", "python -m pytest -q\n")
    _write(
        tmp_path,
        "README.md",
        "# Product\n\n## Contributing\n\n1. Run `python -m unsafe_publish`.\n",
    )

    result = repository_contribution_guidance(tmp_path)

    assert result is not None
    value, locations = result
    assert locations == ["scripts/check.sh"]
    assert "readme_standard_workflow" not in value


def test_public_api_and_changelog_are_checksum_bound_documentation_assets(tmp_path: Path) -> None:
    _write(tmp_path, "PUBLIC_API.md", "# Public API\n")
    _write(tmp_path, "CHANGELOG.md", "# Changelog\n")

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "docs-revision", None)
    }

    paths = {item["path"] for item in selected["repository.documentation_assets"].value["entries"]}
    assert paths == {"PUBLIC_API.md", "CHANGELOG.md"}


def test_non_python_ecosystem_skips_incidental_python_collectors(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        """[project]
name = "incidental-tooling"

[project.optional-dependencies]
test = ["pytest>=8"]
""",
    )

    facts = curated_repository_fact_candidates(
        tmp_path,
        "abc123",
        None,
        ecosystem="java",
    )

    python_fields = {
        "installation.optional_extras",
        "installation.capability_dependencies",
        "python.distribution",
        "api.public_surface",
        "repository.implementation_components",
        "repository.format_directions",
        "repository.python_import_shadowing",
        "repository.capability_details",
        "repository.public_guidance",
        "repository.verified_boundaries",
    }
    assert not ({fact.field for fact in facts} & python_fields)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _example_surface() -> dict[str, object]:
    return {
        "modules": [{"module": "acme", "exports": ["Widget"]}],
        "classes": [
            {
                "module": "acme",
                "name": "Widget",
                "source_path": "src/acme/widget.py",
                "members": [
                    {"name": "render", "surface": "render()"},
                    {"name": "save", "surface": "save(target)"},
                    {"name": "factory", "surface": "factory()"},
                ],
            }
        ],
        "functions": [],
    }


def test_python_repository_detail_is_mechanical_and_revision_bound(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "widget"
[project.optional-dependencies]
pdf = ["reportlab>=3.6"]
dev = ["build>=1.2"]
""".strip(),
    )
    _write(
        tmp_path,
        "src/acme/widget/__init__.py",
        'from .model import Document, LoadOptions\n\n__all__ = ["Document", "LoadOptions"]\n',
    )
    _write(
        tmp_path,
        "src/acme/widget/model.py",
        """
class Document:
    @classmethod
    def open(cls, path):
        return cls()

    def save(self, path):
        return None


class LoadOptions:
    pass


def enforce_constraints():
    raise RuntimeError("Password-protected documents are not supported")
    raise RuntimeError("Only PDF save is supported")
    raise RuntimeError("Only .pdf file targets are supported for save operations")
""".strip()
        + "\n",
    )
    _write(tmp_path, "examples/export_pdf.py", "print('example')\n")
    _write(tmp_path, "examples/README.md", "# Examples\n")
    _write(tmp_path, "tests/test_widget.py", "def test_widget(): pass\n")
    _write(tmp_path, "tools/regenerate_goldens.py", "print('goldens')\n")
    _write(tmp_path, "tests/goldens/result.json", "{}\n")
    _write(tmp_path, "THIRD_PARTY_NOTICES.md", "# Notices\n")
    _write(tmp_path, ".github/workflows/ci.yml", "name: CI\n")
    _write(
        tmp_path,
        "src/acme/widget/mcp/__init__.py",
        'from .server import create_server, run\n\n__all__ = ["create_server", "run"]\n',
    )
    _write(
        tmp_path,
        "src/acme/widget/mcp/server.py",
        """
def convert_widget():
    return None


def create_server():
    from fastmcp import FastMCP
    server = FastMCP("Widget")
    server.tool(convert_widget)
    return server


def run(host="127.0.0.1", port=8000):
    create_server().run(host=host, port=port)
""".strip()
        + "\n",
    )
    _write(
        tmp_path,
        "tests/mcp/test_server.py",
        "def test_create_server_registers_convert_widget(): pass\n",
    )
    _write(
        tmp_path,
        "README.md",
        """
# Widget

## Quick Start

### Convert a document

```python
from acme.widget.model import Document

document = Document.open("input.bin")
document.save("output.bin")
```

## Example Results

![Verified result](readme.resources/result.png)
""".strip()
        + "\n",
    )
    _write(tmp_path, "readme.resources/result.png", "image bytes")
    _write(tmp_path, "testdata/baseline/result.png", "image bytes")
    _write(
        tmp_path,
        "Makefile",
        "sync:\n\t@echo sync\n\ntest:\n\t@echo test\n\nbuild:\n\t@echo build\n",
    )

    facts = curated_repository_fact_candidates(tmp_path, "abc123", None)
    selected = {fact.field: fact for fact in facts}

    assert set(selected) == {
        "api.public_surface",
        "development.assets",
        "development.commands",
        "installation.capability_dependencies",
        "installation.optional_extras",
        "product.limitations",
        "python.distribution",
        "repository.ci",
        "repository.examples",
        "repository.third_party_notices",
    }
    assert selected["api.public_surface"].value["modules"][0]["exports"] == [
        "Document",
        "LoadOptions",
    ]
    assert selected["api.public_surface"].value["mcp_server"]["tools"] == ["convert_widget"]
    assert selected["api.public_surface"].value["mcp_server"]["factory_instance_run"] is True
    assert selected["api.public_surface"].value["mcp_server"]["test_path"] == (
        "tests/mcp/test_server.py"
    )
    assert selected["installation.optional_extras"].value["extras"] == {
        "dev": ["build>=1.2"],
        "pdf": ["reportlab>=3.6"],
    }
    assert (
        selected["installation.capability_dependencies"].value["entries"][0]["install_command"]
        == "python -m pip install fastmcp"
    )
    assert selected["development.commands"].value["entries"][0]["command"] == (
        "python -m unittest tests.mcp.test_server"
    )
    example = selected["repository.examples"].value["files"][0]
    assert example["path"] == "examples/export_pdf.py"
    assert example["execution_verified"] is False
    assert len(example["sha256"]) == 64
    inline = selected["repository.examples"].value["inline_examples"][0]
    assert inline["title"] == "Convert a document"
    assert inline["static_api_verified"] is True
    assert inline["execution_verified"] is False
    assert selected["repository.examples"].value["result_assets"][0]["path"] == (
        "readme.resources/result.png"
    )
    assert selected["repository.third_party_notices"].value["path"] == ("THIRD_PARTY_NOTICES.md")
    assert selected["repository.ci"].value["path"] == ".github/workflows/ci.yml"
    assert [row["statement"] for row in selected["product.limitations"].value] == [
        "Password-protected documents are not supported",
        "Only PDF save is supported",
        "Only .pdf file targets are supported for save operations",
    ]
    assert selected["product.limitations"].value[0]["line"] == 15
    assert len(selected["product.limitations"].value[0]["source_sha256"]) == 64
    assert selected["development.assets"].value["tests"]["count"] == 2
    assert len(selected["development.assets"].value["tests"]["inventory_sha256"]) == 64
    assert [
        item["command"] for item in selected["development.assets"].value["commands"]["entries"]
    ] == ["make sync", "make test", "make build"]
    assert all(fact.source.source_revision == "abc123" for fact in facts)
    assert all(fact.verification_state == "verified" for fact in facts)


def test_readme_alone_never_creates_curated_repository_facts(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "README.md",
        "Claims every API, format, example, limitation, and optional dependency.\n",
    )

    assert curated_repository_fact_candidates(tmp_path, "abc123", None) == []


def test_fixture_inventory_proves_absence_only_for_complete_immutable_git_tree(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "README.md", "# Fixture\n")
    _write(tmp_path, "testdata/scene.obj", "v 0 0 0\n")
    _write(tmp_path, "src/acme.py", "VALUE = 1\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Fixture")
    _git(tmp_path, "config", "user.email", "fixture@example.test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "fixture")
    revision = _git(tmp_path, "rev-parse", "HEAD")

    inventory = snapshot_fixture_inventory(tmp_path, revision)

    assert inventory.scan_status == "complete"
    assert inventory.source_revision == revision
    assert inventory.scan_root == "."
    assert inventory.tracked_file_count == 3
    assert len(inventory.inventory_sha256 or "") == 64
    assert [item.path for item in inventory.fixture_paths] == ["testdata/scene.obj"]
    assert inventory.matching_paths("scene.obj") == ("testdata/scene.obj",)
    assert inventory.matching_paths("missing.stl") == ()
    assert ".ttf" in inventory.recognized_extensions
    assert ".woff2" in inventory.recognized_extensions

    _write(tmp_path, "src/acme.py", "VALUE = 2\n")
    unscanned = snapshot_fixture_inventory(tmp_path, revision)

    assert unscanned.scan_status == "unscanned"
    assert unscanned.failure_reason == "tracked_worktree_modified"
    assert unscanned.inventory_sha256 is None
    assert unscanned.fixture_paths == []


def test_dynamic_python_all_is_not_promoted_to_public_surface(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/acme/__init__.py",
        '__all__ = [name for name in globals() if not name.startswith("_")]\n',
    )

    assert curated_repository_fact_candidates(tmp_path, "abc123", None) == []


def test_readme_example_with_unverified_api_is_retained_only_as_withheld_evidence(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "src/acme/__init__.py", '__all__ = ["Document"]\n')
    _write(tmp_path, "src/acme/model.py", "class Document:\n    pass\n")
    _write(
        tmp_path,
        "README.md",
        """
# Acme

## Quick Start

### Unsupported workflow

```python
from acme.model import Document

document = Document.open("input.bin")
```
""".strip()
        + "\n",
    )

    result = verified_readme_examples(
        tmp_path,
        {
            "modules": [{"module": "acme.model", "exports": ["Document"]}],
            "classes": [
                {
                    "module": "acme.model",
                    "name": "Document",
                    "source_path": "src/acme/model.py",
                    "members": [],
                }
            ],
            "functions": [],
        },
    )

    assert result is not None
    value, locations = result
    assert locations == ["README.md", "src/acme/model.py"]
    assert value["inline_examples"] == []
    withheld = value["withheld_inline_examples"]
    assert len(withheld) == 1
    assert withheld[0]["title"] == "Unsupported workflow"
    assert withheld[0]["code"].endswith('document = Document.open("input.bin")')
    assert withheld[0]["static_api_verified"] is False
    assert withheld[0]["execution_verified"] is False
    assert str(withheld[0]["validation_reason"]).startswith("unknown_product_member:")


def test_direct_quick_start_function_result_is_verified_from_public_api(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname = 'acme'\n[tool.setuptools.packages.find]\nwhere = ['src']\n",
    )
    _write(
        tmp_path,
        "src/acme/__init__.py",
        "from acme.api import create\nfrom acme.result import Result\n\n"
        '__all__ = ["Result", "create"]\n',
    )
    _write(
        tmp_path,
        "src/acme/api.py",
        "from acme.result import Result\n\n"
        "def create(value: str) -> Result:\n"
        "    return Result()\n",
    )
    _write(
        tmp_path,
        "src/acme/result.py",
        "class Result:\n"
        "    def to_svg(self) -> str:\n"
        "        return '<svg/>'\n\n"
        "    def to_png(self) -> bytes:\n"
        "        return b'png'\n",
    )
    _write(
        tmp_path,
        "README.md",
        """
# Acme

## Quick Start

```python
from acme import create

result = create("hello")
svg = result.to_svg()
png = result.to_png()
```
""".strip()
        + "\n",
    )

    facts = curated_repository_fact_candidates(tmp_path, "abc123", None)
    selected = {fact.field: fact for fact in facts}

    functions = selected["api.public_surface"].value["functions"]
    assert functions == [
        {
            "module": "acme",
            "name": "create",
            "return_class": "acme.result:Result",
            "source_path": "src/acme/api.py",
            "source_sha256": functions[0]["source_sha256"],
        }
    ]
    example = selected["repository.examples"].value["inline_examples"][0]
    assert example["title"] == "Quick Start"
    assert example["static_api_verified"] is True
    assert "result.to_svg()" in example["code"]


def test_direct_public_scalar_function_and_safe_str_are_verified(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname = 'acme'\n[tool.setuptools.packages.find]\nwhere = ['src']\n",
    )
    _write(
        tmp_path,
        "src/acme/__init__.py",
        "from .api import render\n\n__all__ = ['render']\n",
    )
    _write(
        tmp_path,
        "src/acme/api.py",
        "def render(value: object) -> str:\n    return str(value)\n",
    )
    _write(
        tmp_path,
        "README.md",
        "# Acme\n\n## Quick Start\n\n"
        "```python\nfrom acme import render\nprint(str(render('hello')))\n```\n",
    )

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "abc123", None)
    }

    assert selected["api.public_surface"].value["functions"][0]["return_class"] is None
    example = selected["repository.examples"].value["inline_examples"][0]
    assert example["static_api_verified"] is True


def test_name_only_internal_function_stays_in_catalog_but_not_readme_projection(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname = 'acme'\n[tool.setuptools.packages.find]\nwhere = ['src']\n",
    )
    _write(
        tmp_path,
        "src/acme/__init__.py",
        "from .public import PublicThing\n__all__ = ['PublicThing']\n",
    )
    _write(tmp_path, "src/acme/public.py", "class PublicThing:\n    pass\n")
    _write(
        tmp_path,
        "src/acme/internal.py",
        "def write_output(value: object) -> bytes:\n    return b'output'\n",
    )

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "abc123", None)
    }
    value = selected["api.public_surface"].value
    projected = {(row["module"], export) for row in value["modules"] for export in row["exports"]}
    catalog = {
        (row["module"], export)
        for row in value["coordinate_catalog"]["modules"]
        for export in row["exports"]
    }

    assert ("acme", "PublicThing") in projected
    assert ("acme.internal", "write_output") not in projected
    assert ("acme.internal", "write_output") in catalog
    assert value["coordinate_catalog"]["presentation_exclusions"] == [
        {
            "qualified_name": "acme.internal.write_output",
            "import_module": "acme.internal",
            "name": "write_output",
            "kind": "function",
            "source_path": "src/acme/internal.py",
            "source_line": 1,
            "reason": "name_only_symbol_without_package_export_or_verified_consumer_import",
        }
    ]


def test_python_public_surface_projects_exact_inherited_api_semantics(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname = 'acme'\n[tool.setuptools.packages.find]\nwhere = ['src']\n",
    )
    _write(
        tmp_path,
        "src/acme/__init__.py",
        "from .model import Child\n__all__ = ['Child']\n",
    )
    _write(
        tmp_path,
        "src/acme/model.py",
        "class Base:\n"
        "    def __init__(self, path: str, strict=False) -> None:\n"
        "        self.path = path\n"
        "    def save(self, target: str) -> bool:\n"
        "        return True\n\n"
        "class Child(Base):\n"
        "    def inspect(self) -> dict[str, int]:\n"
        "        return {}\n",
    )

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "abc123", None)
    }
    classes = selected["api.public_surface"].value["classes"]
    child = next(item for item in classes if item["name"] == "Child")

    assert child["bases"] == ["Base"]
    assert child["constructor"] == {
        "surface": "Base(path, strict=False)",
        "line": 2,
        "source_path": "src/acme/model.py",
        "source_sha256": child["constructor"]["source_sha256"],
        "parameters": [
            {
                "name": "path",
                "kind": "positional",
                "annotation": "str",
                "default": None,
            },
            {
                "name": "strict",
                "kind": "positional",
                "annotation": None,
                "default": "False",
            },
        ],
        "return_annotation": "None",
        "declared_by": "Base",
        "inherited": True,
    }
    members = {item["name"]: item for item in child["members"]}
    assert members["inspect"]["return_annotation"] == "dict[str, int]"
    assert members["inspect"]["declared_by"] == "Child"
    assert members["inspect"]["inherited"] is False
    assert members["save"]["return_annotation"] == "bool"
    assert members["save"]["declared_by"] == "Base"
    assert members["save"]["inherited"] is True


def test_root_layout_public_surface_uses_distributed_packages_and_exact_hashes(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\n"
        "setup(name='widget-foss', packages=['acme', 'acme.widget'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "from . import widget\n__all__ = ['widget']\n")
    _write(
        tmp_path,
        "acme/widget/__init__.py",
        "from .document import Document\n__all__ = ['Document']\n",
    )
    _write(
        tmp_path,
        "acme/widget/document.py",
        "class Document:\n    def save(self, target='output.bin') -> None:\n        return None\n",
    )
    _write(tmp_path, "tests/not_distributed.py", "class InternalTool: pass\n")

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "root-revision", None)
    }

    surface = selected["api.public_surface"]
    assert surface.source.source_revision == "root-revision"
    modules = {item["module"]: item for item in surface.value["modules"]}
    assert modules["acme.widget"]["exports"] == ["Document"]
    assert all(module != "tests.not_distributed" for module in modules)
    assert (
        modules["acme.widget"]["source_sha256"]
        == hashlib.sha256((tmp_path / "acme/widget/__init__.py").read_bytes()).hexdigest()
    )
    document = next(item for item in surface.value["classes"] if item["name"] == "Document")
    assert document["module"] == "acme.widget"
    assert document["source_path"] == "acme/widget/document.py"
    assert (
        document["source_sha256"]
        == hashlib.sha256((tmp_path / "acme/widget/document.py").read_bytes()).hexdigest()
    )
    assert document["members"][0]["surface"] == "save(target='output.bin')"


def test_root_layout_readme_example_binds_constructed_public_class(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\n"
        "setup(name='widget-foss', packages=['acme', 'acme.widget'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "")
    _write(tmp_path, "acme/widget/__init__.py", "from .Document import Document\n")
    _write(
        tmp_path,
        "acme/widget/Document.py",
        "class Document:\n    def save(self, target='output.bin') -> None:\n        return None\n",
    )
    _write(
        tmp_path,
        "README.md",
        "# Widget\n\n"
        "## Quick start\n\n"
        "```python\n"
        "from acme.widget import Document\n\n"
        "document = Document()\n"
        "document.save('output.bin')\n"
        "```\n",
    )

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "root-example", None)
    }

    inline = selected["repository.examples"].value["inline_examples"]
    assert len(inline) == 1
    assert inline[0]["static_api_verified"] is True
    assert inline[0]["evidence_modules"] == ["acme.widget"]


def test_generated_binding_nested_names_project_members_without_duplicating_class(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\nsetup(name='acme', packages=['acme'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "from .Camera import Camera\n__all__ = ['Camera']\n")
    _write(
        tmp_path,
        "acme/Camera.py",
        "class Camera:\n    @property\n    def near_plane(self) -> float:\n        return 0.1\n",
    )

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "nested", None)
    }
    classes = selected["api.public_surface"].value["classes"]
    cameras = [item for item in classes if item["name"] == "Camera"]
    assert len(cameras) == 1
    assert cameras[0]["members"] == [
        {
            "name": "near_plane",
            "kind": "property",
            "surface": "near_plane: float",
            "return_annotation": "float",
            "declared_by": "Camera",
            "inherited": False,
            "source_path": "acme/Camera.py",
            "source_sha256": hashlib.sha256((tmp_path / "acme/Camera.py").read_bytes()).hexdigest(),
            "line": 3,
        }
    ]


def test_ambiguous_same_named_classes_fail_closed_from_class_projection(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\nsetup(name='acme', packages=['acme'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "__all__ = []\n")
    _write(tmp_path, "acme/one.py", "class Widget:\n    def one(self): pass\n")
    _write(tmp_path, "acme/two.py", "class Widget:\n    def two(self): pass\n")

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "ambiguous", None)
    }

    assert all(item["name"] != "Widget" for item in selected["api.public_surface"].value["classes"])
    assert selected["api.public_surface"].value["inventory_counts"]["ambiguous_classes"] == 1


def test_public_surface_projection_is_hard_bounded_for_large_generated_api(tmp_path: Path) -> None:
    class_names = [f"Type{index:02d}" for index in range(70)]
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\nsetup(name='acme', packages=['acme'])\n",
    )
    _write(
        tmp_path,
        "acme/__init__.py",
        "from .models import " + ", ".join(class_names) + "\n__all__ = " + repr(class_names) + "\n",
    )
    _write(
        tmp_path,
        "acme/models.py",
        "\n\n".join(
            f"class {name}:\n"
            + "\n".join(f"    def method_{member:02d}(self): pass" for member in range(30))
            for name in class_names
        )
        + "\n",
    )

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "large", None)
    }
    value = selected["api.public_surface"].value
    prompt_projection = {key: item for key, item in value.items() if key != "coordinate_catalog"}
    encoded = json.dumps(prompt_projection, sort_keys=True, separators=(",", ":")).encode()

    assert value["projection_truncated"] is True
    assert len(value["modules"]) <= value["projection_limits"]["modules"]
    assert len(value["classes"]) <= value["projection_limits"]["classes"]
    assert all(
        len(item["members"]) <= value["projection_limits"]["members_per_class"]
        for item in value["classes"]
    )
    assert len(encoded) <= value["projection_limits"]["json_bytes"]
    assert value["package_namespaces"] == ["acme"]
    assert value["coordinate_catalog"]["content_sha256"]


def test_readme_example_validation_uses_complete_coordinate_catalog(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "README.md",
        "# Acme\n\n## Usage\n\n```python\nfrom acme import Hidden\nHidden().merge()\n```\n",
    )
    projected = {
        "modules": [{"module": "acme", "exports": ["Visible"]}],
        "classes": [
            {
                "module": "acme",
                "name": "Visible",
                "source_path": "src/acme/visible.py",
                "members": [],
            }
        ],
        "coordinate_catalog": {
            "modules": [{"module": "acme", "exports": ["Hidden", "Visible"]}],
            "classes": [
                {
                    "module": "acme",
                    "name": "Hidden",
                    "source_path": "src/acme/hidden.py",
                    "members": [{"name": "merge", "surface": "merge()"}],
                },
                {
                    "module": "acme",
                    "name": "Visible",
                    "source_path": "src/acme/visible.py",
                    "members": [],
                },
            ],
            "functions": [],
            "content_sha256": "catalog-hash",
        },
    }

    curated = verified_readme_examples(tmp_path, projected)

    assert curated is not None
    assert [item["title"] for item in curated[0]["inline_examples"]] == ["Usage"]
    assert curated[0]["inline_examples"][0]["evidence_modules"] == ["acme"]
    assert "src/acme/hidden.py" in curated[1]


def test_readme_example_validation_allows_explicit_runtime_failure_guard() -> None:
    code = (
        "from acme import Widget\n"
        "widget = Widget()\n"
        "if not widget.render():\n"
        '    raise RuntimeError("render failed")\n'
    )

    accepted, modules, reason = validate_python_example(code, _example_surface())

    assert accepted is True
    assert modules == ("acme",)
    assert reason == "accepted"


def test_direct_quick_start_rejects_unknown_calls_and_methods(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/acme/__init__.py",
        "from acme.api import create\nfrom acme.result import Result\n\n"
        '__all__ = ["Result", "create"]\n',
    )
    _write(
        tmp_path,
        "src/acme/api.py",
        "from acme.result import Result\n\ndef create() -> Result:\n    return Result()\n",
    )
    _write(tmp_path, "src/acme/result.py", "class Result:\n    def save(self): pass\n")
    for code in (
        "from acme import create\nresult = create()\nresult.unknown()\n",
        "from acme import create\nresult = create()\nmystery()\n",
        'from acme import create\nresult = create()\neval("result.save()")\n',
    ):
        _write(
            tmp_path,
            "README.md",
            f"# Acme\n\n## Usage\n\n```python\n{code}```\n",
        )

        facts = curated_repository_fact_candidates(tmp_path, "abc123", None)

        assert all(fact.field != "repository.examples" for fact in facts)


def test_additional_examples_h2_and_h3_blocks_are_discovered_and_verified() -> None:
    readme = """# Acme

## Additional examples

```python
from acme import Widget
widget = Widget()
widget.render()
```

### Save a widget

```python
from acme import Widget
widget = Widget()
widget.save("output.bin")
```
"""

    examples, decisions = verified_python_examples(readme, _example_surface())

    assert [example["title"] for example in examples] == [
        "Additional examples",
        "Save a widget",
    ]
    assert [decision.accepted for decision in decisions] == [True, True]
    assert all(example["evidence_modules"] == ["acme"] for example in examples)


def test_follow_on_example_uses_prior_imports_within_the_same_section() -> None:
    readme = """# Acme

## Quick Start

### Render Variants

```python
from acme import Widget
widget = Widget()
widget.render()
```

```python
widget = Widget()
widget.save("output.bin")
```
"""

    examples, decisions = verified_python_examples(readme, _example_surface())

    assert len(examples) == 2
    assert [decision.reason for decision in decisions] == [
        "accepted",
        "accepted_with_section_import_context",
    ]
    assert examples[1]["validation_context_imports"] == ["from acme import Widget"]


def test_classmethod_return_annotation_controls_chained_api_validation() -> None:
    surface = {
        "modules": [
            {"module": "acme", "exports": ["Builder", "Result"]},
        ],
        "classes": [
            {
                "module": "acme",
                "name": "Builder",
                "source_path": "src/acme/builder.py",
                "members": [
                    {
                        "name": "build",
                        "surface": "build(value)",
                        "return_annotation": "Result",
                    }
                ],
            },
            {
                "module": "acme",
                "name": "Result",
                "source_path": "src/acme/result.py",
                "members": [
                    {"name": "write_to", "surface": "write_to(path)", "return_annotation": None}
                ],
            },
        ],
        "functions": [],
    }
    readme = """# Acme

## Quick Start

```python
from acme import Builder
result = Builder.build("input.bin")
result.write_to("output.bin")
```
"""

    examples, decisions = verified_python_examples(readme, surface)

    assert len(examples) == 1
    assert decisions[0].accepted is True
    assert decisions[0].reason == "accepted"


def test_file_factory_narrows_base_result_only_to_unique_suffix_named_subtype() -> None:
    surface = {
        "modules": [{"module": "acme", "exports": ["AssetLoader"]}],
        "classes": [
            {
                "module": "acme",
                "name": "AssetLoader",
                "source_path": "src/acme/loader.py",
                "members": [
                    {"name": "open", "surface": "open(path)", "return_annotation": "Asset"}
                ],
            },
            {
                "module": "acme",
                "name": "Asset",
                "source_path": "src/acme/base.py",
                "members": [{"name": "save", "surface": "save(path)", "return_annotation": None}],
            },
            {
                "module": "acme",
                "name": "TtfAsset",
                "source_path": "src/acme/ttf.py",
                "bases": ["Asset"],
                "members": [
                    {
                        "name": "instantiate",
                        "surface": "instantiate(values)",
                        "return_annotation": "TtfAsset",
                    },
                    {"name": "save", "surface": "save(path)", "return_annotation": None},
                ],
            },
        ],
        "functions": [],
    }
    readme = """# Acme

## Quick Start

```python
from acme import AssetLoader
asset = AssetLoader.open("font.ttf")
instance = asset.instantiate({"weight": 700})
instance.save("output.ttf")
```
"""

    examples, decisions = verified_python_examples(readme, surface)

    assert len(examples) == 1
    assert decisions[0].accepted is True

    unmatched = readme.replace("font.ttf", "font.bin")
    unmatched_examples, unmatched_decisions = verified_python_examples(unmatched, surface)
    assert unmatched_examples == []
    assert unmatched_decisions[0].reason == "unknown_product_member:Asset.instantiate"


def test_decorated_and_product_specific_example_headings_are_discovered() -> None:
    readme = """# Acme

## 🚀 Quick start

```python
from acme import Widget
widget = Widget()
widget.render()
```

## Acme document examples

### Save a widget

```python
from acme import Widget
widget = Widget()
widget.save("output.bin")
```
"""

    examples, decisions = verified_python_examples(readme, _example_surface())

    assert [example["title"] for example in examples] == ["🚀 Quick start", "Save a widget"]
    assert [decision.accepted for decision in decisions] == [True, True]


def test_python_readme_example_validation_fails_closed_with_specific_reasons() -> None:
    surface = _example_surface()
    cases = {
        "unknown member": (
            "from acme import Widget\nwidget = Widget()\nwidget.unknown\n",
            "unknown_product_member:Widget.unknown",
        ),
        "unknown chained member": (
            "from acme import Widget\nwidget = Widget()\nwidget.factory().save('x')\n",
            "unresolved_chained_product_member:Widget.save",
        ),
        "unsafe call": (
            "from acme import Widget\nwidget = Widget()\neval('widget.render()')\n",
            "unsafe_call:eval",
        ),
        "malformed code": (
            "from acme import Widget\nwidget = Widget(\n",
            "malformed_python",
        ),
        "cross-module spoof": (
            "from acme.fake import Widget\nwidget = Widget()\nwidget.render()\n",
            "unknown_product_import:acme.fake.Widget",
        ),
    }

    for code, expected_reason in cases.values():
        accepted, modules, reason = validate_python_example(code, surface)

        assert accepted is False
        assert modules == ()
        assert reason == expected_reason


def test_stdlib_example_operations_are_allowlisted_but_do_not_prove_product_api() -> None:
    accepted, modules, reason = validate_python_example(
        "import io\nfrom acme import Widget\n"
        "widget = Widget()\nstream = io.BytesIO()\nwidget.save(stream)\n"
        "stream.seek(0)\nprint(len(stream.read()))\n",
        _example_surface(),
    )

    assert accepted is True
    assert modules == ("acme",)
    assert reason == "accepted"


def test_reexported_class_generic_children_and_safe_pathlib_are_resolved() -> None:
    surface = {
        "modules": [
            {"module": "acme", "exports": ["Document", "Page"]},
            {"module": "acme.saving", "exports": ["Options"]},
        ],
        "classes": [
            {
                "module": "acme",
                "name": "Document",
                "source_path": "src/acme/model.py",
                "members": [{"name": "GetChildNodes", "surface": "GetChildNodes(node_type)"}],
            },
            {
                "module": "acme",
                "name": "Page",
                "source_path": "src/acme/model.py",
                "members": [{"name": "Title", "surface": "Title: str | None"}],
            },
            {
                "module": "acme",
                "name": "Options",
                "source_path": "src/acme/model.py",
                "members": [],
            },
        ],
        "functions": [],
    }
    code = """from pathlib import Path
from acme import Document, Page
from acme.saving import Options

doc = Document(Path("input.bin").open("rb"))
options = Options()
for page in doc.GetChildNodes(Page):
    print(page.Title)
print(len(list(doc)), options)
"""

    accepted, modules, reason = validate_python_example(code, surface)

    assert accepted is True
    assert modules == ("acme", "acme.saving")
    assert reason == "accepted"


def test_local_subclass_of_public_visitor_is_safe_to_construct() -> None:
    surface = {
        "modules": [{"module": "acme", "exports": ["Document", "Visitor"]}],
        "classes": [
            {
                "module": "acme",
                "name": "Document",
                "source_path": "src/acme/model.py",
                "members": [{"name": "Accept", "surface": "Accept(visitor)"}],
            },
            {
                "module": "acme",
                "name": "Visitor",
                "source_path": "src/acme/model.py",
                "members": [],
            },
        ],
        "functions": [],
    }
    code = """from acme import Document, Visitor

class Counter(Visitor):
    pass

doc = Document()
doc.Accept(Counter())
"""

    accepted, modules, reason = validate_python_example(code, surface)

    assert accepted is True
    assert modules == ("acme",)
    assert reason == "accepted"


def test_constraint_extraction_is_product_neutral_and_source_bound(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/widget/core.py",
        'description = "Only PDF save is supported"\n'
        'raise WidgetConstraint("Only XML output is supported")\n'
        'raise WidgetConstraint("Input archive requires an index")\n',
    )

    facts = curated_repository_fact_candidates(tmp_path, "abc123", None)
    limitations = next(fact for fact in facts if fact.field == "product.limitations")

    assert [row["statement"] for row in limitations.value] == [
        "Only XML output is supported",
        "Input archive requires an index",
    ]


def test_root_layout_development_and_concrete_limitations_are_manifest_bound(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\nsetup(name='acme', packages=['acme'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "")
    _write(
        tmp_path,
        "acme/features.py",
        "class BaseShape:\n"
        "    def convert(self):\n"
        "        raise NotImplementedError('conversion is not implemented')\n\n"
        "class ConcreteShape(BaseShape):\n"
        "    def convert(self):\n"
        "        return 'mesh'\n\n"
        "class AbstractThing:\n"
        "    def convert(self):\n"
        "        raise NotImplementedError('Abstract conversion is not implemented')\n\n"
        "class IShape:\n"
        "    def convert(self):\n"
        "        raise NotImplementedError('conversion is not implemented')\n\n"
        "class EntityRenderer:\n"
        "    '''Base class for rendering entities.'''\n"
        "    def render(self):\n"
        "        raise NotImplementedError('EntityRenderer.render is not implemented')\n\n"
        "class Mesh:\n"
        "    def do_boolean(self):\n"
        "        raise NotImplementedError('Mesh boolean union is not implemented')\n\n"
        "class NurbsSurface:\n"
        "    def evaluate(self):\n"
        "        raise NotImplementedError('NURBS surface evaluation is not implemented')\n\n"
        "class Scene:\n"
        "    def render(self):\n"
        "        raise NotImplementedError('Scene render is not implemented')\n",
    )
    _write(
        tmp_path,
        "tests/test_features.py",
        "import unittest\n\nclass FeatureTests(unittest.TestCase):\n    pass\n",
    )
    _write(
        tmp_path,
        "tests/spoof.py",
        "raise NotImplementedError('Repository-wide export is not implemented')\n",
    )

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "root-truth", None)
    }

    commands = selected["development.commands"].value["entries"]
    assert [item["command"] for item in commands] == [
        "python -m pip install -e .",
        'python -m unittest discover -s tests -p "test_*.py"',
    ]
    assert all(item["evidence_kind"] == "source_derived" for item in commands)
    assert all(item["execution_verified"] is False for item in commands)
    assert commands[0]["sources"][0]["path"] == "setup.py"
    assert len(commands[0]["sources"][0]["sha256"]) == 64
    statements = [item["statement"] for item in selected["product.limitations"].value]
    assert statements == [
        "Mesh boolean union is not implemented",
        "NURBS surface evaluation is not implemented",
        "Scene render is not implemented",
    ]
    assert all(item["path"] == "acme/features.py" for item in selected["product.limitations"].value)


def test_src_layout_commands_and_limitations_ignore_undeclared_spoof_package(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname='acme'\n"
        "[project.optional-dependencies]\ntest=['pytest>=8']\n"
        "[tool.setuptools.packages.find]\nwhere=['src']\ninclude=['acme*']\n",
    )
    _write(tmp_path, "src/acme/__init__.py", "")
    _write(
        tmp_path,
        "src/acme/feature.py",
        "def export():\n    raise NotImplementedError('Mesh export is not implemented')\n",
    )
    _write(
        tmp_path,
        "src/spoof/feature.py",
        "def export():\n    raise NotImplementedError('Every format is unsupported')\n",
    )
    _write(tmp_path, "tests/test_feature.py", "def test_feature():\n    assert True\n")

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "src-truth", None)
    }

    commands = selected["development.commands"].value["entries"]
    assert [item["command"] for item in commands] == [
        "python -m pip install -e .",
        "python -m pytest tests",
    ]
    limitations = selected["product.limitations"].value
    assert [item["statement"] for item in limitations] == ["Mesh export is not implemented"]
    assert limitations[0]["path"] == "src/acme/feature.py"


def test_python_truth_fails_closed_for_absent_or_malformed_distribution_metadata(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "setup.py", "this is not valid Python !!!\n")
    _write(
        tmp_path,
        "src/acme/feature.py",
        "def export():\n    raise NotImplementedError('Mesh export is not implemented')\n",
    )
    _write(tmp_path, "tests/test_feature.py", "import unittest\n")

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "malformed-layout", None)
    }

    assert "development.commands" not in selected
    assert "product.limitations" not in selected

    absent = tmp_path / "absent"
    _write(
        absent,
        "acme/feature.py",
        "def export():\n    raise NotImplementedError('Mesh export is not implemented')\n",
    )
    absent_selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(absent, "absent-layout", None)
    }
    assert "development.commands" not in absent_selected
    assert "product.limitations" not in absent_selected


def test_source_limitations_are_deduplicated_and_bounded(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\nsetup(name='acme', packages=['acme'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "")
    statements = [f"Capability {index} is not implemented" for index in range(15)]
    body = "\n\n".join(
        f"def capability_{index}():\n    raise NotImplementedError({statement!r})"
        for index, statement in enumerate(statements)
    )
    body += (
        "\n\ndef duplicate():\n    raise NotImplementedError('Capability 0 is not implemented')\n"
    )
    _write(tmp_path, "acme/features.py", body)

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "bounded", None)
    }
    limitations = selected["product.limitations"].value

    assert len(limitations) == 10
    assert len({item["statement"] for item in limitations}) == 10


def test_source_guidance_omits_incomplete_and_duplicate_rendering_notices(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "setup.py",
        "from setuptools import setup\nsetup(name='acme', packages=['acme'])\n",
    )
    _write(tmp_path, "acme/__init__.py", "")
    _write(
        tmp_path,
        "acme/Scene.py",
        '"""Rendering is not supported in this package."""\n'
        "class Scene:\n"
        "    def render(self):\n"
        "        raise NotImplementedError('render is not implemented')\n",
    )
    _write(
        tmp_path,
        "acme/Renderer.py",
        "class Renderer:\n"
        "    def render(self):\n"
        "        raise NotImplementedError('Renderer.render is not implemented')\n"
        "\nNOTICE = 'Unsupported data type for Widget:'\n",
    )

    selected = {
        fact.field: fact for fact in curated_repository_fact_candidates(tmp_path, "rendering", None)
    }
    limitations = selected["product.limitations"].value
    statements = [item["statement"] for item in limitations]

    assert statements == ["Scene and renderer output generation are not implemented."]


def test_page_dependencies_and_focused_mcp_command_are_source_bound(tmp_path: Path) -> None:
    _write(tmp_path, "pyproject.toml", "[project]\nname='page'\ndependencies=[]\n")
    _write(
        tmp_path,
        "src/aspose/page/mcp/server.py",
        "def create_server():\n    from fastmcp import FastMCP\n    return FastMCP('Page')\n",
    )
    _write(
        tmp_path,
        "src/aspose/page/image/skia_raster_writer.py",
        '"""Image renderer (requires skia-python)."""\nimport skia\n',
    )
    _write(tmp_path, "tests/mcp/test_handlers.py", "def test_handlers(): pass\n")
    _write(tmp_path, "tests/mcp/test_server.py", "def test_server(): pass\n")

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "page-revision", None)
    }

    dependencies = selected["installation.capability_dependencies"]
    assert [item["distribution"] for item in dependencies.value["entries"]] == [
        "fastmcp",
        "skia-python",
    ]
    assert all(item["source_sha256"] for item in dependencies.value["entries"])
    command = selected["development.commands"].value["entries"][0]
    assert command["command"] == (
        "python -m unittest tests.mcp.test_handlers tests.mcp.test_server"
    )
    assert [item["path"] for item in command["sources"]] == [
        "tests/mcp/test_handlers.py",
        "tests/mcp/test_server.py",
    ]


def test_pdf_distribution_guidance_constraints_and_security_are_repository_derived(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "aspose-pdf-foss-for-python"
requires-python = ">=3.11"
dependencies = ["cryptography>=42", "asn1crypto>=1.5"]
classifiers = ["Development Status :: 3 - Alpha", "Typing :: Typed"]
""".strip(),
    )
    _write(tmp_path, "src/aspose_pdf/py.typed", "")
    _write(
        tmp_path,
        "src/aspose_pdf/pdfa.py",
        'NOTICE = "PDF/A validation is heuristic, not certification-grade conformance."\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/document.py",
        'def replace_text():\n    """This operation does not perform layout reflow."""\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/load_limits.py",
        """
from dataclasses import dataclass

@dataclass
class PdfLoadLimits:
    max_input_bytes: int | None = 1

    @classmethod
    def unlimited(cls):
        return cls(max_input_bytes=None)
""".strip(),
    )
    _write(tmp_path, "supported-features.md", "# Supported features\n")
    _write(
        tmp_path,
        "SECURITY.md",
        "Use https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Python/"
        "security/advisories/new for private reports.\n",
    )
    _write(
        tmp_path,
        "scripts/check.sh",
        "#!/usr/bin/env bash\npython -m ruff check src/\npython -m pytest -q\n",
    )
    _write(tmp_path, "scripts/build.sh", "#!/usr/bin/env bash\npython -m build\n")

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "pdf-revision", None)
    }

    distribution = selected["python.distribution"].value
    assert distribution["runtime_dependencies"] == ["cryptography>=42", "asn1crypto>=1.5"]
    assert distribution["development_status"] == "Alpha"
    assert distribution["typed_marker"]["path"] == "src/aspose_pdf/py.typed"
    assert selected["repository.documentation_assets"].value["entries"][0]["path"] == (
        "supported-features.md"
    )
    statements = [item["statement"] for item in selected["product.limitations"].value]
    assert "PDF/A validation is heuristic, not certification-grade conformance." in statements
    assert "This operation does not perform layout reflow." in statements
    assert (
        selected["repository.security_guidance"]
        .value["policy"]["private_reporting_url"]
        .endswith("/security/advisories/new")
    )
    assert selected["repository.contribution_guidance"].value["validation_scripts"]
    assert [item["command"] for item in selected["development.commands"].value["entries"]] == [
        "scripts/build.sh",
        "scripts/check.sh",
        "python -m pip install -e .",
    ]


def test_pdf_detail_projection_requires_source_apis_tests_and_authoritative_boundaries(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "src/aspose_pdf/document.py",
        '''
class Document:
    def __init__(self, source=None, *, limits=None): pass
    @classmethod
    def open_streaming(cls, source, *, limits=None): pass
    def load_from(self, source, *, limits=None): pass
    def save(self, target): pass
    def merge(self, other): pass
    def validate(self): pass
    def info(self): pass
    def xmp_metadata(self): pass
    def outlines(self): pass
    def encrypt(self, password): pass
    def decrypt(self, password): pass
    def optimize(self): pass
    def optimize_resources(self): pass
    def compress_streams(self): pass
    def validate_pdfa(self): pass
    def validate_pdfua(self): pass
    def convert_to_pdfa(self): pass
    def convert_to_pdfua(self): pass
    def add_attachment(self): pass
    def replace_text(self):
        """This operation does not perform layout reflow."""

LOAD_CONTRACT = (
    "raw bytes, or a binary stream; missing password instead of yielding an empty document"
)
'''.strip(),
    )
    _write(
        tmp_path,
        "src/aspose_pdf/pages.py",
        '''
class Page:
    def add_text(self): pass
    def add_image(self): pass
    def draw_line(self): pass
    def draw_rectangle(self): pass
    def replace_text(self): pass
    def redact_text(self): pass
    def render(self):
        """The renderer is dependency-free and supports common page content."""
    def save_as_image(self): pass
'''.strip(),
    )
    _write(
        tmp_path,
        "src/aspose_pdf/facades.py",
        """
class PdfExtractor:
    def extract_text(self): pass
    def get_text(self): pass
    def extract_image(self): pass
    def extract_attachment(self): pass

class PdfFileEditor:
    def concatenate(self): pass
    def extract(self): pass
    def insert(self): pass
    def delete(self): pass
    def append(self): pass
""".strip(),
    )
    _write(
        tmp_path,
        "src/aspose_pdf/forms.py",
        "class Form:\n"
        "    def add_text_field(self): pass\n"
        "    def add_checkbox(self): pass\n"
        "    def add_radio_group(self): pass\n"
        "    def flatten(self): pass\n",
    )
    _write(
        tmp_path,
        "src/aspose_pdf/annotations/__init__.py",
        "class AnnotationCollection:\n"
        "    def add(self): pass\n"
        "    def insert(self): pass\n"
        "    def delete(self): pass\n"
        "    def clear(self): pass\n",
    )
    _write(
        tmp_path,
        "src/aspose_pdf/load_limits.py",
        """
class PdfLoadLimits:
    max_input_bytes: int | None = 1024
    @classmethod
    def unlimited(cls): return cls()
""".strip(),
    )
    _write(tmp_path, "src/aspose_pdf/text_layout.py", "class TextLayoutOptions:\n    pass\n")
    _write(
        tmp_path,
        "src/aspose_pdf/pdfa.py",
        'NOTICE = "not certification-grade PDF/A conformance"\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/pdfua.py",
        'NOTICE = "not certification-grade PDF/UA conformance"\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/signature.py",
        'NOTICE = "does **not** perform full PKCS#7 certificate chain checking"\n'
        "class PdfSignature:\n"
        "    def valid(self): pass\n"
        "    def validate(self): pass\n",
    )
    _write(
        tmp_path,
        "src/aspose_pdf/exceptions.py",
        "class UnsupportedFeature(Exception):\n"
        '    """Raised when a compatibility surface names a feature this package lacks."""\n',
    )
    _write(tmp_path, "tests/test_page_rendering.py", 'png = "page.png"\ntiff = "page.tiff"\n')
    _write(
        tmp_path,
        "src/aspose_pdf/engine/encryption.py",
        'CONTRACT = "AES-CBC, RC4 encryption"\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/engine/font_authoring.py",
        'CONTRACT = "FontEmbeddingException and /ToUnicode"\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/engine/text_layout.py",
        'CONTRACT = "TextLayoutOptions preserve shaped visual order"\n',
    )
    _write(tmp_path, "src/aspose_pdf/py.typed", "")
    _write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname = "aspose-pdf-foss"\nclassifiers = ["Development Status :: 3 - Alpha"]\n',
    )
    _write(tmp_path, "SECURITY.md", "Report security issues privately.\n")
    _write(
        tmp_path,
        "supported-features.md",
        "The contract is the active `tests/test_*.py` suite.\n"
        "Layout reflow remains out of scope in this prerelease.\n"
        "OCR is not implemented.\n"
        "These are heuristic signals, not certification-grade results.\n"
        "Lazy opening still defers page-content decoding.\n"
        "`PdfLoadLimits.unlimited()` returns a policy with every field disabled.\n"
        "The limits reduce risk; they are not a proof of complete isolation.\n"
        "Run highly hostile documents in an isolated worker.\n"
        "Positioned Standard-14 text or embedded Unicode text with `Page.add_text()`.\n"
        "The Unicode bidi algorithm shapes mixed-direction text.\n",
    )

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "pdf-revision", None)
    }

    details = selected["repository.capability_details"].value
    labels = {item["label"] for item in details["capability_groups"]}
    assert len(details["capability_groups"]) == 13
    assert "Create and inspect PDF signatures" in labels
    assert "Optimize streams, images, fonts, and unused objects" in labels
    assert "Encrypt and decrypt documents with RC4 or AES" in labels
    assert any(label.startswith("Add Standard-14") for label in labels)
    assert details["input_formats"] == ["PDF"]
    assert details["output_formats"] == ["PDF", "PNG", "TIFF"]
    boundaries = selected["repository.verified_boundaries"].value
    assert len(boundaries["boundaries"]) == 6
    assert all(len(item["sha256"]) == 64 for item in boundaries["evidence"])
    guidance = selected["repository.public_guidance"].value
    assert len(guidance) == 8
    assert all(isinstance(statement, str) and statement for statement in guidance)
    security = selected["repository.security_guidance"].value
    assert security["resource_limits"]["bounded_defaults"] is True
    assert security["resource_limits"]["entry_points"] == [
        "__init__",
        "load_from",
        "open_streaming",
    ]
    assert security["operational_guidance"]["limits_are_not_a_complete_dos_sandbox"] is True
