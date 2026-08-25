"""Tests for source-derived TypeScript consumer normalization."""

import json

from readme_agent.facts.typescript_example_normalization import (
    normalize_typescript_package_consumer,
)
from readme_agent.registry.models import MinimalExamplePolicy


def _write_repository(root) -> None:
    (root / "src" / "package").mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "@scope/widget",
                "main": "dist/index.js",
                "types": "dist/index.d.ts",
            }
        ),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text(
        json.dumps({"compilerOptions": {"rootDir": "src", "outDir": "dist"}}),
        encoding="utf-8",
    )
    (root / "src" / "package" / "index.ts").write_text(
        "export { Widget } from './Widget';\nexport { Required } from './Required';\n",
        encoding="utf-8",
    )
    (root / "src" / "package" / "Widget.ts").write_text(
        "export class Widget { constructor(name?: string) {} }\n",
        encoding="utf-8",
    )
    (root / "src" / "package" / "Required.ts").write_text(
        "export class Required { constructor(name: string) {} }\n",
        encoding="utf-8",
    )


def test_ambiguous_imports_become_one_source_proven_constructible_consumer(tmp_path) -> None:
    _write_repository(tmp_path)
    example = MinimalExamplePolicy(
        language="typescript",
        class_name="Widget",
        code=(
            "import { Widget } from '@scope/widget';\n"
            "import { Feature } from '@scope/widget/feature';\n"
            "const widget = new Widget();\n"
        ),
        evidence_paths=["README.md"],
        required_symbols=["Widget", "Feature"],
    )

    normalized = normalize_typescript_package_consumer(tmp_path, example)

    assert normalized.code == (
        "import { Widget } from '@scope/widget/dist/package';\n\n"
        "const widget = new Widget();\n"
        "console.log(widget);\n"
    )
    assert normalized.required_symbols == ["Widget"]
    assert normalized.evidence_paths == [
        "src/package/index.ts",
        "src/package/Widget.ts",
    ]


def test_current_canonical_import_is_preserved(tmp_path) -> None:
    _write_repository(tmp_path)
    example = MinimalExamplePolicy(
        language="typescript",
        class_name="Widget",
        code=(
            "import { Widget } from '@scope/widget/dist/package';\nconst widget = new Widget();\n"
        ),
        evidence_paths=["src/package/Widget.ts"],
        required_symbols=["Widget"],
    )

    assert normalize_typescript_package_consumer(tmp_path, example) == example


def test_public_barrel_wins_over_executable_root_entry(tmp_path) -> None:
    (tmp_path / "aspose_cells").mkdir()
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "excel-cells", "main": "index.ts"}),
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        json.dumps({"compilerOptions": {"outDir": "dist"}}),
        encoding="utf-8",
    )
    (tmp_path / "index.ts").write_text(
        "import { Workbook } from './aspose_cells';\nnew Workbook();\n",
        encoding="utf-8",
    )
    (tmp_path / "aspose_cells" / "index.ts").write_text(
        "export { Workbook } from './workbook';\nexport { Style } from './style';\n",
        encoding="utf-8",
    )
    (tmp_path / "aspose_cells" / "workbook.ts").write_text(
        "export class Workbook {}\n",
        encoding="utf-8",
    )
    (tmp_path / "aspose_cells" / "style.ts").write_text(
        "export class Style {}\n",
        encoding="utf-8",
    )
    example = MinimalExamplePolicy(
        language="typescript",
        class_name="Workbook",
        code=(
            "import { Workbook, Style } from './aspose_cells';\n"
            "const workbook = new Workbook();\n"
            "const style = new Style();\n"
        ),
        evidence_paths=["README.md"],
        required_symbols=["Workbook", "Style"],
    )

    normalized = normalize_typescript_package_consumer(tmp_path, example)

    assert normalized.code == (
        "import { Workbook } from 'excel-cells/dist/aspose_cells';\n\n"
        "const workbook = new Workbook();\n"
        "console.log(workbook);\n"
    )
    assert normalized.required_symbols == ["Workbook"]
    assert normalized.evidence_paths == [
        "aspose_cells/index.ts",
        "aspose_cells/workbook.ts",
    ]
