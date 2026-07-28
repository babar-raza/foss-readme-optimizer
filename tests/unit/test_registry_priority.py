"""Governed ecosystem ordering for portfolio execution."""

import json
from pathlib import Path

import pytest

from readme_agent.errors import ConfigError
from readme_agent.registry.models import ProductEntry
from readme_agent.registry.priority import (
    PlatformPriorityV1,
    load_platform_priority,
    order_entries_by_platform_priority,
)


def _entry(ecosystem: str, suffix: str) -> ProductEntry:
    return ProductEntry(
        family=f"family-{suffix}",
        platform=ecosystem,
        repo_name=f"repo-{suffix}",
        repo_url=f"https://github.com/org/repo-{suffix}",
        clone_url=f"https://github.com/org/repo-{suffix}.git",
        active=True,
        discovered_via="fixture",
        mode="disabled",
        ecosystem=ecosystem,
    )


def test_real_priority_is_the_user_governed_order():
    assert load_platform_priority().execution_order == [
        "python",
        "net",
        "java",
        "cpp",
        "typescript",
        "rust",
        "go",
    ]


def test_portfolio_order_is_stable_within_each_ecosystem():
    entries = (
        _entry("go", "go-one"),
        _entry("python", "python-one"),
        _entry("java", "java-one"),
        _entry("python", "python-two"),
        _entry("net", "net-one"),
        _entry("cpp", "cpp-one"),
        _entry("typescript", "typescript-one"),
        _entry("rust", "rust-one"),
    )

    ordered = order_entries_by_platform_priority(entries)

    assert [entry.ecosystem for entry in ordered] == [
        "python",
        "python",
        "net",
        "java",
        "cpp",
        "typescript",
        "rust",
        "go",
    ]
    assert [entry.repo_name for entry in ordered[:2]] == ["repo-python-one", "repo-python-two"]


def test_unknown_ecosystem_follows_go_without_becoming_unlisted():
    entries = (_entry("unknown", "unknown"), _entry("go", "go"))

    ordered = order_entries_by_platform_priority(entries)

    assert [entry.ecosystem for entry in ordered] == ["go", "unknown"]


@pytest.mark.parametrize(
    "execution_order",
    [
        ["python", "net", "java", "cpp", "typescript", "rust"],
        ["python", "net", "java", "cpp", "typescript", "rust", "rust"],
    ],
)
def test_incomplete_or_duplicate_policy_fails_closed(tmp_path: Path, execution_order: list[str]):
    path = tmp_path / "priority.json"
    path.write_text(
        json.dumps({"schema_version": 1, "execution_order": execution_order}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="malformed"):
        load_platform_priority(path)


def test_schema_rejects_unknown_ecosystem():
    with pytest.raises(ValueError):
        PlatformPriorityV1(
            execution_order=["python", "net", "java", "cpp", "typescript", "rust", "swift"]
        )
