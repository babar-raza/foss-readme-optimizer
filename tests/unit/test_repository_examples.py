"""Repository README examples remain untrusted until real local verification."""

from __future__ import annotations

import pytest

from readme_agent.facts.repository_examples import (
    repository_readme_example_candidates,
    repository_source_example_candidates,
)
from readme_agent.facts.rust_example_verifier import _resolve_declared_symbols


def test_extracts_only_bounded_language_matched_examples(tmp_path):
    (tmp_path / "README.md").write_text(
        """# Widget

```csharp
using Widget;
var item = new Item();
item.Save("out.bin");
```

```bash
dotnet test
```
""",
        encoding="utf-8",
    )

    candidates = repository_readme_example_candidates(
        tmp_path,
        "dotnet",
        supporting_paths=["src/Widget.cs"],
    )

    assert len(candidates) == 1
    assert candidates[0].class_name == "ReadmeExample"
    assert candidates[0].code.startswith("using Widget;")
    assert candidates[0].evidence_paths == ["README.md", "src/Widget.cs"]
    assert candidates[0].required_symbols == ["using Widget;"]


def test_unlabelled_and_wrong_language_blocks_are_not_candidates(tmp_path):
    (tmp_path / "README.md").write_text(
        "```\nprint('unlabelled')\n```\n\n```java\nclass Example {}\n```\n",
        encoding="utf-8",
    )

    assert repository_readme_example_candidates(tmp_path, "python") == []


def test_repository_authored_native_example_keeps_required_compiler_scaffolding(tmp_path):
    includes = "\n".join(f'#include "widget/header_{index}.h"' for index in range(30))
    source = f'{includes}\n\nint main() {{\n    Widget item;\n    item.Save("out.bin");\n}}\n'
    assert 600 < len(source) < 2_400
    (tmp_path / "README.md").write_text(
        f"# Widget\n\n```cpp\n{source}```\n",
        encoding="utf-8",
    )

    candidates = repository_readme_example_candidates(tmp_path, "cpp")

    assert len(candidates) == 1
    assert candidates[0].code == source


def test_python_typescript_and_rust_examples_expose_imported_public_symbol_anchors(tmp_path):
    cases = {
        "python": (
            "from aspose.threed import Scene, Node as PublicNode\n"
            "scene = Scene()\nnode = PublicNode()\n",
            ["Node", "Scene"],
        ),
        "typescript": (
            "import { Scene, Node as PublicNode } from '@aspose/3d';\nconst scene = new Scene();\n",
            ["Node", "Scene"],
        ),
        "rust": (
            "use aspose_cells_foss_rust::{CellValue, Workbook};\n"
            "fn main() { let _ = Workbook::new(); let _ = CellValue::Number(1.0); }\n",
            ["CellValue", "Workbook"],
        ),
    }
    for language, (code, expected) in cases.items():
        (tmp_path / "README.md").write_text(
            f"# Widget\n\n```{language}\n{code}```\n",
            encoding="utf-8",
        )

        candidates = repository_readme_example_candidates(tmp_path, language)

        assert candidates[0].required_symbols == expected


def test_python_alias_import_anchors_the_public_operations_not_the_import_statement(tmp_path):
    (tmp_path / "README.md").write_text(
        """# Widget

```python
import aspose.words_foss as aw

doc = aw.Document("input.docx")
doc.save("output.pdf", aw.SaveFormat.PDF)
```
""",
        encoding="utf-8",
    )

    candidates = repository_readme_example_candidates(tmp_path, "python")

    assert candidates[0].required_symbols == ["aw.Document", "aw.SaveFormat.PDF"]


def test_python_readme_fence_yields_smallest_self_contained_public_operation(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "cssforge"\n[tool.setuptools.packages.find]\ninclude = ["engine*"]\n',
        encoding="utf-8",
    )
    package = tmp_path / "engine"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        """# CSSForge

```python
from engine.dom import DictNode
from engine.paint import SkiaPaintSink

dom = DictNode("div", {"display": "block"}, text="Hello")
sink = SkiaPaintSink(400, 200)
sink.paint(dom)
```
""",
        encoding="utf-8",
    )

    candidates = repository_readme_example_candidates(tmp_path, "python")
    minimal = next(
        candidate for candidate in candidates if candidate.required_symbols == ["DictNode"]
    )

    assert minimal.code == (
        "from engine.dom import DictNode\n\n"
        "dom = DictNode('div', {'display': 'block'}, text='Hello')\n"
    )
    assert minimal.required_symbols == ["DictNode"]
    assert minimal.evidence_paths == ["README.md"]


def test_rust_readme_local_names_resolve_only_to_unique_public_symbols():
    available = {
        "aspose_cells_foss_rust::CellValue",
        "aspose_cells_foss_rust::Workbook",
    }

    assert _resolve_declared_symbols(["Workbook", "CellValue"], available) == [
        "aspose_cells_foss_rust::CellValue",
        "aspose_cells_foss_rust::Workbook",
    ]

    with pytest.raises(ValueError, match="does not resolve uniquely"):
        _resolve_declared_symbols(
            ["Workbook"],
            {"one::Workbook", "two::Workbook"},
        )


def test_go_source_example_is_complete_comment_free_and_module_bound(tmp_path):
    (tmp_path / "go.mod").write_text(
        "module github.com/acme/widget\n\ngo 1.24\n",
        encoding="utf-8",
    )
    examples = tmp_path / "_examples"
    (examples / "text").mkdir(parents=True)
    (examples / "text" / "main.go").write_text(
        """package main

import (
    "fmt"
    widget "github.com/acme/widget"
)

func main() {
    // Keep source commentary out of visitor-facing examples.
    item := widget.Open("input.bin")
    fmt.Println("https://example.test//literal", item)
}
""",
        encoding="utf-8",
    )

    candidates = repository_source_example_candidates(tmp_path, "go")

    assert len(candidates) == 1
    assert candidates[0].evidence_paths == ["_examples/text/main.go"]
    assert candidates[0].required_symbols == ["widget.Open"]
    assert "source commentary" not in candidates[0].code
    assert '"https://example.test//literal"' in candidates[0].code


def test_go_source_examples_reject_sensitive_and_non_module_consumers(tmp_path):
    (tmp_path / "go.mod").write_text(
        "module github.com/acme/widget\n\ngo 1.24\n",
        encoding="utf-8",
    )
    password = tmp_path / "_examples" / "password"
    unrelated = tmp_path / "_examples" / "unrelated"
    password.mkdir(parents=True)
    unrelated.mkdir(parents=True)
    (password / "main.go").write_text(
        'package main\nimport widget "github.com/acme/widget"\n'
        'func main() { widget.Open("secret.bin") }\n',
        encoding="utf-8",
    )
    (unrelated / "main.go").write_text(
        'package main\nimport "fmt"\nfunc main() { fmt.Println("hello") }\n',
        encoding="utf-8",
    )

    assert repository_source_example_candidates(tmp_path, "go") == []


def test_python_source_example_extracts_one_self_contained_public_operation(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-widget-foss"\nversion = "1.0"\n'
        '[tool.setuptools]\npackages = ["aspose", "aspose.widget"]\n',
        encoding="utf-8",
    )
    package = tmp_path / "aspose" / "widget"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from . import api\n", encoding="utf-8")
    (package / "api.py").write_text(
        "class Document:\n"
        "    @classmethod\n"
        "    def create(cls, title, body):\n"
        "        return cls()\n",
        encoding="utf-8",
    )
    examples = tmp_path / "ApiExamples"
    examples.mkdir()
    (examples / "create_document.py").write_text(
        "import argparse\n"
        "from aspose.widget import api, unused\n\n"
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        "    args = parser.parse_args()\n"
        "    document = api.Document.create('Quarterly update', 'Ready')\n"
        "    print(document, args)\n",
        encoding="utf-8",
    )

    candidates = repository_source_example_candidates(tmp_path, "python")

    assert candidates[0].code == (
        "from aspose.widget import api\n\n"
        "document = api.Document.create('Quarterly update', 'Ready')\n"
    )
    assert candidates[0].class_name == "Document"
    assert candidates[0].evidence_paths == ["ApiExamples/create_document.py"]
    assert candidates[0].required_symbols == ["api.Document.create"]
    assert "argparse" not in candidates[0].code
    assert "unused" not in candidates[0].code


def test_python_source_example_accepts_directly_imported_public_function(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-widget-foss"\nversion = "1.0"\n'
        '[tool.setuptools]\npackages = ["aspose_widget_foss"]\n',
        encoding="utf-8",
    )
    package = tmp_path / "aspose_widget_foss"
    package.mkdir()
    (package / "__init__.py").write_text(
        "def create_widget(name): return name\n",
        encoding="utf-8",
    )
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "quickstart.py").write_text(
        "from aspose_widget_foss import create_widget, unused\n\nwidget = create_widget('demo')\n",
        encoding="utf-8",
    )

    candidates = repository_source_example_candidates(tmp_path, "python")

    assert candidates[0].code == (
        "from aspose_widget_foss import create_widget\n\nwidget = create_widget('demo')\n"
    )
    assert candidates[0].required_symbols == ["create_widget"]


def test_python_source_example_closes_class_method_inputs_from_repository_code(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-widget-foss"\nversion = "1.0"\n'
        '[tool.setuptools]\npackages = ["aspose", "aspose.widget"]\n',
        encoding="utf-8",
    )
    package = tmp_path / "aspose" / "widget"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("class Document: pass\n", encoding="utf-8")
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "load_markdown.py").write_text(
        "import io\n"
        "import aspose.widget as aw\n\n"
        "class Loading:\n"
        "    def load(self):\n"
        "        source = '# Title\\n'\n"
        "        doc = aw.Document(io.BytesIO(source.encode('utf-8')))\n",
        encoding="utf-8",
    )

    candidates = repository_source_example_candidates(tmp_path, "python")
    document = next(candidate for candidate in candidates if candidate.class_name == "Document")

    assert document.code == (
        "import io\n"
        "import aspose.widget as aw\n\n"
        "source = '# Title\\n'\n"
        "doc = aw.Document(io.BytesIO(source.encode('utf-8')))\n"
    )
    assert document.required_symbols == ["aw.Document"]
