"""Discover revision-bound Python golden-test workflows from repository source."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shlex
import tomllib
from pathlib import Path

from markdown_it import MarkdownIt

from readme_agent.facts.python_golden_workflow_schema import (
    GoldenArtifactInventoryV1,
    GoldenDependencyGroupV1,
    GoldenEnvironmentControlV1,
    GoldenFontPolicyV1,
    GoldenRendererFallbackV1,
    GoldenSourceFileV1,
    GoldenVisualDiffPolicyV1,
    GoldenWorkflowCommandV1,
    PythonGoldenWorkflowEvidenceV1,
)
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules"}
_ENVIRONMENT_NAME = re.compile(r"^[A-Z][A-Z0-9_]{5,}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(root: Path, path: Path) -> GoldenSourceFileV1:
    return GoldenSourceFileV1(path=path.relative_to(root).as_posix(), sha256=_sha256(path))


def _python_files(root: Path, relative: str, pattern: str) -> list[Path]:
    directory = root / relative
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.rglob(pattern)
        if path.is_file()
        and not any(part in _IGNORED_DIRECTORIES for part in path.relative_to(root).parts)
    )


def _tree(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _loaded_names(tree: ast.AST) -> set[str]:
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _calls_attribute(tree: ast.AST, base: str, attribute: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == base
        for node in ast.walk(tree)
    )


def _call_uses_name(tree: ast.AST, attribute: str, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
        and name in _loaded_names(node)
        for node in ast.walk(tree)
    )


def _helper_imports_used(tree: ast.Module, helper_module: str) -> bool:
    loaded = _loaded_names(tree)
    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == helper_module
        for alias in node.names
    }
    return bool(imported) and imported <= loaded


def _module_path(root: Path, module: str) -> Path | None:
    candidate = root.joinpath(*module.split(".")).with_suffix(".py")
    return candidate if candidate.is_file() else None


def _path_segments(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name):
        return []
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path":
        if len(node.args) != 1:
            return None
        return _path_segments(node.args[0])
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _path_segments(node.left)
        right = _path_segments(node.right)
        if left is not None and right is not None:
            return [*left, *right]
    return None


def _assigned_paths(tree: ast.Module) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if value is None:
            continue
        segments = _path_segments(value)
        if not segments:
            continue
        names = [target.id for target in targets if isinstance(target, ast.Name)]
        results.extend((name, "/".join(segments)) for name in names)
    return results


def _has_case_option(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and any(
            isinstance(argument, ast.Constant) and argument.value == "--case"
            for argument in node.args
        )
        for node in ast.walk(tree)
    )


def _case_ids(tree: ast.Module) -> tuple[str, ...]:
    values: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and "CASES" in target.id for target in targets):
            continue
        if node.value is None:
            continue
        for child in ast.walk(node.value):
            if not isinstance(child, ast.Call) or not child.args:
                continue
            first = child.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                values.add(first.value)
    return tuple(sorted(values))


def _representative_case_ids(
    root: Path, tool_path: str, case_ids: tuple[str, ...]
) -> tuple[str, ...]:
    readme = root / "README.md"
    try:
        tokens = MarkdownIt("commonmark").parse(readme.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError):
        return ()
    allowed = set(case_ids)
    selections: set[tuple[str, ...]] = set()
    invalid_selection = False
    for token in tokens:
        if token.type != "fence":
            continue
        for line in token.content.splitlines():
            try:
                parts = shlex.split(line, posix=True)
            except ValueError:
                continue
            normalized = [part.removeprefix("./") for part in parts]
            if tool_path not in normalized:
                continue
            if normalized.count(tool_path) != 1:
                invalid_selection = True
                continue
            tool_index = normalized.index(tool_path)
            launcher = parts[tool_index - 1].replace("\\", "/").rsplit("/", 1)[-1].casefold()
            tail = parts[tool_index + 1 :]
            positions = [index for index, part in enumerate(tail) if part == "--case"]
            if not positions:
                continue
            values = tuple(tail[index + 1] for index in positions if index + 1 < len(tail))
            if (
                tool_index < 1
                or launcher not in {"py", "python", "python3", "python.exe"}
                or positions != list(range(0, len(tail), 2))
                or len(values) != len(positions)
                or len(values) < 2
                or len(set(values)) != len(values)
                or any(value not in allowed for value in values)
            ):
                invalid_selection = True
                continue
            selections.add(values)
    if invalid_selection or len(selections) != 1:
        return ()
    return next(iter(selections))


def _truthy_values(function: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    values = {
        item.value
        for node in ast.walk(function)
        if isinstance(node, (ast.Set, ast.Tuple, ast.List))
        for item in node.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }
    return tuple(sorted(values))


def _environment_evidence(
    root: Path,
) -> tuple[tuple[GoldenEnvironmentControlV1, ...], GoldenFontPolicyV1 | None]:
    controls: dict[tuple[str, str], GoldenEnvironmentControlV1] = {}
    font_policy: GoldenFontPolicyV1 | None = None
    for path in _python_files(root, "src", "*.py"):
        tree = _tree(path)
        if tree is None:
            continue
        source = _source(root, path)
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(target, ast.Name) and "ENV" in target.id for target in targets):
                continue
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                continue
            name = node.value.value
            if not _ENVIRONMENT_NAME.fullmatch(name):
                continue
            target_names = [target.id for target in targets if isinstance(target, ast.Name)]
            if not target_names or not set(target_names) & _loaded_names(tree):
                continue
            users = [
                function
                for function in tree.body
                if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                and set(target_names) & _loaded_names(function)
                and "get" in _called_names(function)
            ]
            enabled_values = tuple(
                sorted({value for user in users for value in _truthy_values(user)})
            )
            if not enabled_values:
                continue
            controls[(name, source.path)] = GoldenEnvironmentControlV1(
                name=name, enabled_values=enabled_values, source=source
            )
            functions = [
                function
                for function in tree.body
                if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            selectors = [
                function
                for function in functions
                if users[0].name in _called_names(function)
                and {"_BASE14_FONTS", "require_unicode"} <= _loaded_names(function)
            ]
            finders = [
                function
                for function in functions
                if {"_COMMON_FONT_DIRS", "_UNICODE_FONT_CANDIDATES"} <= _loaded_names(function)
            ]
            if "SYSTEM_FONT" in name and selectors and finders:
                font_policy = GoldenFontPolicyV1(
                    environment_name=name,
                    enabled_values=enabled_values,
                    default_strategy="built_in_fonts_unless_unicode_required",
                    enabled_strategy="search_system_font_directories",
                    source=source,
                )
    return tuple(controls[key] for key in sorted(controls)), font_policy


def _renderer_fallbacks(
    root: Path, helper: Path, tree: ast.Module
) -> tuple[GoldenRendererFallbackV1, ...]:
    source = _source(root, helper)
    fallbacks: dict[tuple[str, str], GoldenRendererFallbackV1] = {}
    loaded = _loaded_names(tree)
    for module in _imported_modules(tree):
        if module == "fitz" and "fitz" in loaded and _calls_attribute(tree, "fitz", "open"):
            fallbacks[("PyMuPDF", "fitz")] = GoldenRendererFallbackV1(
                name="PyMuPDF", mechanism="python_import", identifier="fitz", source=source
            )
    for assignment in ast.walk(tree):
        if not isinstance(assignment, (ast.Assign, ast.AnnAssign)) or assignment.value is None:
            continue
        targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
        target_names = [target.id for target in targets if isinstance(target, ast.Name)]
        node = assignment.value
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "which" or not node.args:
            continue
        first = node.args[0]
        if (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and set(target_names) & loaded
            and any(_call_uses_name(tree, "run", name) for name in target_names)
        ):
            identifier = first.value
            fallbacks[(identifier, identifier)] = GoldenRendererFallbackV1(
                name=identifier,
                mechanism="executable",
                identifier=identifier,
                source=source,
            )
    return tuple(fallbacks[key] for key in sorted(fallbacks))


def _workflow_candidates(root: Path) -> list[tuple[Path, Path, Path, ast.Module, ast.Module]]:
    candidates: list[tuple[Path, Path, Path, ast.Module, ast.Module]] = []
    tools = [path for path in _python_files(root, "tools", "*.py") if "golden" in path.name]
    tests = [path for path in _python_files(root, "tests", "test_*.py") if "golden" in path.name]
    for tool in tools:
        tool_tree = _tree(tool)
        if tool_tree is None or not _has_case_option(tool_tree):
            continue
        for test in tests:
            test_tree = _tree(test)
            if test_tree is None or "unittest" not in _imported_modules(test_tree):
                continue
            common = sorted(_imported_modules(tool_tree) & _imported_modules(test_tree))
            linked = [
                (module, path)
                for module in common
                if (path := _module_path(root, module)) and "golden" in path.name
            ]
            if (
                len(linked) == 1
                and _helper_imports_used(tool_tree, linked[0][0])
                and _helper_imports_used(test_tree, linked[0][0])
            ):
                helpers = [linked[0][1]]
                candidates.append((tool, test, helpers[0], tool_tree, test_tree))
    return candidates


def _dependency_groups(
    root: Path, imported_modules: set[str]
) -> tuple[GoldenDependencyGroupV1, ...]:
    manifest = root / "pyproject.toml"
    try:
        payload = tomllib.loads(manifest.read_text(encoding="utf-8-sig"))
        optional = payload["project"]["optional-dependencies"]
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return ()
    source = _source(root, manifest)
    aliases = {"pillow": "PIL", "pymupdf": "fitz"}
    groups: list[GoldenDependencyGroupV1] = []
    for name, requirements in sorted(optional.items()):
        if not isinstance(requirements, list) or not all(
            isinstance(item, str) for item in requirements
        ):
            continue
        distributions = [re.match(r"[A-Za-z0-9_.-]+", item) for item in requirements]
        imports = {
            aliases.get(match.group(0).casefold(), match.group(0).replace("-", "_"))
            for match in distributions
            if match
        }
        if imports & imported_modules:
            groups.append(
                GoldenDependencyGroupV1(name=name, requirements=tuple(requirements), source=source)
            )
    return tuple(groups)


def _visual_diff_policy(
    root: Path, helper: Path, helper_tree: ast.Module, test_tree: ast.Module
) -> GoldenVisualDiffPolicyV1 | None:
    functions = {
        node.name: node
        for node in helper_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    availability = functions.get("visual_diff_available")
    required_names = {"HAS_PILLOW", "HAS_PYMUPDF", "HAS_PDFTOPPM"}
    boolean_operators = (
        {type(node.op) for node in ast.walk(availability) if isinstance(node, ast.BoolOp)}
        if availability is not None
        else set()
    )
    pillow_aliases = {
        alias.asname or alias.name
        for node in ast.walk(helper_tree)
        if isinstance(node, ast.ImportFrom) and node.module == "PIL"
        for alias in node.names
    }
    if (
        availability is None
        or not required_names <= _loaded_names(availability)
        or not {ast.And, ast.Or} <= boolean_operators
        or not any(
            _calls_attribute(helper_tree, alias, attribute)
            for alias in pillow_aliases
            for attribute in ("open", "difference")
        )
        or not {"visual_diff_available", "create_visual_diff_artifacts"} <= _called_names(test_tree)
    ):
        return None
    return GoldenVisualDiffPolicyV1(
        required_python_packages=("Pillow",),
        renderer_any_of=("PyMuPDF", "pdftoppm"),
        source=_source(root, helper),
    )


def collect_python_golden_workflow(root: Path) -> PythonGoldenWorkflowEvidenceV1 | None:
    """Return one unambiguous source-linked Python golden workflow, or fail closed."""

    candidates = _workflow_candidates(root)
    if len(candidates) != 1:
        return None
    tool, test, helper, tool_tree, test_tree = candidates[0]
    helper_tree = _tree(helper)
    if helper_tree is None:
        return None
    assigned_paths = _assigned_paths(helper_tree)
    golden_paths = sorted(
        {value for name, value in assigned_paths if "GOLDEN" in name and (root / value).is_dir()}
    )
    failure_paths = sorted(
        {
            value
            for name, value in assigned_paths
            if "FAILURE" in name and value.startswith("tests/")
        }
    )
    function_names = {
        node.name
        for node in helper_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    called_by_test = _called_names(test_tree)
    failure_calls = sorted(name for name in called_by_test if name.startswith("failure_"))
    if (
        len(golden_paths) != 1
        or len(failure_paths) != 1
        or "semantic_manifest" not in function_names
        or "semantic_manifest" not in called_by_test
        or "fail" not in called_by_test
        or not failure_calls
    ):
        return None
    failure_names = {
        name
        for name, _ in assigned_paths
        if "FAILURE" in name and name in _loaded_names(helper_tree)
    }
    functions = {
        node.name: node
        for node in helper_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if not failure_names or not any(
        call in functions and failure_names & _loaded_names(functions[call])
        for call in failure_calls
    ):
        return None
    golden_root = root / golden_paths[0]
    artifact_paths = sorted(path for path in golden_root.rglob("*") if path.is_file())
    if not artifact_paths:
        return None
    case_ids = _case_ids(helper_tree)
    if not case_ids or any(
        not any(
            path.stem == case_id or path.name.startswith(f"{case_id}.") for path in artifact_paths
        )
        for case_id in case_ids
    ):
        return None
    imported_modules = (
        _imported_modules(tool_tree) | _imported_modules(test_tree) | _imported_modules(helper_tree)
    )
    dependency_groups = _dependency_groups(root, imported_modules)
    visual_policy = _visual_diff_policy(root, helper, helper_tree, test_tree)
    renderer_fallbacks = _renderer_fallbacks(root, helper, helper_tree)
    if not dependency_groups or visual_policy is None or len(renderer_fallbacks) < 2:
        return None
    environment_controls, font_policy = _environment_evidence(root)
    artifacts = tuple(_source(root, path) for path in artifact_paths)
    inventory_payload = json.dumps(
        [artifact.model_dump(mode="json") for artifact in artifacts],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    tool_source = _source(root, tool)
    test_source = _source(root, test)
    representative_case_ids = _representative_case_ids(root, tool_source.path, case_ids)
    test_module = test_source.path.removesuffix(".py").replace("/", ".")
    manifest_source = dependency_groups[0].source
    extras = ",".join(group.name for group in dependency_groups)
    commands = [
        GoldenWorkflowCommandV1(
            kind="install_requirements",
            command=f'python -m pip install -e ".[{extras}]"',
            source=manifest_source,
        ),
        GoldenWorkflowCommandV1(
            kind="regenerate_all", command=f"python {tool_source.path}", source=tool_source
        ),
        GoldenWorkflowCommandV1(
            kind="verify",
            command=f"python -m unittest {test_module} -v",
            source=test_source,
        ),
    ]
    for case_id in case_ids:
        commands.insert(
            -1,
            GoldenWorkflowCommandV1(
                kind="regenerate_selected",
                command=f"python {tool_source.path} --case {case_id}",
                source=tool_source,
                case_id=case_id,
            ),
        )
    supporting = {item.path: item for item in (tool_source, test_source, _source(root, helper))}
    supporting[manifest_source.path] = manifest_source
    if representative_case_ids:
        supporting["README.md"] = _source(root, root / "README.md")
    for control in environment_controls:
        supporting[control.source.path] = control.source
    return PythonGoldenWorkflowEvidenceV1(
        artifact_inventory=GoldenArtifactInventoryV1(
            root=golden_paths[0],
            count=len(artifacts),
            inventory_sha256=hashlib.sha256(inventory_payload).hexdigest(),
            files=artifacts,
        ),
        regeneration_tool=tool_source,
        verification_test=test_source,
        helper_module=_source(root, helper),
        commands=tuple(commands),
        case_ids=case_ids,
        representative_case_ids=representative_case_ids,
        comparison_mode="semantic_manifest",
        failure_output_path=failure_paths[0],
        environment_controls=environment_controls,
        renderer_fallbacks=renderer_fallbacks,
        dependency_groups=dependency_groups,
        visual_diff_policy=visual_policy,
        font_policy=font_policy,
        source_files=tuple(supporting[path] for path in sorted(supporting)),
    )


def python_golden_workflow_fact(
    root: Path,
    *,
    source_revision: str | None = None,
    observed_at: str | None = None,
) -> FactRecordV2 | None:
    """Project a discovered workflow into a provenance-complete product fact."""

    evidence = collect_python_golden_workflow(root)
    if evidence is None:
        return None
    locations = ",".join(source.path for source in evidence.source_files)
    return FactRecordV2(
        fact_id=descriptive_fact_id("development.golden_workflow", "python-source"),
        field="development.golden_workflow",
        value=evidence.model_dump(mode="json"),
        source=FactSourceV2(
            source_type="mechanical_test",
            location=f"repository://{locations}",
            source_revision=source_revision,
            retrieved_at=observed_at,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.development_and_testing"],
    )
