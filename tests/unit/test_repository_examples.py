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
