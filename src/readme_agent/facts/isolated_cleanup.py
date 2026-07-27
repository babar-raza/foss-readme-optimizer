"""Remove Docker execution resources and prove their absence fail-closed."""

from __future__ import annotations

import subprocess
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
    for _attempt in range(_REMOVE_ATTEMPTS):
        try:
            runner.run(remove, timeout_seconds=30)
            observed = runner.run(inspect, timeout_seconds=10)
        except Exception:
            continue
        if _absence_confirmed(observed):
            return True
    return False
