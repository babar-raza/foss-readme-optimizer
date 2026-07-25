"""Shared tool and environment helpers for ecosystem example verifiers."""

from __future__ import annotations

import os
from pathlib import Path

from readme_agent.facts.example_execution import ExampleExecutionResultV1


def missing_tool_result(tool: str) -> ExampleExecutionResultV1:
    """Represent a missing executable without invoking a shell."""
    return ExampleExecutionResultV1(
        argv=[tool],
        return_code=9009,
        stdout="",
        stderr=f"required executable is not available on PATH: {tool}",
        timed_out=False,
        environment_names=[],
    )


def disposable_profile_environment(workspace: Path) -> dict[str, str]:
    """Keep package-manager credentials and user configuration out of builds."""
    profile = workspace.parent / "tool-profile"
    profile.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["HOME"] = str(profile)
    environment["USERPROFILE"] = str(profile)
    environment["APPDATA"] = str(profile / "roaming")
    environment["LOCALAPPDATA"] = str(profile / "local")
    if os.name == "nt":
        drive, tail = os.path.splitdrive(str(profile))
        environment["HOMEDRIVE"] = drive
        environment["HOMEPATH"] = tail
    return environment
