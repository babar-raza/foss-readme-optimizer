"""Bind visitor-facing Python input placeholders to repository-owned fixtures."""

from __future__ import annotations

import ast
import hashlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from readme_agent.facts.python_consumer_schema import PythonFixtureBindingV1
from readme_agent.repository_snapshot import RepositorySnapshotV1

_MAX_FIXTURE_BYTES = 16 * 1024 * 1024
_INPUT_CALL_NAMES = frozenset({"from_file", "load", "open", "read"})
_FIXTURE_DIRECTORY_TOKENS = frozenset(
    {
        "example",
        "examples",
        "fixture",
        "fixtures",
        "resource",
        "resources",
        "sample",
        "samples",
        "testdata",
    }
)
_PREFERRED_FIXTURE_STEMS = ("minimal", "sample", "example", "input", "simple")


@dataclass(frozen=True)
class _InputPathCandidate:
    target: Path
    allow_substitution: bool
    exact_name_only: bool = False


def _input_paths_from_example(
    code: str,
    *,
    known_constructor_names: frozenset[str] = frozenset(),
) -> list[_InputPathCandidate]:
    tree = ast.parse(code, filename=".readme-agent-consumer.py")
    imported_constructors = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if (alias.asname or alias.name)[:1].isupper()
    }
    paths: dict[Path, tuple[bool, bool]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        call_name = (
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else node.func.id
            if isinstance(node.func, ast.Name)
            else ""
        )
        ordinary_input_call = call_name in _INPUT_CALL_NAMES
        verified_constructor_call = (
            not ordinary_input_call
            and call_name in imported_constructors
            and call_name in known_constructor_names
        )
        if (
            not ordinary_input_call
            and not verified_constructor_call
            and (call_name not in imported_constructors)
        ):
            continue
        first = node.args[0]
        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            continue
        if call_name == "open" and len(node.args) > 1:
            mode = node.args[1]
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
                if any(flag in mode.value for flag in "wax+"):
                    continue
        value = first.value.replace("\\", "/")
        path = Path(value)
        if not value or path.is_absolute() or ".." in path.parts or not path.suffix:
            continue
        prior_ordinary, prior_constructor = paths.get(path, (False, False))
        paths[path] = (
            prior_ordinary or ordinary_input_call,
            prior_constructor or verified_constructor_call,
        )
    return [
        _InputPathCandidate(
            target=path,
            allow_substitution=ordinary or constructor,
            exact_name_only=constructor and not ordinary,
        )
        for path, (ordinary, constructor) in sorted(
            paths.items(), key=lambda item: item[0].as_posix().casefold()
        )
    ]


def _fixture_rank(snapshot_root: Path, path: Path, target: Path) -> tuple:
    relative = path.relative_to(snapshot_root)
    tokens = {part.casefold() for part in relative.parts[:-1]}
    stem = path.stem.casefold()
    preferred_stem = next(
        (index for index, value in enumerate(_PREFERRED_FIXTURE_STEMS) if stem == value),
        len(_PREFERRED_FIXTURE_STEMS),
    )
    return (
        path.name.casefold() != target.name.casefold(),
        not bool(tokens & _FIXTURE_DIRECTORY_TOKENS),
        preferred_stem,
        len(relative.parts),
        path.stat().st_size,
        relative.as_posix().casefold(),
    )


def _repository_fixture_candidates(
    snapshot_root: Path, matches: Callable[[Path], bool]
) -> list[Path]:
    return [
        path
        for path in snapshot_root.rglob("*")
        if path.is_file()
        and matches(path)
        and 0 < path.stat().st_size <= _MAX_FIXTURE_BYTES
        and ".git" not in {part.casefold() for part in path.relative_to(snapshot_root).parts}
    ]


def _select_repository_fixture(snapshot_root: Path, target: Path) -> Path | None:
    candidates = _repository_fixture_candidates(
        snapshot_root, lambda path: path.suffix.casefold() == target.suffix.casefold()
    )
    return min(
        candidates,
        key=lambda path: _fixture_rank(snapshot_root, path, target),
        default=None,
    )


def _select_repository_fixture_by_name(snapshot_root: Path, target: Path) -> Path | None:
    """Match only an identical filename anywhere in the tree, never a bare suffix.

    Constructor calls admit arbitrary string arguments, not just file inputs, so
    substitution must not guess from the extension alone the way ordinary
    ``open``/``load``/``from_file``/``read`` calls do.
    """

    candidates = _repository_fixture_candidates(
        snapshot_root, lambda path: path.name.casefold() == target.name.casefold()
    )
    return min(
        candidates,
        key=lambda path: _fixture_rank(snapshot_root, path, target),
        default=None,
    )


def _exact_repository_fixture(snapshot_root: Path, target: Path) -> Path | None:
    source = (snapshot_root / target).resolve()
    try:
        source.relative_to(snapshot_root)
    except ValueError:
        return None
    if not source.is_file() or not 0 < source.stat().st_size <= _MAX_FIXTURE_BYTES:
        return None
    return source


def stage_repository_input_fixtures(
    snapshot: RepositorySnapshotV1,
    workspace: Path,
    code: str,
    *,
    known_constructor_names: frozenset[str] = frozenset(),
) -> list[PythonFixtureBindingV1]:
    """Stage deterministic inputs without changing the visitor-facing example."""

    bindings: list[PythonFixtureBindingV1] = []
    workspace_root = workspace.resolve()
    snapshot_root = snapshot.root_path.resolve()
    for candidate in _input_paths_from_example(
        code, known_constructor_names=known_constructor_names
    ):
        target = candidate.target
        destination = (workspace_root / target).resolve()
        try:
            destination.relative_to(workspace_root)
        except ValueError:
            continue
        if destination.exists():
            exact_source = _exact_repository_fixture(snapshot_root, target)
            if exact_source is None or not destination.is_file():
                continue
            source_bytes = exact_source.read_bytes()
            if not 0 < len(source_bytes) <= _MAX_FIXTURE_BYTES:
                continue
            if destination.read_bytes() != source_bytes:
                raise ValueError(
                    f"copied repository fixture differs from immutable source: {target.as_posix()}"
                )
            bindings.append(
                PythonFixtureBindingV1(
                    source_path=exact_source.relative_to(snapshot_root).as_posix(),
                    target_path=target.as_posix(),
                    sha256=hashlib.sha256(source_bytes).hexdigest(),
                    size_bytes=len(source_bytes),
                )
            )
            continue
        source = _exact_repository_fixture(snapshot_root, target)
        if source is None and candidate.allow_substitution:
            source = (
                _select_repository_fixture_by_name(snapshot_root, target)
                if candidate.exact_name_only
                else _select_repository_fixture(snapshot_root, target)
            )
        if source is None:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        bindings.append(
            PythonFixtureBindingV1(
                source_path=source.relative_to(snapshot.root_path).as_posix(),
                target_path=target.as_posix(),
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                size_bytes=source.stat().st_size,
            )
        )
    return bindings
