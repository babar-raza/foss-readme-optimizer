"""Statically validate curated Python README examples against public repository facts."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

_SAFE_BUILTINS = {"RuntimeError", "enumerate", "len", "list", "open", "print", "range"}
_UNSAFE_CALLS = {"compile", "eval", "exec", "__import__"}
_STDLIB_MODULES = {
    "io": {"BytesIO": "bytes_io", "StringIO": "text_io"},
    "json": {"loads": "scalar"},
    "pathlib": {"Path": "path"},
}
_STDLIB_MEMBERS = {
    "bytes": {"decode": "scalar"},
    "bytes_io": {"getvalue": "bytes", "read": "bytes", "seek": "scalar", "write": "scalar"},
    "file": {"read": "scalar", "write": "scalar"},
    "path": {"open": "file"},
    "text_io": {"getvalue": "scalar", "read": "scalar", "seek": "scalar", "write": "scalar"},
}


@dataclass(frozen=True)
class _ValueType:
    kind: str
    key: str = ""


@dataclass(frozen=True)
class _ClassContract:
    name: str
    members: dict[str, str | None]


@dataclass(frozen=True)
class ExampleDecision:
    """One canonical README example's static acceptance decision."""

    title: str
    accepted: bool
    reason: str
    evidence_modules: tuple[str, ...]


def _modules_from_source(path: str, class_name: str) -> set[str]:
    if not path.endswith(".py"):
        return set()
    module = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    if module.endswith(".__init__"):
        return {module.removesuffix(".__init__")}
    if module.rsplit(".", 1)[-1] == class_name:
        return {module, module.rsplit(".", 1)[0]}
    return {module}


def _type_name(surface: str, member: str, class_names: dict[str, str]) -> str | None:
    annotation = surface.split("->", 1)[1].strip() if "->" in surface else None
    if annotation is None and ":" in surface and "(" not in surface.split(":", 1)[0]:
        annotation = surface.split(":", 1)[1].strip()
    if annotation:
        tokens = re.findall(r"[A-Za-z_]\w*", annotation)
        for token in tokens:
            if token.casefold() in class_names:
                return class_names[token.casefold()]
    normalized = member.casefold().removeprefix("get_").removeprefix("create_")
    normalized = normalized.removeprefix("to_").replace("_", "")
    candidates = [
        class_name
        for token, class_name in class_names.items()
        if normalized == token
        or normalized.removesuffix("s") == token
        or normalized.endswith(token)
        or normalized.removesuffix("s").endswith(token)
    ]
    return candidates[0] if len(set(candidates)) == 1 else None


def _public_contract(
    value: object,
) -> tuple[dict[str, set[str]], dict[str, _ClassContract], dict[str, str]]:
    if not isinstance(value, dict):
        return {}, {}, {}
    modules = {
        row["module"]: {str(item) for item in row.get("exports", [])}
        for row in value.get("modules", [])
        if isinstance(row, dict)
        and isinstance(row.get("module"), str)
        and isinstance(row.get("exports"), list)
    }
    rows = [
        row
        for row in value.get("classes", [])
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    ]
    name_counts: dict[str, int] = {}
    for row in rows:
        folded = str(row["name"]).casefold().replace("_", "")
        name_counts[folded] = name_counts.get(folded, 0) + 1
    class_names = {
        str(row["name"]).casefold().replace("_", ""): str(row["name"])
        for row in rows
        if name_counts[str(row["name"]).casefold().replace("_", "")] == 1
    }
    classes: dict[str, _ClassContract] = {}
    contracts_by_name: dict[str, _ClassContract] = {}
    for row in rows:
        name = str(row["name"])
        class_modules = _modules_from_source(str(row.get("source_path") or ""), name)
        if isinstance(row.get("module"), str) and row["module"]:
            class_modules.add(str(row["module"]))
        members = {
            str(item["name"]): _type_name(
                str(item.get("surface") or ""), str(item["name"]), class_names
            )
            for item in row.get("members", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        contract = _ClassContract(name=name, members=members)
        contracts_by_name[name] = contract
        for module in class_modules:
            classes[f"{module}:{name}"] = contract
    for module, exports in modules.items():
        for exported in exports:
            if exported in contracts_by_name:
                classes.setdefault(f"{module}:{exported}", contracts_by_name[exported])
    functions = {
        f"{row['module']}:{row['name']}": str(row["return_class"])
        for row in value.get("functions", [])
        if isinstance(row, dict)
        and isinstance(row.get("module"), str)
        and isinstance(row.get("name"), str)
        and isinstance(row.get("return_class"), str)
        and str(row["return_class"]) in classes
    }
    return modules, classes, functions


class _Validator:
    def __init__(self, public_surface: object) -> None:
        self.modules, self.classes, self.functions = _public_contract(public_surface)
        self.names: dict[str, _ValueType] = {}
        self.evidence_modules: set[str] = set()
        self.reason = "accepted"

    def reject(self, reason: str) -> _ValueType:
        if self.reason == "accepted":
            self.reason = reason
        return _ValueType("invalid")

    def class_key(self, name: str) -> str | None:
        matches = [(key, value) for key, value in self.classes.items() if value.name == name]
        if not matches:
            return None
        member_sets = {tuple(sorted(value.members.items())) for _, value in matches}
        if len(member_sets) != 1:
            return None
        return min((key for key, _ in matches), key=lambda key: (key.count("."), len(key), key))

    def resolve(self, node: ast.AST) -> _ValueType:
        if isinstance(node, ast.Name):
            return self.names.get(node.id, _ValueType("scalar"))
        if isinstance(node, ast.Constant):
            return _ValueType("scalar")
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for item in node.elts:
                self.resolve(item)
            return _ValueType("sequence")
        if isinstance(node, ast.Dict):
            for dict_item in [*node.keys, *node.values]:
                if dict_item is not None:
                    self.resolve(dict_item)
            return _ValueType("scalar")
        if isinstance(node, ast.Subscript):
            owner = self.resolve(node.value)
            self.resolve(node.slice)
            return _ValueType("scalar") if owner.kind != "invalid" else owner
        if isinstance(node, ast.Attribute):
            owner = self.resolve(node.value)
            if owner.kind in {"product_class", "product_instance"}:
                contract = self.classes[owner.key]
                if node.attr not in contract.members:
                    return self.reject(f"unknown_product_member:{contract.name}.{node.attr}")
                result = contract.members[node.attr]
                if result:
                    result_key = self.class_key(result)
                    if result_key is not None:
                        return _ValueType("product_instance", result_key)
                return _ValueType("product_unknown", owner.key)
            if owner.kind == "product_unknown":
                contract = self.classes[owner.key]
                return self.reject(f"unresolved_chained_product_member:{contract.name}.{node.attr}")
            if owner.kind == "stdlib_module":
                result = _STDLIB_MODULES[owner.key].get(node.attr)
                return (
                    _ValueType(result or "invalid")
                    if result
                    else self.reject(f"unsafe_stdlib_member:{owner.key}.{node.attr}")
                )
            if owner.kind in _STDLIB_MEMBERS:
                result = _STDLIB_MEMBERS[owner.kind].get(node.attr)
                return (
                    _ValueType(result or "scalar")
                    if result
                    else self.reject(f"unsafe_stdlib_member:{owner.kind}.{node.attr}")
                )
            if owner.kind == "invalid":
                return owner
            return _ValueType("scalar")
        if isinstance(node, ast.Call):
            for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
                self.resolve(argument)
            if isinstance(node.func, ast.Name):
                if node.func.id in _UNSAFE_CALLS:
                    return self.reject(f"unsafe_call:{node.func.id}")
                named_owner = self.names.get(node.func.id)
                if named_owner is not None and named_owner.kind == "product_class":
                    return _ValueType("product_instance", named_owner.key)
                if named_owner is not None and named_owner.kind == "product_function":
                    return _ValueType("product_instance", named_owner.key)
                if named_owner is not None and named_owner.kind == "local_function":
                    return _ValueType("scalar")
                if named_owner is not None and named_owner.kind in {
                    "bytes_io",
                    "path",
                    "text_io",
                }:
                    return named_owner
                if node.func.id in _SAFE_BUILTINS:
                    return _ValueType("file" if node.func.id == "open" else "scalar")
                return self.reject(f"unknown_call:{node.func.id}")
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                class_owner = self.names.get(node.func.value.id)
                if (
                    class_owner is not None
                    and class_owner.kind == "product_class"
                    and node.func.attr in self.classes[class_owner.key].members
                ):
                    self.resolve(node.func)
                    return _ValueType("product_instance", class_owner.key)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "GetChildNodes"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and (target := self.names.get(node.args[0].id)) is not None
                and target.kind == "product_class"
            ):
                owner = self.resolve(node.func)
                return target if owner.kind != "invalid" else owner
            return self.resolve(node.func)
        if isinstance(
            node,
            (ast.BinOp, ast.BoolOp, ast.Compare, ast.JoinedStr, ast.FormattedValue, ast.UnaryOp),
        ):
            for child in ast.iter_child_nodes(node):
                self.resolve(child)
            return _ValueType("scalar")
        return _ValueType("scalar")

    def validate(self, tree: ast.Module) -> tuple[bool, tuple[str, ...], str]:
        for node in tree.body:
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name not in _STDLIB_MODULES:
                        return False, (), f"unsupported_import:{item.name}"
                    self.names[item.asname or item.name] = _ValueType("stdlib_module", item.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    return False, (), "relative_import"
                for item in node.names:
                    stdlib = _STDLIB_MODULES.get(node.module, {}).get(item.name)
                    if stdlib is not None:
                        self.names[item.asname or item.name] = _ValueType(stdlib)
                        continue
                    key = f"{node.module}:{item.name}"
                    if key in self.functions:
                        self.names[item.asname or item.name] = _ValueType(
                            "product_function", self.functions[key]
                        )
                    elif key in self.classes:
                        self.names[item.asname or item.name] = _ValueType("product_class", key)
                    elif item.name not in self.modules.get(node.module, set()):
                        return False, (), f"unknown_product_import:{node.module}.{item.name}"
                    self.evidence_modules.add(node.module)
        if not self.evidence_modules:
            return False, (), "no_product_api_import"
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.ClassDef):
                bases = [
                    self.names.get(base.id) for base in node.bases if isinstance(base, ast.Name)
                ]
                inherited = next(
                    (base for base in bases if base and base.kind == "product_class"),
                    None,
                )
                if inherited is not None:
                    inherited_contract = self.classes[inherited.key]
                    members = dict(inherited_contract.members)
                    for child in ast.walk(node):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            members.setdefault(child.name, None)
                        targets = (
                            child.targets
                            if isinstance(child, ast.Assign)
                            else [child.target]
                            if isinstance(child, ast.AnnAssign)
                            else []
                        )
                        for target in targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                members.setdefault(target.attr, None)
                    key = f"local:{node.name}"
                    self.classes[key] = _ClassContract(name=node.name, members=members)
                    self.names[node.name] = _ValueType("product_class", key)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.names[node.name] = _ValueType("local_function")
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = self.resolve(node.value) if node.value is not None else _ValueType("scalar")
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        self.names[target.id] = value
                    elif isinstance(target, ast.Attribute):
                        self.resolve(target)
            elif isinstance(node, ast.For):
                value = self.resolve(node.iter)
                if isinstance(node.target, ast.Name):
                    self.names[node.target.id] = value
                for child in node.body:
                    for expression in ast.walk(child):
                        if isinstance(expression, (ast.Attribute, ast.Call)):
                            self.resolve(expression)
            else:
                for expression in ast.walk(node):
                    if isinstance(expression, (ast.Attribute, ast.Call)):
                        self.resolve(expression)
            if self.reason != "accepted":
                return False, (), self.reason
        return True, tuple(sorted(self.evidence_modules)), "accepted"


def validate_python_example(code: str, public_surface: object) -> tuple[bool, tuple[str, ...], str]:
    """Validate syntax, imports, calls, and resolvable API member paths without execution."""

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, (), "malformed_python"
    return _Validator(public_surface).validate(tree)
