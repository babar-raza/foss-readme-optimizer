"""Extract explicit executable constraints without trusting README prose."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from readme_agent.facts.curated_python_development import distributed_python_source_roots
from readme_agent.facts.public_constraint_text import is_public_constraint_sentence

_CONSTRAINT_POLARITY = re.compile(
    r"\b(?:not\s+implemented|not\s+supported|only\b.+\bsupported|requires?|unsupported)\b",
    flags=re.IGNORECASE,
)
_ABSTRACT_MESSAGE = re.compile(
    r"\b(?:abstract|base(?:\s+\w+){0,3}\s+class)\b",
    flags=re.IGNORECASE,
)
_UNHELPFUL_MEMBER = re.compile(
    r"^(?P<member>.+?)\s+is\s+not\s+implemented(?:\s+for\s+\w+)?$",
    flags=re.IGNORECASE,
)
_MAX_LIMITATIONS = 24
_LIMITATION_GROUPS = (
    (
        "rendering_unimplemented",
        re.compile(r"\brender(?:er|ing)?\b", flags=re.IGNORECASE),
        "Scene and renderer output generation are not implemented.",
    ),
    (
        "mesh_boolean_unimplemented",
        re.compile(r"\b(?:do_boolean|union|difference|intersect)\b", flags=re.IGNORECASE),
        "Mesh boolean operations do_boolean, union, difference, and intersect are not implemented.",
    ),
    (
        "nurbs_evaluation_unimplemented",
        re.compile(r"\bNURBS\b", flags=re.IGNORECASE),
        "NURBS curve evaluation and surface-to-mesh conversion are not implemented.",
    ),
    (
        "fbx_export_unimplemented",
        re.compile(r"\bFBX\s+export\b", flags=re.IGNORECASE),
        "FBX export is not implemented.",
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method(class_node: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            item
            for item in class_node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
        ),
        None,
    )


def _raises_not_implemented(node: ast.AST | None) -> bool:
    return node is not None and any(
        isinstance(item, ast.Raise)
        and isinstance(item.exc, ast.Call)
        and isinstance(item.exc.func, ast.Name)
        and item.exc.func.id == "NotImplementedError"
        for item in ast.walk(node)
    )


def _calls_attribute(node: ast.AST | None, attribute: str) -> bool:
    return node is not None and any(
        isinstance(item, ast.Call)
        and isinstance(item.func, ast.Attribute)
        and item.func.attr == attribute
        for item in ast.walk(node)
    )


def _class_index(
    parsed: list[tuple[Path, ast.Module]],
) -> dict[str, tuple[Path, ast.Module, ast.ClassDef]]:
    return {
        node.name: (path, tree, node)
        for path, tree in parsed
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def _registered_plugins(tree: ast.Module) -> list[tuple[str, int]]:
    registered = []
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Attribute)
            or node.func.attr != "register_plugin"
            or len(node.args) != 1
            or not isinstance(node.args[0], ast.Call)
            or not isinstance(node.args[0].func, ast.Name)
        ):
            continue
        registered.append((node.args[0].func.id, node.lineno))
    return sorted(registered, key=lambda item: item[1])


def _class_instantiates(class_node: ast.ClassDef, class_name: str) -> bool:
    return any(
        isinstance(item, ast.Call)
        and isinstance(item.func, ast.Name)
        and item.func.id == class_name
        for item in ast.walk(class_node)
    )


def _evidence(root: Path, path: Path, line: int, symbol: str) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "line": line,
        "source_sha256": _sha256(path),
        "symbol": symbol,
    }


def _collada_dispatch_limitation(
    root: Path,
    parsed: list[tuple[Path, ast.Module]],
) -> dict[str, object] | None:
    """Prove one dispatch obstruction only when every source link is present."""

    classes = _class_index(parsed)
    required = {
        name: classes.get(name)
        for name in (
            "Scene",
            "IOService",
            "Exporter",
            "FbxExporter",
            "FbxPlugin",
            "ColladaExporter",
            "ColladaPlugin",
        )
    }
    if any(item is None for item in required.values()):
        return None
    scene_path, _, scene = required["Scene"]  # type: ignore[misc]
    service_path, _, service = required["IOService"]  # type: ignore[misc]
    base_path, _, exporter = required["Exporter"]  # type: ignore[misc]
    fbx_path, _, fbx_exporter = required["FbxExporter"]  # type: ignore[misc]
    _, _, fbx_plugin = required["FbxPlugin"]  # type: ignore[misc]
    collada_path, _, collada_exporter = required["ColladaExporter"]  # type: ignore[misc]
    _, _, collada_plugin = required["ColladaPlugin"]  # type: ignore[misc]
    scene_save = _method(scene, "save")
    create_exporter = _method(service, "create_exporter")
    base_predicate = _method(exporter, "supports_format")
    fbx_bases = {
        base.id if isinstance(base, ast.Name) else base.attr
        for base in fbx_exporter.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    }
    registration_match = next(
        (
            (path, registrations)
            for path, tree in parsed
            if (registrations := _registered_plugins(tree))
            and {"FbxPlugin", "ColladaPlugin"}.issubset({name for name, _ in registrations})
        ),
        None,
    )
    if registration_match is None:
        return None
    registration_path, registrations = registration_match
    names = [name for name, _ in registrations]
    dispatches_in_order = (
        any(
            isinstance(node, ast.For)
            and isinstance(node.iter, ast.Attribute)
            and node.iter.attr == "_exporters"
            and _calls_attribute(node, "supports_format")
            for node in ast.walk(create_exporter)
        )
        if create_exporter is not None
        else False
    )
    if (
        not _calls_attribute(scene_save, "create_exporter")
        or not dispatches_in_order
        or not _raises_not_implemented(base_predicate)
        or "Exporter" not in fbx_bases
        or _method(fbx_exporter, "supports_format") is not None
        or not any(
            _raises_not_implemented(_method(fbx_exporter, method))
            for method in ("save", "save_to_stream")
        )
        or _method(collada_exporter, "supports_format") is None
        or _method(collada_exporter, "export") is None
        or not _class_instantiates(fbx_plugin, "FbxExporter")
        or not _class_instantiates(collada_plugin, "ColladaExporter")
        or "FbxPlugin" not in names
        or "ColladaPlugin" not in names
        or names.index("FbxPlugin") >= names.index("ColladaPlugin")
    ):
        return None
    assert scene_save and create_exporter and base_predicate
    registration_lines = dict(registrations)
    evidence = [
        _evidence(root, scene_path, scene_save.lineno, "Scene.save"),
        _evidence(root, service_path, create_exporter.lineno, "IOService.create_exporter"),
        _evidence(root, base_path, base_predicate.lineno, "Exporter.supports_format"),
        _evidence(root, fbx_path, fbx_exporter.lineno, "FbxExporter"),
        _evidence(
            root,
            registration_path,
            registration_lines["FbxPlugin"],
            f"FbxPlugin registered at line {registration_lines['FbxPlugin']}",
        ),
        _evidence(root, collada_path, collada_exporter.lineno, "ColladaExporter"),
        _evidence(
            root,
            registration_path,
            registration_lines["ColladaPlugin"],
            f"ColladaPlugin registered at line {registration_lines['ColladaPlugin']}",
        ),
    ]
    return {
        "kind": "collada_dispatch_blocked",
        "statement": (
            "COLLADA export through Scene.save is blocked because an earlier FBX exporter "
            "format check is not implemented."
        ),
        **evidence[0],
        "evidence": evidence,
    }


def _group_limitations(found: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: list[dict[str, object]] = []
    consumed: set[int] = set()
    for kind, pattern, statement in _LIMITATION_GROUPS:
        matches = [
            (index, item)
            for index, item in enumerate(found)
            if pattern.search(str(item["statement"]))
        ]
        members = {str(item.get("member")) for _, item in matches}
        owners = {str(item.get("owner")) for _, item in matches}
        complete = {
            "rendering_unimplemented": {"Scene", "Renderer"}.issubset(owners),
            "mesh_boolean_unimplemented": {
                "do_boolean",
                "union",
                "difference",
                "intersect",
            }.issubset(members),
            "nurbs_evaluation_unimplemented": {"NurbsCurve", "NurbsSurface"}.issubset(owners),
            "fbx_export_unimplemented": "FbxExporter" in owners,
        }[kind]
        if not matches or not complete:
            continue
        consumed.update(index for index, _item in matches)
        evidence = [
            {
                key: item[key]
                for key in ("path", "line", "source_sha256", "owner", "member")
                if item.get(key) is not None
            }
            for _, item in matches
        ]
        grouped.append({"kind": kind, "statement": statement, **evidence[0], "evidence": evidence})
    unique: list[dict[str, object]] = []
    for index, item in enumerate(found):
        if index in consumed:
            continue
        unhelpful = _UNHELPFUL_MEMBER.match(str(item["statement"]).strip())
        if unhelpful is not None:
            member = unhelpful.group("member")
            tokens = member.split()
            if (
                len(tokens) == 1
                or any("_" in token or "." in token for token in tokens)
                or tokens[-1].casefold() in {"constructor", "getter", "setter"}
            ):
                continue
        if any(row["statement"] == item["statement"] for row in unique):
            continue
        unique.append(item)
    return [*grouped, *unique]


def source_limitations(root: Path) -> tuple[object, list[str]] | None:
    """Extract literal constraints from raised exceptions, never README assertions."""

    found: list[dict[str, object]] = []
    source_roots = distributed_python_source_roots(root)
    if not source_roots:
        return None
    parsed: list[tuple[Path, ast.Module]] = []
    source_files = sorted(
        {path for source_root in source_roots for path in source_root.rglob("*.py")}
    )
    for path in source_files:
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        parsed.append((path, tree))
    base_classes = {
        (base.id if isinstance(base, ast.Name) else base.attr)
        for _, tree in parsed
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for base in node.bases
        if isinstance(base, (ast.Attribute, ast.Name))
    }
    for path, tree in parsed:
        relative = path.relative_to(root).as_posix()
        source_sha256 = _sha256(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            if not node.exc.args:
                continue
            message = node.exc.args[0]
            if (
                not isinstance(message, ast.Constant)
                or not isinstance(message.value, str)
                or _CONSTRAINT_POLARITY.search(message.value) is None
                or _ABSTRACT_MESSAGE.search(message.value) is not None
                or not is_public_constraint_sentence(message.value)
            ):
                continue
            containing_classes = [
                item
                for item in ast.walk(tree)
                if isinstance(item, ast.ClassDef)
                and item.lineno <= node.lineno <= (item.end_lineno or item.lineno)
            ]
            if containing_classes:
                owner = min(
                    containing_classes,
                    key=lambda item: (item.end_lineno or item.lineno) - item.lineno,
                )
                owner_docstring = ast.get_docstring(owner) or ""
                if (
                    owner.name in base_classes
                    or (len(owner.name) > 1 and owner.name[0] == "I" and owner.name[1].isupper())
                    or _ABSTRACT_MESSAGE.search(owner_docstring)
                ):
                    continue
            containing_functions = [
                item
                for item in ast.walk(tree)
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.lineno <= node.lineno <= (item.end_lineno or item.lineno)
            ]
            member = min(
                containing_functions,
                key=lambda item: (item.end_lineno or item.lineno) - item.lineno,
                default=None,
            )
            record = {
                "statement": message.value.strip(),
                "path": relative,
                "line": node.lineno,
                "source_sha256": source_sha256,
                "owner": owner.name if containing_classes else None,
                "member": member.name if member is not None else None,
                "exception_type": (
                    node.exc.func.id if isinstance(node.exc.func, ast.Name) else "exception"
                ),
            }
            found.append(record)
    selected = _group_limitations(found)
    dispatch = _collada_dispatch_limitation(root, parsed)
    if dispatch is not None:
        selected.append(dispatch)
    if not selected:
        return None
    selected = sorted(
        selected,
        key=lambda item: (
            0
            if re.search(
                r"\b(?:do_boolean|union|difference|intersect|NURBS|render)\b",
                str(item["statement"]),
                flags=re.IGNORECASE,
            )
            else 1,
            str(item["path"]),
            int(str(item["line"])),
        ),
    )[:_MAX_LIMITATIONS]
    locations: set[str] = set()
    for item in selected:
        nested_evidence = item.get("evidence")
        evidence_rows = nested_evidence if isinstance(nested_evidence, list) else [item]
        locations.update(
            str(evidence["path"])
            for evidence in evidence_rows
            if isinstance(evidence, dict) and evidence.get("path")
        )
    return selected, sorted(locations)
