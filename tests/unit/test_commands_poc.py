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
