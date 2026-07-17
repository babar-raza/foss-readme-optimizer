"""Independently re-derives proof that push is blocked -- never by attempting a real push.

Called once right after setup (hard-assert, abort if it fails) and again by
the evidence writer immediately before finalizing evidence.
"""

import platform
from dataclasses import dataclass
from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.hooks import BLOCK_MARKER
from readme_agent.gitsafety.neuter import DISABLED_PUSH_URL


@dataclass
class PushBlockProof:
    ok: bool
    push_url: str | None
    fetch_url: str | None
    hook_installed: bool
    hook_contains_marker: bool
    executable_bit_set: bool | None  # None = not checked (meaningless on Windows)
    detail: str


def verify_push_blocked(repo_path: Path) -> PushBlockProof:
    remote_result = run_git(["remote", "-v"], cwd=repo_path, timeout=10)
    push_url = None
    fetch_url = None
    for line in remote_result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "origin":
            if parts[2] == "(push)":
                push_url = parts[1]
            elif parts[2] == "(fetch)":
                fetch_url = parts[1]

    hook_path = repo_path / ".git" / "hooks" / "pre-push"
    hook_installed = hook_path.exists()
    hook_text = hook_path.read_text(encoding="utf-8") if hook_installed else ""
    hook_contains_marker = BLOCK_MARKER in hook_text

    executable_bit_set: bool | None = None
    if platform.system() != "Windows" and hook_installed:
        executable_bit_set = bool(hook_path.stat().st_mode & 0o111)

    push_neutered = push_url == DISABLED_PUSH_URL
    ok = push_neutered and hook_installed and hook_contains_marker

    detail = (
        f"push_url={push_url!r} (expected {DISABLED_PUSH_URL!r}), "
        f"hook_installed={hook_installed}, hook_contains_marker={hook_contains_marker}"
    )
    if platform.system() == "Windows":
        detail += (
            ", executable_bit=not checked (NTFS has no meaningful bit; Git for "
            "Windows invokes hooks via its bundled shell regardless -- excluded "
            "from the pass/fail verdict, not silently assumed to pass)"
        )

    return PushBlockProof(
        ok=ok,
        push_url=push_url,
        fetch_url=fetch_url,
        hook_installed=hook_installed,
        hook_contains_marker=hook_contains_marker,
        executable_bit_set=executable_bit_set,
        detail=detail,
    )
