"""Collect static Python package facts used by optional README sections."""

from __future__ import annotations

import ast
import hashlib
import tomllib
from collections.abc import Callable
from pathlib import Path

from readme_agent.facts.curated_python_fixture_inventory import snapshot_fixture_inventory
from readme_agent.facts.curated_python_public_surface import python_public_surface
from readme_agent.facts.curated_python_readme import (
    is_quick_start_example_title,
    verified_readme_examples,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, local_fact_verification_allowed

_IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules"}
_MAX_RUNTIME_VERIFICATION_ATTEMPTS = 3
VerifyLocalExampleFn = Callable[
    [RepositorySnapshotV1, MinimalExamplePolicy], LocalProductVerificationV1
]


def _real_isolated_execution_proves(
    code: str,
    snapshot: RepositorySnapshotV1,
    verify_fn: VerifyLocalExampleFn,
) -> bool:
    example = MinimalExamplePolicy(
        language="python",
        class_name="readme_example",
        code=code.rstrip() + "\n",
        evidence_paths=["README.md"],
    )
    result = verify_fn(snapshot, example)
    return result.truth_eligible and result.outcome in {
        "SOURCE_BUILD_VERIFIED",
        "SOURCE_TREE_VERIFIED",
    }


def _runtime_verify_quick_start_examples(
    inline_examples: list[dict[str, object]],
    withheld_inline_examples: list[dict[str, object]],
    snapshot: RepositorySnapshotV1,
    *,
    verify_fn: VerifyLocalExampleFn = verify_local_product_example,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Prove the canonical Quick Start example(s) through real isolated execution.

    Bounded to the "Quick Start" heading only, and to `_MAX_RUNTIME_VERIFICATION_ATTEMPTS`
    attempts total -- each attempt spins up a real OS-isolated Python interpreter
    (`python_example_verifier.verify` / `prove_python_consumer`), so this deliberately does
    not attempt every example the way `select_verified_repository_example`'s ranked
    selection does for `example.minimal`.

    Two independent groups benefit, for two different reasons:

    - A `withheld_inline_examples` entry failed `curated_python_readme`'s conservative
      AST-only public-surface check (`static_api_verified is False`) -- e.g. note-python's
      real Quick Start block iterates `for page in doc:` and reads `page.Title...`, which the
      static validator cannot resolve through the loop variable and misattributes to
      `Document`. Real execution is strictly stronger than that static check and can prove
      such a block correct despite the static rejection; a successful proof PROMOTES it into
      `inline_examples` (leaving `static_api_verified` honestly `False`, since that check
      still never ran successfully, but setting `runtime_verified` True).
    - An `inline_examples` entry that already has `static_api_verified is True` may still lack
      any execution evidence; a successful proof only adds `runtime_verified` True, changing
      nothing else.

    Only a successful real proof changes anything -- failed attempts and untried entries are
    left exactly as `verified_python_examples` produced them.
    """

    updated_inline = list(inline_examples)
    remaining_withheld: list[dict[str, object]] = []
    attempts = 0
    for item in withheld_inline_examples:
        code = item.get("code") if isinstance(item, dict) else None
        promoted = False
        if (
            attempts < _MAX_RUNTIME_VERIFICATION_ATTEMPTS
            and isinstance(item, dict)
            and is_quick_start_example_title(str(item.get("title") or ""))
            and isinstance(code, str)
            and code.strip()
        ):
            attempts += 1
            if _real_isolated_execution_proves(code, snapshot, verify_fn):
                updated_inline.append({**item, "runtime_verified": True})
                promoted = True
        if not promoted:
            remaining_withheld.append(item)
    for index, item in enumerate(updated_inline):
        if attempts >= _MAX_RUNTIME_VERIFICATION_ATTEMPTS:
            break
        code = item.get("code") if isinstance(item, dict) else None
        if (
            not isinstance(item, dict)
            or item.get("static_api_verified") is not True
            or item.get("runtime_verified") is True
            or not is_quick_start_example_title(str(item.get("title") or ""))
            or not isinstance(code, str)
            or not code.strip()
        ):
            continue
        attempts += 1
        if _real_isolated_execution_proves(code, snapshot, verify_fn):
            updated_inline[index] = {**item, "runtime_verified": True}
    return updated_inline, remaining_withheld


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Derive one importer format only from its exact supports_format implementation."""

    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "isinstance"
            and len(child.args) == 2
            and isinstance(child.args[0], ast.Name)
            and child.args[0].id == "file_format"
            and isinstance(child.args[1], ast.Name)
            and child.args[1].id.endswith("Format")
        ):
            stem = child.args[1].id.removesuffix("Format").casefold()
            return {"gltf": "GLTF", "obj": "OBJ", "stl": "STL", "threemf": "3MF"}.get(
                stem, stem.upper()
            )
    return None


def _implemented(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    statements = [
        child
        for child in node.body
        if not isinstance(child, ast.Pass)
        and not (
            isinstance(child, ast.Expr)
            and isinstance(child.value, ast.Constant)
            and isinstance(child.value.value, str)
        )
    ]
    return bool(statements) and not all(isinstance(child, ast.Raise) for child in statements)


def _implemented_keyword_branch(tree: ast.AST, keyword: str) -> bool:
    for child in ast.walk(tree):
        if not isinstance(child, ast.If) or keyword not in ast.unparse(child.test).casefold():
            continue
        if any(not isinstance(statement, ast.Pass) for statement in child.body):
            return True
    return False


def python_source_format_directions(root: Path) -> tuple[object, list[str]] | None:
    """Collect source-implemented Python import and export directions without execution claims."""

    directions: list[dict[str, object]] = []
    locations: list[str] = []
    roles = {
        "Importer": ("import_scene", "input"),
        "Exporter": ("export", "output"),
    }
    paths = sorted({path for role in roles for path in root.rglob(f"*{role}.py")})
    for path in paths:
        relative = path.relative_to(root)
        if any(part in _IGNORED_DIRECTORIES for part in relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        role = next((name for name in roles if path.stem.endswith(name)), None)
        if role is None:
            continue
        implementation_name, direction = roles[role]
        for definition in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            methods = {
                node.name: node
                for node in definition.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            support = methods.get("supports_format")
            implementation = methods.get(implementation_name)
            if support is None or implementation is None or not _implemented(implementation):
                continue
            format_name = _format_name(support)
            if format_name is None:
                continue
            calls = {
                node.func.attr
                for node in ast.walk(implementation)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            item: dict[str, object] = {
                "format": format_name,
                "direction": direction,
                "implementation_symbol": f"{definition.name}.{implementation_name}",
                "supports_format_symbol": f"{definition.name}.supports_format",
                "source_path": relative.as_posix(),
                "source_sha256": _sha256(path),
                "execution_verified": False,
            }
            if format_name == "STL" and direction == "input":
                item["variants"] = sorted(
                    variant
                    for variant, method in (
                        ("ascii", "_read_ascii_stl"),
                        ("binary", "_read_binary_stl"),
                    )
                    if method in calls
                )
            if format_name == "OBJ" and direction == "input":
                item["material_library_support"] = all(
                    _implemented_keyword_branch(tree, keyword) for keyword in ("mtllib", "usemtl")
                )
            directions.append(item)
            locations.append(relative.as_posix())
    if not directions:
        return None
    return (
        {
            "schema_version": 1,
            "assurance": "repository_source_implementation",
            "execution_verified": False,
            "directions": directions,
        },
        sorted(set(locations)),
    )


def python_optional_extras(root: Path) -> tuple[object, list[str]] | None:
    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return None
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    extras = project.get("optional-dependencies")
    if not isinstance(extras, dict) or not extras:
        return None
    normalized = {
        str(name): [str(requirement) for requirement in requirements]
        for name, requirements in sorted(extras.items())
        if isinstance(requirements, list)
    }
    return {"manifest_path": "pyproject.toml", "extras": normalized}, ["pyproject.toml"]


def example_inventory(
    root: Path,
    source_revision: str | None = None,
    *,
    snapshot: RepositorySnapshotV1 | None = None,
) -> tuple[object, list[str]] | None:
    base = root / "examples"
    files = sorted(
        path
        for path in (base.rglob("*.py") if base.is_dir() else [])
        if path.is_file()
        and not any(part in _IGNORED_DIRECTORIES for part in path.relative_to(root).parts)
    )
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
            "execution_verified": False,
        }
        for path in files
    ]
    locations = [str(entry["path"]) for entry in entries]
    index_path = root / "examples" / "README.md"
    if index_path.is_file():
        entries.append(
            {
                "path": "examples/README.md",
                "sha256": _sha256(index_path),
                "execution_verified": False,
            }
        )
        locations.append("examples/README.md")
    public_surface = python_public_surface(root)
    curated = verified_readme_examples(root, public_surface[0] if public_surface else None)
    value: dict[str, object] = {
        "files": entries,
        "execution_policy": "inventory_only",
    }
    if curated is not None:
        value.update(curated[0])
        locations.extend(curated[1])
        inline_examples = value.get("inline_examples")
        withheld_examples = value.get("withheld_inline_examples")
        if (
            snapshot is not None
            and local_fact_verification_allowed()
            and isinstance(inline_examples, list)
            and isinstance(withheld_examples, list)
            and (inline_examples or withheld_examples)
        ):
            updated_inline, updated_withheld = _runtime_verify_quick_start_examples(
                inline_examples, withheld_examples, snapshot
            )
            value["inline_examples"] = updated_inline
            value["withheld_inline_examples"] = updated_withheld
    if not entries and curated is None:
        return None
    fixture_inventory = snapshot_fixture_inventory(root, source_revision)
    value["fixture_inventory"] = fixture_inventory.model_dump(mode="json")
    if fixture_inventory.tree_id is not None:
        locations.append(f"git-tree:{fixture_inventory.tree_id}")
    return value, sorted(set(locations))
