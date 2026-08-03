"""Corroborate bounded Python barcode output formats from public source and tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")


class _OutputSpec(NamedTuple):
    backend: str
    public_method: str
    return_type: str
    renderer_class: str
    media_type: str


_RESULT_PATH = "src/aspose_barcode_foss/result.py"
_OUTPUTS = (
    _OutputSpec(
        backend="png",
        public_method="to_png",
        return_type="bytes",
        renderer_class="PngRenderer",
        media_type="image/png",
    ),
    _OutputSpec(
        backend="svg",
        public_method="to_svg",
        return_type="str",
        renderer_class="SvgRenderer",
        media_type="image/svg+xml",
    ),
)


def corroborate_python_barcode_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Add only public, tested PNG/SVG export records for an immutable barcode tree."""

    root = repository_root.resolve()
    original = _sanitize_supplied_functionality(root, formats)
    if not _revision_matches(root, source_revision) or not _generation_contract_is_proven(root):
        return original
    result_module = _parse_relative(root, _RESULT_PATH)
    if result_module is None:
        return original

    result = list(original)
    for spec in _OUTPUTS:
        public_method = _unique_class_method(result_module, "Barcode", spec.public_method)
        if public_method is None or not _output_contract_is_proven(root, spec, public_method):
            continue
        result = _record_proven_output(result, name=spec.backend.upper(), line=public_method.lineno)
    if not _revision_matches(root, source_revision):
        return original
    return result


def _revision_matches(root: Path, expected: str) -> bool:
    if _REVISION.fullmatch(expected) is None or not (root / ".git").is_dir():
        return False
    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return revision.stdout.strip().casefold() == expected.casefold() and not status.stdout.strip()


def _parse_relative(root: Path, relative_path: str) -> ast.Module | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
        return ast.parse(candidate.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError, ValueError):
        return None


def _unique_function(module: ast.Module, name: str) -> ast.FunctionDef | None:
    matches = [
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _unique_class_method(
    module: ast.Module, class_name: str, method_name: str
) -> ast.FunctionDef | None:
    owners = [
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    ]
    if len(owners) != 1:
        return None
    methods = [
        node
        for node in owners[0].body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    ]
    return methods[0] if len(methods) == 1 else None


def _argument_names(function: ast.FunctionDef) -> set[str]:
    return {
        argument.arg
        for argument in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
    }


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _call_names(function: ast.FunctionDef) -> set[str]:
    return {
        name
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and (name := _call_name(node)) is not None
    }


def _generation_contract_is_proven(root: Path) -> bool:
    api = _parse_relative(root, "src/aspose_barcode_foss/api.py")
    service = _parse_relative(root, "src/aspose_barcode_foss/_internal/service.py")
    api_test = _parse_relative(root, "tests/api/test_api_entrypoints.py")
    service_test = _parse_relative(root, "tests/api/test_barcode_service.py")
    if None in (api, service, api_test, service_test):
        return False
    assert api is not None and service is not None
    assert api_test is not None and service_test is not None
    public_generate = _unique_function(api, "generate")
    service_generate = _unique_class_method(service, "BarcodeService", "generate")
    delegation_test = _unique_function(api_test, "test_generate_delegates_to_the_default_service")
    pipeline_test = _unique_function(
        service_test, "test_barcode_service_runs_parse_before_encode_and_forwards_encode_options"
    )
    if None in (public_generate, service_generate, delegation_test, pipeline_test):
        return False
    assert public_generate is not None and service_generate is not None
    assert delegation_test is not None and pipeline_test is not None
    return all(
        (
            {"symbology", "data"} <= _argument_names(public_generate),
            {"symbology", "data"} <= _argument_names(service_generate),
            "generate" in _call_names(public_generate),
            {"get_definition", "parse", "encode", "Barcode"} <= _call_names(service_generate),
            "generate" in _call_names(delegation_test),
            "generate" in _call_names(pipeline_test),
            {"parse", "encode"} <= _string_literals(pipeline_test),
        )
    )


def _output_contract_is_proven(
    root: Path, spec: _OutputSpec, public_method: ast.FunctionDef
) -> bool:
    renderer = _parse_relative(
        root, f"src/aspose_barcode_foss/_internal/renderers/{spec.backend}.py"
    )
    integration_test = _parse_relative(root, f"tests/rendering/test_barcode_{spec.backend}.py")
    renderer_test = _parse_relative(root, f"tests/rendering/test_{spec.backend}_renderer.py")
    if renderer is None or integration_test is None or renderer_test is None:
        return False
    renderer_method = _unique_class_method(renderer, spec.renderer_class, "render")
    if renderer_method is None:
        return False
    return all(
        (
            isinstance(public_method.returns, ast.Name)
            and public_method.returns.id == spec.return_type,
            spec.renderer_class in _call_names(public_method),
            {spec.backend, spec.media_type} <= _string_literals(public_method),
            _returns_attribute(public_method, "artifact", "data"),
            {"RenderedArtifact"} <= _call_names(renderer_method),
            {spec.backend, spec.media_type} <= _string_literals(renderer_method),
            _test_proves_public_output(integration_test, spec),
            _test_proves_renderer_artifact(renderer_test, spec),
        )
    )


def _test_proves_public_output(module: ast.Module, spec: _OutputSpec) -> bool:
    tests = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(f"test_barcode_{spec.public_method}")
    ]
    return any(
        spec.public_method in _call_names(test)
        and spec.return_type in {name.id for name in ast.walk(test) if isinstance(name, ast.Name)}
        for test in tests
    )


def _test_proves_renderer_artifact(module: ast.Module, spec: _OutputSpec) -> bool:
    tests = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(f"test_{spec.backend}_renderer")
    ]
    return any(
        "render" in _call_names(test)
        and {spec.backend, spec.media_type} <= _string_literals(test)
        and spec.return_type in {name.id for name in ast.walk(test) if isinstance(name, ast.Name)}
        for test in tests
    )


def _returns_attribute(function: ast.FunctionDef, owner: str, attribute: str) -> bool:
    return any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == owner
        and node.value.attr == attribute
        for node in ast.walk(function)
    )


def _string_literals(node: ast.AST) -> set[str]:
    return {
        item.value
        for item in ast.walk(node)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }


def _sanitize_supplied_functionality(
    root: Path, formats: list[AsposeOrgFormatEvidenceV1]
) -> list[AsposeOrgFormatEvidenceV1]:
    return [
        item.model_copy(update={"functional": None})
        if item.functional is True
        and (item.direction not in {"import", "export", "both"} or not _safe_file(root, item.file))
        else item
        for item in formats
    ]


def _safe_file(root: Path, relative_path: str) -> bool:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return candidate.is_file()


def _record_proven_output(
    formats: list[AsposeOrgFormatEvidenceV1], *, name: str, line: int
) -> list[AsposeOrgFormatEvidenceV1]:
    candidates = [
        index
        for index, item in enumerate(formats)
        if item.format.casefold() == name.casefold()
        and item.direction == "export"
        and item.file == _RESULT_PATH
    ]
    if len(candidates) > 1:
        return formats
    proven = AsposeOrgFormatEvidenceV1(
        format=name,
        direction="export",
        file=_RESULT_PATH,
        line=line,
        functional=True,
    )
    if not candidates:
        return [*formats, proven]
    result = list(formats)
    result[candidates[0]] = proven
    return result
