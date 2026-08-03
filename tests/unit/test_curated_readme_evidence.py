"""Repository-bound facts for valuable curated README detail."""

from pathlib import Path

from readme_agent.facts.curated_readme_evidence import curated_repository_fact_candidates


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        '__all__ = ["Document", "LoadOptions"]\n',
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
        "installation.optional_extras",
        "product.limitations",
        "repository.ci",
        "repository.examples",
        "repository.third_party_notices",
    }
    assert selected["api.public_surface"].value["modules"][0]["exports"] == [
        "Document",
        "LoadOptions",
    ]
    assert selected["api.public_surface"].value["mcp_server"]["tools"] == ["convert_widget"]
    assert selected["api.public_surface"].value["mcp_server"]["test_path"] == (
        "tests/mcp/test_server.py"
    )
    assert selected["installation.optional_extras"].value["extras"] == {
        "dev": ["build>=1.2"],
        "pdf": ["reportlab>=3.6"],
    }
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
    assert selected["product.limitations"].value[0]["line"] == 11
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


def test_dynamic_python_all_is_not_promoted_to_public_surface(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/acme/__init__.py",
        '__all__ = [name for name in globals() if not name.startswith("_")]\n',
    )

    assert curated_repository_fact_candidates(tmp_path, "abc123", None) == []


def test_readme_example_with_unverified_api_is_not_promoted(tmp_path: Path) -> None:
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

    facts = curated_repository_fact_candidates(tmp_path, "abc123", None)

    assert all(fact.field != "repository.examples" for fact in facts)


def test_direct_quick_start_function_result_is_verified_from_public_api(tmp_path: Path) -> None:
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


def test_constraint_extraction_is_product_neutral_and_raise_only(tmp_path: Path) -> None:
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
