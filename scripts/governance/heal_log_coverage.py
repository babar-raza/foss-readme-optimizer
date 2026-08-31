"""Auto-heal `logs/` coverage gaps found by `audit_log_coverage.py`: one skeleton entry per gap
date, tagged `auto-skeleton` so it's greppable and visibly distinct from a hand-authored entry.

This is the one script in `scripts/governance/` documented as intentionally write-capable and
commit/push-capable outside of a human-authored `git commit`. It exists because every other layer
of `logs/` coverage enforcement -- the documented "two touches" convention, and
`validate_plan_structure.py`'s pre-commit/CI blocking check -- depends on whichever agent is
committing having a local hook installed or remembering the rule. Neither holds unconditionally
for every agent/clone/environment with standing commit authority to this repo (see decision
recording this design). This script makes coverage a guaranteed, mechanically-derived property of
the repository instead: it never asks any agent to comply, it repairs the gap directly.

Deliberately narrow: only ever touches files under `logs/`. Self-verifies via
`log_shard_writer.write_entry`'s per-shard check, then a full `validate_plan_structure.py` run,
before committing anything -- aborts loudly instead of committing/pushing a result that would
leave `logs/` internally inconsistent. Circuit breaker: refuses to auto-heal more than
`MAX_AUTO_HEAL_DATES` dates in one run; a batch that large signals something worse happening than
an ordinary missed entry and needs a human, not a bigger blast radius for an unattended script.

Standalone; never imported by `src/`. Usage:

    python scripts/governance/heal_log_coverage.py --full-history --dry-run
    python scripts/governance/heal_log_coverage.py --push-range <before-sha> <after-sha>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from governance.audit_log_coverage import find_gaps  # noqa: E402
from governance.log_shard_writer import write_entry  # noqa: E402

MAX_AUTO_HEAL_DATES = 5

# plans/master.md's Decision Ledger is backed by plans/decisions/catalog.jsonl, and
# plans/requirements.md is backed by plans/requirements/catalog.jsonl -- both catalogs tag under
# their narrative document, per logs/README.md's three-tag scheme (master/requirements/governance).
_TAG_BY_GOVERNED_FILE = {
    "plans/master.md": "master",
    "plans/decisions/catalog.jsonl": "master",
    "plans/GOVERNANCE.md": "governance",
    "plans/requirements.md": "requirements",
    "plans/requirements/catalog.jsonl": "requirements",
}


def _run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout


def _skeleton_for_gap(gap: dict) -> dict:
    """Build the `write_entry` kwargs for one gap date's auto-skeleton entry."""
    commits = gap["commits"]
    # `.get()`, not `[...]`: `files` is expected to only ever contain governed paths (that's what
    # audit_log_coverage.py's git pathspec restricts `--name-only` to), but a skeleton is exactly
    # the wrong place to let an unexpected value raise -- fall back to "master" rather than crash
    # an unattended CI job over a tag, and still list the file in the body regardless.
    inferred = {
        _TAG_BY_GOVERNED_FILE[f] for c in commits for f in c["files"] if f in _TAG_BY_GOVERNED_FILE
    }
    tags = sorted(inferred) or ["master"]
    tags.append("auto-skeleton")

    if len(commits) == 1:
        title = commits[0]["subject"]
    else:
        title = f"{len(commits)} commits landed without a logs/ entry."
    summary = title if len(title) <= 120 else title[:117] + "..."

    lines = [
        "Auto-generated skeleton (scripts/governance/heal_log_coverage.py) -- coverage is "
        "guaranteed mechanically; the narrative below is not. Needs enrichment describing each "
        "commit's actual root cause and fix; find every skeleton with `grep auto-skeleton "
        "logs/*.md`.",
        "",
    ]
    for commit in commits:
        files = ", ".join(commit["files"])
        lines.append(f"- `{commit['sha'][:9]}` {commit['author']} -- {commit['subject']} ({files})")
    body = "\n".join(lines)

    return {
        "date": gap["date"],
        "tags": tags,
        "decisions": [],
        "requirements": [],
        "wave_phase": [],
        "title": title,
        "summary": summary,
        "body": body,
    }


def _validate_commit_and_push(dates: list[str]) -> int:
    """Run the full structural validator against the just-written skeleton(s); commit and push
    only if it's clean. Isolated from `heal()` so tests can stub this whole tail (it's the one
    part of this script that shells out to git and to another script as a subprocess) while still
    exercising the real gap-finding and skeleton-generation logic above it."""
    validate = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "governance" / "validate_plan_structure.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if validate.returncode != 0:
        print(
            "validate_plan_structure.py failed against the healed state -- not committing or "
            "pushing anything. This is the healer's own self-check catching a bug in itself, not "
            "a pre-existing repo problem (the same check already gates every other commit).\n"
            + validate.stdout
            + validate.stderr,
            file=sys.stderr,
        )
        return 1

    _run_git(["add", "--", "logs/"])
    message = (
        f"docs(logs): auto-heal missing shard entr{'y' if len(dates) == 1 else 'ies'} for "
        + (dates[0] if len(dates) == 1 else f"{len(dates)} dates ({dates[0]}..{dates[-1]})")
    )
    _run_git(["commit", "-m", message])
    _run_git(["push"])
    print(f"Committed and pushed: {message}")
    return 0


def heal(rev_range: str | None, *, dry_run: bool) -> int:
    gaps = find_gaps(rev_range)
    if not gaps:
        print("No logs/ coverage gaps found -- nothing to heal.")
        return 0

    if len(gaps) > MAX_AUTO_HEAL_DATES:
        print(
            f"Refusing to auto-heal: {len(gaps)} gap dates found, over the "
            f"{MAX_AUTO_HEAL_DATES}-date circuit breaker. This is too large a batch for a "
            "routine missed entry -- needs human investigation, not a bigger unattended "
            "auto-write. Dates: " + ", ".join(g["date"] for g in gaps),
            file=sys.stderr,
        )
        return 2

    dates = [g["date"] for g in gaps]
    print(f"Healing {len(gaps)} gap date(s): {', '.join(dates)}")
    for gap in gaps:
        skeleton = _skeleton_for_gap(gap)
        if dry_run:
            print(f"[dry-run] would write logs/{skeleton['date']}.md: {skeleton['title']!r}")
            continue
        entries = write_entry(**skeleton)
        print(f"Wrote logs/{skeleton['date']}.md ({entries} entries).")

    if dry_run:
        print("[dry-run] skipping validate/commit/push.")
        return 0

    return _validate_commit_and_push(dates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full-history", action="store_true")
    mode.add_argument("--push-range", nargs=2, metavar=("BEFORE", "AFTER"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without writing, validating, committing, or pushing.",
    )
    args = parser.parse_args()

    if args.full_history:
        rev_range: str | None = None
    else:
        before, after = args.push_range
        rev_range = after if set(before) == {"0"} else f"{before}..{after}"

    return heal(rev_range, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
