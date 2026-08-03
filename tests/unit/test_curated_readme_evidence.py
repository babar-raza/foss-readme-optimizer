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
    def encrypt(self, password): pass
    def decrypt(self, password): pass
    def optimize(self): pass
    def compress_streams(self): pass
    def validate_pdfa(self): pass
    def validate_pdfua(self): pass
    def convert_to_pdfa(self): pass
    def convert_to_pdfua(self): pass
    def replace_text(self):
        """This operation does not perform layout reflow."""
'''.strip(),
    )
    _write(
        tmp_path,
        "src/aspose_pdf/pages.py",
        '''
class Page:
    def add_text(self): pass
    def add_image(self): pass
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
        'NOTICE = "does **not** perform full PKCS#7 certificate chain checking"\n',
    )
    _write(
        tmp_path,
        "src/aspose_pdf/exceptions.py",
        "class UnsupportedFeature(Exception):\n"
        '    """Raised when a compatibility surface names a feature this package lacks."""\n',
    )
    _write(tmp_path, "tests/test_page_rendering.py", 'png = "page.png"\ntiff = "page.tiff"\n')
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
        "Run highly hostile documents in an isolated worker.\n",
    )

    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(tmp_path, "pdf-revision", None)
    }

    details = selected["repository.capability_details"].value
    assert len(details["capability_groups"]) == 9
    assert details["input_formats"] == ["PDF"]
    assert details["output_formats"] == ["PDF", "PNG", "TIFF"]
    boundaries = selected["repository.verified_boundaries"].value
    assert len(boundaries["boundaries"]) == 6
    assert all(len(item["sha256"]) == 64 for item in boundaries["evidence"])
    security = selected["repository.security_guidance"].value
    assert security["resource_limits"]["bounded_defaults"] is True
    assert security["resource_limits"]["entry_points"] == [
        "__init__",
        "load_from",
        "open_streaming",
    ]
    assert security["operational_guidance"]["limits_are_not_a_complete_dos_sandbox"] is True
