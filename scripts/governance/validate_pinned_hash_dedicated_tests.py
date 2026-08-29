"""Pre-commit and CI gate (GOV-033): run a specific test on demand for a pin that has its
own dedicated pytest test, rather than the declarative `validate_pinned_hashes.py`
registry -- GOV-032's registry deliberately excludes exactly these cases (its own
module docstring: "already covered by their own existing dedicated pytest tests...
deliberately NOT duplicated here"). That exclusion is correct *only if* the
dedicated test actually runs before the commit reaches shared history -- today it
doesn't: full pytest is CI-only, and the post-commit hook pushes unconditionally.
`d8795bbdb` (2026-08-28) proved the gap concretely: it edited a vendored check file
without re-pinning the check-battery manifest, and the drift reached `main` and sat
there undetected until an unrelated full-suite run caught it hours later.

This closes that one demonstrated hole without moving the full suite into
pre-commit (which this project's own hook design note already rejects as an
invitation to `--no-verify` fatigue): only the one or two node ids relevant to the
files actually staged in *this* commit run, not the whole suite.

Staging-scoped mode alone is not sufficient, and the same `d8795bbdb` drift proves why
twice over: the hook that runs this script only landed on 2026-08-29, so the 2026-08-28
commit could not have been stopped by it, and a clone with no hooks installed is still
unguarded today. `--all` therefore runs every registered dedicated test regardless of what
is staged, and CI's `pinned-hashes` job runs it in that mode -- so a drifted pin fails on
the next push even when it reached `main` through an unhooked clone. The staging-scoped
default remains the pre-commit path: fast, and it still catches the drift one commit
earlier than CI can.

Run standalone: `.venv/Scripts/python scripts/governance/validate_pinned_hash_dedicated_tests.py`
Run every registered test: same command with `--all`.
Exit 0 = nothing staged triggers a dedicated test, or every triggered test passed.
Exit 1 = a triggered test failed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DedicatedTestTrigger:
    label: str
    trigger_paths: frozenset[str]
    node_id: str


def _check_battery_trigger_paths() -> frozenset[str]:
    """Derived from the manifest itself, not hardcoded -- the manifest is the one
    source of truth for which vendored files it pins; hardcoding a copy of that
    list here would just be a second place for it to go stale."""

    manifest_path = REPO_ROOT / "data" / "imported" / "aspose_org_check_battery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = {manifest_path.relative_to(REPO_ROOT).as_posix()}
    paths.update(item["destination_path"] for item in manifest["files"])
    return frozenset(paths)


def load_dedicated_test_triggers() -> tuple[DedicatedTestTrigger, ...]:
    """The declarative table. Extend with one more entry per future case where a
    pin is deliberately covered by its own dedicated test instead of the GOV-032
    registry."""

    return (
        DedicatedTestTrigger(
            label="vendored check-battery manifest",
            trigger_paths=_check_battery_trigger_paths(),
            node_id=(
                "tests/unit/test_aspose_org_check_battery_source.py"
                "::test_vendored_check_battery_matches_its_content_addressed_manifest"
            ),
        ),
    )


def triggered_node_ids(
    staged_paths: Iterable[str], triggers: Iterable[DedicatedTestTrigger]
) -> list[str]:
    staged = set(staged_paths)
    node_ids: list[str] = []
    for trigger in triggers:
        if staged & trigger.trigger_paths and trigger.node_id not in node_ids:
            node_ids.append(trigger.node_id)
    return node_ids


def staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def run_pytest(node_ids: list[str]) -> int:
    command = [sys.executable, "-m", "pytest", *node_ids, "-q", "-p", "no:cacheprovider"]
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def all_node_ids(triggers: Iterable[DedicatedTestTrigger]) -> list[str]:
    node_ids: list[str] = []
    for trigger in triggers:
        if trigger.node_id not in node_ids:
            node_ids.append(trigger.node_id)
    return node_ids


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    triggers = load_dedicated_test_triggers()
    if "--all" in args:
        node_ids = all_node_ids(triggers)
        if not node_ids:
            return 0
        print(
            "validate_pinned_hash_dedicated_tests: --all -- running every registered "
            f"dedicated pin test ({len(node_ids)}):"
        )
        for node_id in node_ids:
            print(f"  {node_id}")
        exit_code = run_pytest(node_ids)
        if exit_code != 0:
            print(
                "validate_pinned_hash_dedicated_tests: FAILED -- a recorded pin no longer "
                "matches recomputed source truth; re-pin it (see the failing test's own "
                "assertion for the exact recorded-vs-actual mismatch).",
                file=sys.stderr,
            )
        return exit_code
    staged = staged_files()
    if not staged:
        return 0
    node_ids = triggered_node_ids(staged, triggers)
    if not node_ids:
        return 0
    print(
        "validate_pinned_hash_dedicated_tests: staged files touch a pin with its own "
        f"dedicated test -- running {len(node_ids)} targeted test(s) before allowing this commit:"
    )
    for node_id in node_ids:
        print(f"  {node_id}")
    exit_code = run_pytest(node_ids)
    if exit_code != 0:
        print(
            "validate_pinned_hash_dedicated_tests: FAILED -- re-pin before committing "
            "(see the failing test's own assertion for the exact recorded-vs-actual mismatch).",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
