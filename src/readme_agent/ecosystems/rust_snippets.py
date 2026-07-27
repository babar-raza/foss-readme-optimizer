"""Extract syntax-valid repository-authored Rust examples and test functions."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from readme_agent.ecosystems.rust_api_schema import (
    RustPackageLayoutV1,
    RustSnippetV1,
)
from readme_agent.ecosystems.rust_syntax import (
    RustSourceModule,
    node_text,
    parse_rust_source_file,
    preceding_attributes,
    top_level_nodes,
)


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _snippets(
    module: RustSourceModule,
    *,
    repository_root: Path,
    examples: bool,
) -> list[RustSnippetV1]:
    records: list[RustSnippetV1] = []
    for node in top_level_nodes(module):
        if node.type != "function_item":
            continue
        name = node_text(node.child_by_field_name("name"), module.source)
        attributes = preceding_attributes(node, module.source)
        kind: Literal["example_main", "test_function"] | None = (
            "example_main"
            if examples and name == "main"
            else "test_function"
            if any(text.replace(" ", "").startswith("#[test]") for text in attributes)
            else None
        )
        if kind is None:
            continue
        records.append(
            RustSnippetV1(
                kind=kind,
                function_name=name,
                source_path=_relative(module.source_path, repository_root),
                source_line=node.start_point.row + 1,
                code=node_text(node, module.source),
            )
        )
    return records


def extract_rust_snippets(
    repository_root: Path,
    package: RustPackageLayoutV1,
    modules: list[RustSourceModule],
) -> list[RustSnippetV1]:
    """Return examples/main and source/test functions proven by the Rust parser."""

    records = [
        record
        for module in modules
        for record in _snippets(module, repository_root=repository_root, examples=False)
    ]
    for relative in [*package.example_paths, *package.test_paths]:
        path = repository_root / relative
        parsed = parse_rust_source_file(
            path,
            module=("external", path.stem),
            search_directory=path.parent,
            public_from_parent=False,
            path_attribute=None,
        )
        records.extend(
            _snippets(
                parsed,
                repository_root=repository_root,
                examples=relative in package.example_paths,
            )
        )
    unique = {(record.kind, record.source_path, record.source_line): record for record in records}
    return [unique[key] for key in sorted(unique)]
