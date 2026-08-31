"""Read-only detector for `logs/` coverage gaps: which calendar dates have a commit touching the
governed plan-trio/catalog files but no `logs/<date>.md` shard on disk. This is the same query
used to find the 10 real missing days that motivated this script -- productionized so
`heal_log_coverage.py` (what to auto-fix) and the scheduled full-history audit workflow (what
slipped past every other layer) share one implementation instead of drifting reimplementations.

Deliberately simple: "covered" means the shard file exists on disk right now, for any date with a
governed-file commit in the scanned range -- it does not require the logs/ change to have landed
in the exact same commit or push, since a later push on the same day legitimately covers an
earlier one. `validate_plan_structure.py`'s `check_governed_edits_paired_with_log_entry` is the
separate, stricter, same-change check that runs as the local pre-commit/CI blocking gate; this
script is the ground-truth sweep, not a diff-of-one-change check.

Never modifies anything. Standalone; never imported by `src/`. Usage:

    python scripts/governance/audit_log_coverage.py --full-history
    python scripts/governance/audit_log_coverage.py --push-range <before-sha> <after-sha>

Prints one JSON object to stdout: `{"gaps": [{"date": ..., "commits": [{"sha", "author",
"subject", "files"}, ...]}, ...]}`, oldest date first. Exit code 0 if no gaps, 1 if any gaps found.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = REPO_ROOT / "logs"

GOVERNED_PATHS = (
    "plans/master.md",
    "plans/GOVERNANCE.md",
    "plans/requirements.md",
    "plans/decisions/catalog.jsonl",
    "plans/requirements/catalog.jsonl",
)

_FIELD_SEP = "\x1f"  # unit separator -- safe against commit subjects containing any other
# punctuation, unlike a printable delimiter such as "|" or ",".


def _run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    return completed.stdout


def _commits_touching_governed_files(rev_range: str | None) -> list[dict]:
    """One record per commit (in `rev_range`, or full history if None) that touches at least one
    governed path, each with its date/author/subject and exactly which governed files it
    touched."""
    log_args = ["log", f"--format=%H{_FIELD_SEP}%ad{_FIELD_SEP}%an{_FIELD_SEP}%s", "--date=short"]
    if rev_range:
        log_args.append(rev_range)
    log_args.append("--")
    log_args.extend(GOVERNED_PATHS)

    commits = []
    for line in _run_git(log_args).splitlines():
        if not line.strip():
            continue
        sha, date, author, subject = line.split(_FIELD_SEP, 3)
        files_output = _run_git(["show", "--name-only", "--format=", sha, "--", *GOVERNED_PATHS])
        files = [f for f in files_output.splitlines() if f.strip()]
        commits.append(
            {"sha": sha, "date": date, "author": author, "subject": subject, "files": files}
        )
    return commits


_USE_GIT_COMMITS = object()  # sentinel: tests inject an explicit commit list instead of this
# default, so they never shell out to git or touch the real repo -- same seam pattern as
# validate_plan_structure.py's `_USE_GIT`/`_USE_GIT_TEXTS`.


def find_gaps(
    rev_range: str | None = None,
    commits: list[dict] | None = _USE_GIT_COMMITS,  # type: ignore[assignment]
) -> list[dict]:
    """Every distinct date (within `rev_range`, or full history) with a governed-file commit and
    no `logs/<date>.md` on disk right now, each with its contributing commits, oldest date
    first."""
    if commits is _USE_GIT_COMMITS:
        commits = _commits_touching_governed_files(rev_range)

    by_date: dict[str, list[dict]] = {}
    for commit in commits:
        by_date.setdefault(commit["date"], []).append(commit)

    return [
        {"date": date, "commits": by_date[date]}
        for date in sorted(by_date)
        if not (LOGS_DIR / f"{date}.md").exists()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--full-history", action="store_true", help="Scan all of HEAD's history, not just a range."
    )
    mode.add_argument(
        "--push-range",
        nargs=2,
        metavar=("BEFORE", "AFTER"),
        help="Scan only commits reachable from AFTER but not BEFORE (a push event's before/after "
        "SHAs). A BEFORE of all zeros -- a brand-new branch's push event -- falls back to AFTER's "
        "full history instead of erroring.",
    )
    args = parser.parse_args()

    if args.full_history:
        rev_range: str | None = None
    else:
        before, after = args.push_range
        rev_range = after if set(before) == {"0"} else f"{before}..{after}"

    gaps = find_gaps(rev_range)
    print(json.dumps({"gaps": gaps}, indent=2))
    if gaps:
        print(f"{len(gaps)} date(s) with ungoverned edits and no logs/ entry.", file=sys.stderr)
        return 1
    print("No logs/ coverage gaps found.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
