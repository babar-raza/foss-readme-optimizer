"""Constructor-call fixture substitution stays fail-closed to verified public classes."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.python_consumer_fixtures import (
    _input_paths_from_example,
    stage_repository_input_fixtures,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1

_CONSTRUCTOR_EXAMPLE = (
    'from note.document import Document\ndocument = Document("SimpleTable.one")\n'
)


def _snapshot(root: Path) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="fixture/note-python",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        inventory_sha256="0" * 64,
        captured_at="2026-08-19T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/fixture/note-python.git",
            git_tree_sha256="0" * 64,
        ),
    )


def test_constructor_call_defaults_to_no_substitution_without_known_constructor_names() -> None:
    candidates = _input_paths_from_example(_CONSTRUCTOR_EXAMPLE)

    assert len(candidates) == 1
    assert candidates[0].target == Path("SimpleTable.one")
    assert candidates[0].allow_substitution is False


def test_constructor_call_becomes_substitution_eligible_for_a_known_constructor() -> None:
    candidates = _input_paths_from_example(
        _CONSTRUCTOR_EXAMPLE, known_constructor_names=frozenset({"Document"})
    )

    assert len(candidates) == 1
    assert candidates[0].target == Path("SimpleTable.one")
    assert candidates[0].allow_substitution is True
    assert candidates[0].exact_name_only is True


def test_constructor_call_stays_ineligible_for_an_unrelated_known_constructor_name() -> None:
    candidates = _input_paths_from_example(
        _CONSTRUCTOR_EXAMPLE, known_constructor_names=frozenset({"Workbook"})
    )

    assert len(candidates) == 1
    assert candidates[0].allow_substitution is False


def test_ordinary_input_call_names_are_unaffected_by_known_constructor_names() -> None:
    code = 'data = load("input.bin")\n'

    without_known = _input_paths_from_example(code)
    with_unrelated_known = _input_paths_from_example(
        code, known_constructor_names=frozenset({"Document"})
    )

    assert without_known == with_unrelated_known
    assert without_known[0].allow_substitution is True
    assert without_known[0].exact_name_only is False


def test_staging_does_not_fuzzy_substitute_a_constructor_call_without_verified_names(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshot"
    workspace = tmp_path / "workspace"
    fixture = snapshot_root / "testfiles" / "SimpleTable.one"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"one-format-bytes")
    (workspace / "testfiles").mkdir(parents=True)
    (workspace / "testfiles" / "SimpleTable.one").write_bytes(b"one-format-bytes")

    bindings = stage_repository_input_fixtures(
        _snapshot(snapshot_root), workspace, _CONSTRUCTOR_EXAMPLE
    )

    assert bindings == []
    assert not (workspace / "SimpleTable.one").exists()


def test_staging_fuzzy_substitutes_a_verified_constructor_call_to_the_real_fixture(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshot"
    workspace = tmp_path / "workspace"
    fixture = snapshot_root / "testfiles" / "SimpleTable.one"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"one-format-bytes")
    (workspace / "testfiles").mkdir(parents=True)
    (workspace / "testfiles" / "SimpleTable.one").write_bytes(b"one-format-bytes")

    bindings = stage_repository_input_fixtures(
        _snapshot(snapshot_root),
        workspace,
        _CONSTRUCTOR_EXAMPLE,
        known_constructor_names=frozenset({"Document"}),
    )

    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.source_path == "testfiles/SimpleTable.one"
    assert binding.target_path == "SimpleTable.one"
    assert binding.size_bytes == len(b"one-format-bytes")
    staged = workspace / "SimpleTable.one"
    assert staged.is_file()
    assert staged.read_bytes() == b"one-format-bytes"


def test_staging_refuses_a_same_suffix_but_differently_named_fixture_for_a_constructor(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshot"
    workspace = tmp_path / "workspace"
    fixture = snapshot_root / "testfiles" / "Different.one"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"unrelated repository fixture")
    (workspace / "testfiles").mkdir(parents=True)
    (workspace / "testfiles" / "Different.one").write_bytes(b"unrelated repository fixture")
    code = 'from note.document import Document\ndocument = Document("testfiles/Missing.one")\n'

    bindings = stage_repository_input_fixtures(
        _snapshot(snapshot_root),
        workspace,
        code,
        known_constructor_names=frozenset({"Document"}),
    )

    assert bindings == []
    assert not (workspace / "testfiles" / "Missing.one").exists()
