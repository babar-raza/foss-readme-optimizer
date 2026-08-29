"""Path-matching logic for the pre-commit dedicated-test gate. Does not re-test
pytest itself -- only whether the right node id(s) get selected for a given staged
file set, and that an untouched tree triggers nothing."""

from __future__ import annotations

from scripts.governance.validate_pinned_hash_dedicated_tests import (
    DedicatedTestTrigger,
    load_dedicated_test_triggers,
    triggered_node_ids,
)


def test_no_staged_files_trigger_nothing() -> None:
    assert triggered_node_ids([], load_dedicated_test_triggers()) == []


def test_unrelated_staged_files_trigger_nothing() -> None:
    staged = ["src/readme_agent/cli.py", "README.md", "tests/unit/test_cli.py"]
    assert triggered_node_ids(staged, load_dedicated_test_triggers()) == []


def test_check_battery_source_file_triggers_its_dedicated_test() -> None:
    staged = [
        "src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/"
        "readme_refresh_checks.py"
    ]
    node_ids = triggered_node_ids(staged, load_dedicated_test_triggers())
    assert node_ids == [
        "tests/unit/test_aspose_org_check_battery_source.py"
        "::test_vendored_check_battery_matches_its_content_addressed_manifest"
    ]


def test_check_battery_sibling_file_also_triggers_it() -> None:
    staged = ["src/readme_agent/vendored_asposeorg/scripts/pipeline/lib/api_table_dupes.py"]
    assert len(triggered_node_ids(staged, load_dedicated_test_triggers())) == 1


def test_manifest_file_itself_triggers_it() -> None:
    staged = ["data/imported/aspose_org_check_battery_manifest.json"]
    assert len(triggered_node_ids(staged, load_dedicated_test_triggers())) == 1


def test_two_files_from_the_same_trigger_produce_one_node_id_not_two() -> None:
    staged = [
        "src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/"
        "readme_refresh_checks.py",
        "src/readme_agent/vendored_asposeorg/scripts/pipeline/lib/api_table_dupes.py",
    ]
    assert len(triggered_node_ids(staged, load_dedicated_test_triggers())) == 1


def test_synthetic_trigger_only_fires_on_its_own_paths() -> None:
    trigger = DedicatedTestTrigger(
        label="synthetic",
        trigger_paths=frozenset({"a/b.py", "a/c.py"}),
        node_id="tests/unit/test_fixture.py::test_thing",
    )
    assert triggered_node_ids(["a/b.py"], [trigger]) == ["tests/unit/test_fixture.py::test_thing"]
    assert triggered_node_ids(["z/unrelated.py"], [trigger]) == []
