"""Remove Docker execution resources and prove their absence fail-closed."""

from __future__ import annotations

import subprocess
import time
from typing import Literal, Protocol

_REMOVE_ATTEMPTS = 3
_NOT_FOUND_MARKERS = (
    "no such container",
    "no such volume",
    "no such object",
    "not found",
)


class DockerCleanupRunner(Protocol):
    """Narrow structural seam for bounded Docker cleanup commands."""

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one Docker control-plane command."""


def _absence_confirmed(result: subprocess.CompletedProcess[str]) -> bool:
    if result.returncode == 0 or result.returncode == 124:
        return False
    detail = f"{result.stdout}\n{result.stderr}".lower()
    return any(marker in detail for marker in _NOT_FOUND_MARKERS)


def _listing_is_empty(result: subprocess.CompletedProcess[str]) -> bool:
    return result.returncode == 0 and not result.stdout.strip()


def _resource_is_absent(
    runner: DockerCleanupRunner,
    inspect: list[str],
    listing: list[str],
) -> bool:
    observed = runner.run(inspect, timeout_seconds=10)
    listed = runner.run(listing, timeout_seconds=10)
    return _absence_confirmed(observed) and _listing_is_empty(listed)


def remove_docker_resource(
    runner: DockerCleanupRunner,
    kind: Literal["container", "volume"],
    identity: str,
) -> bool:
    """Idempotently remove one named resource and confirm explicit absence."""

    remove = (
        ["rm", "--force", identity]
        if kind == "container"
        else ["volume", "rm", "--force", identity]
    )
    inspect = [kind, "inspect", identity]
    listing = (
        ["ps", "-aq", "--filter", f"name={identity}"]
        if kind == "container"
        else ["volume", "ls", "-q", "--filter", f"name={identity}"]
    )
    stability_seconds = max(float(getattr(runner, "cleanup_stability_seconds", 0.0)), 0.0)
    for _attempt in range(_REMOVE_ATTEMPTS):
        try:
            runner.run(remove, timeout_seconds=30)
            absent = _resource_is_absent(runner, inspect, listing)
            if absent and stability_seconds:
                time.sleep(stability_seconds)
                absent = _resource_is_absent(runner, inspect, listing)
        except Exception:
            continue
        if absent:
            return True
    return False
