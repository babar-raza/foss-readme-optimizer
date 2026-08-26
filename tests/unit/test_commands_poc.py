"""Test the rapid POC command's portfolio inclusion semantics."""

import argparse
from types import SimpleNamespace

from readme_agent import commands_poc


def test_all_python_includes_active_disabled_entry_using_platform_fallback(monkeypatch) -> None:
    entries = [
        SimpleNamespace(
            org_repo="org/verified-python",
            ecosystem="python",
            platform="python",
            active=True,
            mode="dry_run",
        ),
        SimpleNamespace(
            org_repo="org/new-private-python",
            ecosystem=None,
            platform="python",
            active=True,
            mode="disabled",
        ),
        SimpleNamespace(
            org_repo="org/inactive-python",
            ecosystem="python",
            platform="python",
            active=False,
            mode="disabled",
        ),
        SimpleNamespace(
            org_repo="org/java",
            ecosystem="java",
            platform="java",
            active=True,
            mode="dry_run",
        ),
    ]
    observed: list[str] = []
    monkeypatch.setattr(commands_poc, "load_products", lambda: entries)
    monkeypatch.setattr(
        commands_poc,
        "run_poc_for_repo",
        lambda org_repo: observed.append(org_repo) or 0,
    )

    result = commands_poc.cmd_poc(argparse.Namespace(all_python=True, repo=None))

    assert result == 0
    assert observed == ["org/verified-python", "org/new-private-python"]


def _registry_entries() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            org_repo="org/python-one",
            ecosystem="python",
            platform="python",
            active=True,
            mode="dry_run",
        ),
        SimpleNamespace(
            org_repo="org/cpp-one",
            ecosystem="cpp",
            platform="cpp",
            active=True,
            mode="dry_run",
        ),
        SimpleNamespace(
            org_repo="org/go-one",
            ecosystem=None,
            platform="go",
            active=True,
            mode="disabled",
        ),
        SimpleNamespace(
            org_repo="org/inactive-rust",
            ecosystem="rust",
            platform="rust",
            active=False,
            mode="disabled",
        ),
    ]


def test_all_active_covers_every_ecosystem_in_the_allow_list(monkeypatch) -> None:
    """The portfolio target is every processable repository, not one ecosystem."""

    observed: list[str] = []
    monkeypatch.setattr(commands_poc, "load_products", _registry_entries)
    monkeypatch.setattr(
        commands_poc,
        "run_poc_for_repo",
        lambda org_repo: observed.append(org_repo) or 0,
    )

    result = commands_poc.cmd_poc(
        argparse.Namespace(all_python=False, all_active=True, ecosystem=None, repo=None)
    )

    assert result == 0
    # Inactive entries stay excluded: data/products.json remains the hard allow-list.
    assert observed == ["org/python-one", "org/cpp-one", "org/go-one"]


def test_all_active_honours_the_ecosystem_filter_including_platform_fallback(monkeypatch) -> None:
    observed: list[str] = []
    monkeypatch.setattr(commands_poc, "load_products", _registry_entries)
    monkeypatch.setattr(
        commands_poc,
        "run_poc_for_repo",
        lambda org_repo: observed.append(org_repo) or 0,
    )

    result = commands_poc.cmd_poc(
        argparse.Namespace(all_python=False, all_active=True, ecosystem=["cpp", "GO"], repo=None)
    )

    assert result == 0
    assert observed == ["org/cpp-one", "org/go-one"]


def test_all_active_fails_closed_when_no_entry_matches(monkeypatch) -> None:
    """An ecosystem typo must report nothing to do rather than silently succeed."""

    observed: list[str] = []
    monkeypatch.setattr(commands_poc, "load_products", _registry_entries)
    monkeypatch.setattr(
        commands_poc,
        "run_poc_for_repo",
        lambda org_repo: observed.append(org_repo) or 0,
    )

    result = commands_poc.cmd_poc(
        argparse.Namespace(all_python=False, all_active=True, ecosystem=["dotnet"], repo=None)
    )

    assert result == 1
    assert observed == []
