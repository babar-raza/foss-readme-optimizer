"""Repository README examples remain untrusted until real local verification."""

from __future__ import annotations

from readme_agent.facts.repository_examples import repository_readme_example_candidates


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
